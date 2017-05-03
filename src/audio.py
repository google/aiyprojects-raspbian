# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Wraps the audio backend with a simple Python interface for recording and
playback.
"""

import logging
import os
import subprocess
import threading
import wave

logger = logging.getLogger('audio')


def sample_width_to_string(sample_width):
    """Convert sample width (bytes) to ALSA format string."""
    return {1: 's8', 2: 's16', 4: 's32'}[sample_width]


class Recorder(threading.Thread):

    """Stream audio from microphone in a background thread and run processing
    callbacks. It reads audio in a configurable format from the microphone,
    then converts it to a known format before passing it to the processors.
    """

    CHUNK_S = 0.1

    def __init__(self, input_device='default',
                 channels=1, bytes_per_sample=2, sample_rate_hz=16000):
        """Create a Recorder with the given audio format.

        The Recorder will not start until start() is called. start() is called
        automatically if the Recorder is used in a `with`-statement.

        - input_device: name of ALSA device (for a list, run `arecord -L`)
        - channels: number of channels in audio read from the mic
        - bytes_per_sample: sample width in bytes (eg 2 for 16-bit audio)
        - sample_rate_hz: sample rate in hertz
        """

        super().__init__()

        self._processors = []

        self._chunk_bytes = int(self.CHUNK_S * sample_rate_hz) * channels * bytes_per_sample

        self._cmd = [
            'arecord',
            '-q',
            '-t', 'raw',
            '-D', input_device,
            '-c', str(channels),
            '-f', sample_width_to_string(bytes_per_sample),
            '-r', str(sample_rate_hz),
        ]
        self._arecord = None
        self._closed = False

    def add_processor(self, processor):
        self._processors.append(processor)

    def del_processor(self, processor):
        self._processors.remove(processor)

    def run(self):
        """Reads data from arecord and passes to processors."""

        self._arecord = subprocess.Popen(self._cmd, stdout=subprocess.PIPE)
        logger.info("started recording")

        # check for race-condition when __exit__ is called at the same time as
        # the process is started by the background thread
        if self._closed:
            self._arecord.kill()
            return

        this_chunk = b''

        while True:
            input_data = self._arecord.stdout.read(self._chunk_bytes)
            if not input_data:
                break

            this_chunk += input_data
            if len(this_chunk) >= self._chunk_bytes:
                self._handle_chunk(this_chunk[:self._chunk_bytes])
                this_chunk = this_chunk[self._chunk_bytes:]

        if not self._closed:
            logger.error('Microphone recorder died unexpectedly, aborting...')
            # sys.exit doesn't work from background threads, so use os._exit as
            # an emergency measure.
            logging.shutdown()
            os._exit(1)  # pylint: disable=protected-access

    def _handle_chunk(self, chunk):
        """Send audio chunk to all processors.
        """
        for p in self._processors:
            p.add_data(chunk)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self._closed = True
        if self._arecord:
            self._arecord.kill()


class Player(object):

    """Plays short audio clips from a buffer or file."""

    def __init__(self, output_device='default'):
        self._output_device = output_device

    def play_bytes(self, audio_bytes, sample_rate, sample_width=2):
        """Play audio from the given bytes-like object.

        audio_bytes: audio data (mono)
        sample_rate: sample rate in Hertz (24 kHz by default)
        sample_width: sample width in bytes (eg 2 for 16-bit audio)
        """

        cmd = [
            'aplay',
            '-q',
            '-t', 'raw',
            '-D', self._output_device,
            '-c', '1',
            '-f', sample_width_to_string(sample_width),
            '-r', str(sample_rate),
        ]

        aplay = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        aplay.stdin.write(audio_bytes)
        aplay.stdin.close()
        retcode = aplay.wait()

        if retcode:
            logger.error('aplay failed with %d', retcode)

    def play_wav(self, wav_path):
        """Play audio from the given WAV file. The file should be mono and
        small enough to load into memory.

        wav_path: path to wav file
        """

        with wave.open(wav_path, 'r') as wav:
            if wav.getnchannels() != 1:
                raise ValueError(wav_path + 'is not a mono file')

            frames = wav.readframes(wav.getnframes())
            self.play_bytes(frames, wav.getframerate(), wav.getsampwidth())


class WavDump(object):

    """A processor that logs to a WAV file, for testing audio recording."""

    def __init__(self, path, duration,
                 channels, bytes_per_sample, sample_rate_hz):
        self._wav = wave.open(path, 'wb')
        self._wav.setnchannels(channels)
        self._wav.setsampwidth(bytes_per_sample)
        self._wav.setframerate(sample_rate_hz)

        self._n_bytes = 0
        self._total_bytes = int(duration * sample_rate_hz) * channels * bytes_per_sample

    def add_data(self, data):
        """Write frames to the file if they fit within the total size."""
        max_bytes = self._total_bytes - self._n_bytes
        data = data[:max_bytes]
        self._n_bytes += len(data)

        if data:
            self._wav.writeframes(data)

    def is_done(self):
        return self._n_bytes >= self._total_bytes

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._wav.close()


def main():
    logging.basicConfig(level=logging.INFO)

    import argparse
    import time

    parser = argparse.ArgumentParser(description="Test audio wrapper")
    parser.add_argument('action', choices=['dump', 'play'],
                        help='What to do with the audio')
    parser.add_argument('-I', '--input-device', default='default',
                        help='Name of the audio input device')
    parser.add_argument('-c', '--channels', type=int, default=1,
                        help='Number of channels')
    parser.add_argument('-f', '--bytes-per-sample', type=int, default=2,
                        help='Sample width in bytes')
    parser.add_argument('-r', '--rate', type=int, default=16000,
                        help='Sample rate in Hertz')
    parser.add_argument('-O', '--output-device', default='default',
                        help='Name of the audio output device')
    parser.add_argument('-d', '--duration', default=2, type=float,
                        help='Dump duration in seconds (default: 2)')
    parser.add_argument('filename', help='Path to WAV file')
    args = parser.parse_args()

    if args.action == 'dump':
        recorder = Recorder(
            input_device=args.input_device,
            channels=args.channels,
            bytes_per_sample=args.bytes_per_sample,
            sample_rate_hz=args.rate)

        dumper = WavDump(args.filename, args.duration, args.channels,
                         args.bytes_per_sample, args.rate)

        with recorder, dumper:
            recorder.add_processor(dumper)

            while not dumper.is_done():
                time.sleep(0.1)

    elif args.action == 'play':
        Player(args.output_device).play_wav(args.filename)

if __name__ == '__main__':
    main()
