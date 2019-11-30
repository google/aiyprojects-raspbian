"""
APIs to record and play audio files.

.. note::

    These APIs are designed for the Voice Kit, but have no dependency on the Voice
    HAT/Bonnet specifically. However, many of the APIs require some type of sound card
    attached to the Raspberry Pi that can be detected by the ALSA subsystem.

.. module:: aiy.voice.audio

Recording
---------

.. autofunction:: arecord

.. autofunction:: record_file

.. autofunction:: record_file_async

.. autoclass:: Recorder
    :members:
    :undoc-members:
    :show-inheritance:


Playback
--------

.. autofunction:: aplay

.. autofunction:: play_raw

.. autofunction:: play_raw_async

.. autofunction:: play_wav

.. autofunction:: play_wav_async

.. autoclass:: BytesPlayer
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

.. autoclass:: FilePlayer
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:


Audio format
------------

.. autofunction:: wave_set_format

.. autofunction:: wave_get_format

.. autoclass:: AudioFormat
    :members:
    :undoc-members:
    :show-inheritance:

"""

import contextlib
import subprocess
import threading
import itertools
import wave

from collections import namedtuple

SUPPORTED_FILETYPES = ('wav', 'raw', 'voc', 'au')


class AudioFormat(namedtuple('AudioFormat',
                             ['sample_rate_hz', 'num_channels', 'bytes_per_sample'])):
    @property
    def bytes_per_second(self):
        return self.sample_rate_hz * self.num_channels * self.bytes_per_sample

AudioFormat.CD = AudioFormat(sample_rate_hz=44100, num_channels=2, bytes_per_sample=2)


def wave_set_format(wav_file, fmt):
    """
    Sets the format for the given WAV file, using the given :class:`AudioFormat`.

    Args:
        wav_file: A :class:`wave.Wave_write` object.
        fmt: A :class:`AudioFormat` object.
    """
    wav_file.setnchannels(fmt.num_channels)
    wav_file.setsampwidth(fmt.bytes_per_sample)
    wav_file.setframerate(fmt.sample_rate_hz)


def wave_get_format(wav_file):
    """
    Returns the :class:`AudioFormat` corresponding to the WAV file provided.

    Args:
        wav_file: A :class:`wave.Wave_read` object.
    """
    return AudioFormat(sample_rate_hz=wav_file.getframerate(),
                       num_channels=wav_file.getnchannels(),
                       bytes_per_sample=wav_file.getsampwidth())


def arecord(fmt, filetype='raw', filename=None, device='default'):
    """Returns an ``arecord`` command-line command.

    Args:
        fmt: The audio format; an instance of :class:`AudioFormat`.
        filetype: The type of file. Must be either 'wav', 'raw', 'voc', or 'au'.
        filename: The audio file to play.
        device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.
    """
    if fmt is None:
        raise ValueError('Format must be specified for recording.')

    if filetype not in SUPPORTED_FILETYPES:
        raise ValueError('File type must be %s.' % ', '.join(SUPPORTED_FILETYPES))

    cmd = ['arecord', '-q',
           '-D', device,
           '-t', filetype,
           '-c', str(fmt.num_channels),
           '-f', 's%d' % (8 * fmt.bytes_per_sample),
           '-r', str(fmt.sample_rate_hz)]

    if filename is not None:
        cmd.append(filename)

    return cmd


def aplay(fmt, filetype='raw', filename=None, device='default'):
    """Returns an ``aplay`` command-line command.

    Args:
        fmt: The audio format; an instance of :class:`AudioFormat`.
        filetype: The type of file. Must be either 'wav', 'raw', 'voc', or 'au'.
        filename: The audio file to play.
        device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.
    """
    if filetype == 'raw' and fmt is None:
        raise ValueError('Format must be specified for raw data.')

    cmd = ['aplay', '-q',
           '-D', device,
           '-t', filetype]

    if fmt is not None:
        cmd.extend(['-c', str(fmt.num_channels),
                    '-f', 's%d' % (8 * fmt.bytes_per_sample),
                    '-r', str(fmt.sample_rate_hz)])

    if filename is not None:
        cmd.append(filename)

    return cmd

def record_file_async(fmt, filename, filetype, device='default'):
    """
    Records an audio file, asynchronously. To stop the recording, terminate the returned
    :class:`~subprocess.Popen` object.

    Args:
        fmt: The audio format; an instance of :class:`AudioFormat`.
        filename: The file where the recording should be saved.
        filetype: The type of file. Must be either 'wav', 'raw', 'voc', or 'au'.
        device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.

    Returns:
        The :class:`~subprocess.Popen` object for the subprocess in which audio is recording.
    """
    if filename is None:
        raise ValueError('Filename must be specified.')

    if filetype is None:
        raise ValueError('Filetype must be specified.')

    cmd = arecord(fmt, filetype=filetype, filename=filename, device=device)
    return subprocess.Popen(cmd)


def record_file(fmt, filename, filetype, wait, device='default'):
    """
    Records an audio file (blocking). The length of the recording is determined by a
    blocking ``wait`` function that you provide. When your ``wait`` function finishes,
    so does this function and the recording.

    For an example, see :github:`src/examples/voice/voice_recorder.py`.

    Args:
        fmt: The audio format; an instance of :class:`AudioFormat`.
        filename: The file where the recording should be saved.
        filetype: The type of file. Must be either 'wav', 'raw', 'voc', or 'au'.
        wait: A blocking function that determines the length of the recording (and thus the
            length of time that this function is blocking).
        device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.
    """
    if wait is None:
        raise ValueError('Wait callback must be specified.')

    process = record_file_async(fmt, filename, filetype, device)
    try:
        wait()
    finally:
        process.terminate()
        process.wait()


def play_wav_async(filename_or_data):
    """
    Plays a WAV file or data asynchronously.

    Args:
        filename_or_data: The WAV file or bytes to play.

    Returns:
        The :class:`~subprocess.Popen` object for the subprocess in which audio is playing.
    """
    if isinstance(filename_or_data, (bytes, bytearray)):
        cmd = aplay(fmt=None, filetype='wav', filename=None)
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        process.stdin.write(filename_or_data)
        return process

    if isinstance(filename_or_data, str):
        cmd = aplay(fmt=None, filetype='wav', filename=filename_or_data)
        return subprocess.Popen(cmd)

    raise ValueError('Must be filename or byte-like object')


def play_wav(filename_or_data):
    """
    Plays a WAV file or data (blocking).

    Args:
        filename_or_data: The WAV file or bytes to play.
    """
    play_wav_async(filename_or_data).wait()


def play_raw_async(fmt, filename_or_data):
    """
    Plays raw audio data asynchronously.

    Args:
        fmt: The audio format; an instance of :class:`AudioFormat`.
        filename_or_data: The file or bytes to play.

    Returns:
        The :class:`~subprocess.Popen` object for the subprocess in which audio is playing.
    """
    if isinstance(filename_or_data, (bytes, bytearray)):
        cmd = aplay(fmt=fmt, filetype='raw')
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        process.stdin.write(filename_or_data)
        return process

    if isinstance(filename_or_data, str):
        cmd = aplay(fmt=fmt, filetype='raw', filename=filename_or_data)
        return subprocess.Popen(cmd)

    raise ValueError('Must be filename or byte-like object')


def play_raw(fmt, filename_or_data):
    """
    Plays raw audio data (blocking).

    Args:
        fmt: The audio format; an instance of :class:`AudioFormat`.
        filename_or_data: The file or bytes to play.
    """
    play_raw_async(fmt, filename_or_data).wait()


class Recorder:

    def __init__(self, ):
        self._process = None
        self._done = threading.Event()
        self._started = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.join()

    def record(self, fmt, chunk_duration_sec, device='default',
               num_chunks=None,
               on_start=None, on_stop=None, filename=None):
        """
        Records audio with the ALSA soundcard driver, via ``arecord``.

        Args:
            fmt: The audio format; an instance of :class:`AudioFormat`.
            chunk_duration_sec: The duration of each audio chunk, in seconds (may be float).
            device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.
            num_chunks: The number of chunks to record. Leave as ``None`` to instead record
                indefinitely, until you call :meth:`~Recorder.done`.
            on_start: A function callback to call when recording starts.
            on_stop: A function callback to call when recording stops.
            filename: A filename to use if you want to save the recording as a WAV file.
        Yields:
            A chunk of audio data. Each chunk size = ``chunk_duraction_sec * fmt.bytes_per_second``
        """

        chunk_size = int(chunk_duration_sec * fmt.bytes_per_second)
        cmd = arecord(fmt=fmt, device=device)

        wav_file = None
        if filename:
            wav_file = wave.open(filename, 'wb')
            wave_set_format(wav_file, fmt)

        self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self._started.set()
        if on_start:
            on_start()
        try:
            for _ in (range(num_chunks) if num_chunks else itertools.count()):
                if self._done.is_set():
                    break
                data = self._process.stdout.read(chunk_size)
                if not data:
                    break
                if wav_file:
                    wav_file.writeframes(data)
                yield data
        finally:
            self._process.stdout.close()
            if on_stop:
                on_stop()
            if wav_file:
                wav_file.close()

    def done(self):
        """
        Stops the recording that started via :meth:`~Recorder.record`.
        """
        self._done.set()

    def join(self):
        self._started.wait()
        self._process.wait()



class Player:
    def __init__(self):
        self._process = None
        self._started = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.join()

    def _popen(self, cmd, **kwargs):
        self._process = subprocess.Popen(cmd, **kwargs)
        self._started.set()
        return self._process

    def join(self):
        self._started.wait()
        self._process.wait()


class FilePlayer(Player):
    """
    Plays audio from a file.
    """
    def play_raw(self, fmt, filename, device='default'):
        """
        Plays a raw audio file.

        Args:
            fmt: The audio format; an instance of :class:`AudioFormat`.
            filename: The audio file to play.
            device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.
        """
        self._popen(aplay(fmt=fmt, filetype='raw', filename=filename, device=device))


    def play_wav(self, filename, device='default'):
        """
        Plays a WAV file.

        Args:
            filename: The WAV file to play.
            device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.
        """
        self._popen(aplay(fmt=None, filetype='wav', filename=filename, device=device))

class BytesPlayer(Player):
    """
    Plays audio from a given byte data source.
    """
    def play(self, fmt, device='default'):
        """
        Args:
            fmt: The audio format; an instance of :class:`AudioFormat`.
            device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.

        Returns:
            A closure with an inner function ``push()`` that accepts the byte data. 
        """
        process = self._popen(aplay(fmt=fmt, filetype='raw', device=device), stdin=subprocess.PIPE)

        def push(data):
            if data:
                process.stdin.write(data)
            else:
                process.stdin.close()
        return push
