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

"""A recorder driver capable of recording voice samples from the VoiceHat microphones."""

import logging
import os
import subprocess
import threading

import aiy._drivers._alsa

logger = logging.getLogger('recorder')


class Recorder(threading.Thread):
    """A driver to record audio from the VoiceHat microphones.

    Stream audio from microphone in a background thread and run processing
    callbacks. It reads audio in a configurable format from the microphone,
    then converts it to a known format before passing it to the processors.

    This driver accumulates input (audio samples) in a local buffer. Once the
    buffer contains more than CHUNK_S seconds, it passes the chunk to all
    processors. An audio processor defines a 'add_data' method that receives
    the chunk of audio samples to process.
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

        super().__init__(daemon=True)
        self._record_event = threading.Event()
        self._processors = []

        self._chunk_bytes = int(self.CHUNK_S * sample_rate_hz) * channels * bytes_per_sample

        self._cmd = [
            'arecord',
            '-q',
            '-t', 'raw',
            '-D', input_device,
            '-c', str(channels),
            # pylint: disable=W0212
            '-f', aiy._drivers._alsa.sample_width_to_string(bytes_per_sample),
            '-r', str(sample_rate_hz),
        ]
        self._arecord = None
        self._closed = False

    def add_processor(self, processor):
        """Add an audio processor.

        An audio processor is an object that has an 'add_data' method with the
        following signature:
        class MyProcessor(object):
          def __init__(self):
            ...

          def add_data(self, data):
            # processes the chunk of data here.

        The added processor may be called multiple times with chunks of audio data.
        """
        self._record_event.set()
        self._processors.append(processor)

    def remove_processor(self, processor):
        """Remove an added audio processor."""
        try:
            self._processors.remove(processor)
        except ValueError:
            logger.warn("processor was not found in the list")
        self._record_event.clear()

    def run(self):
        """Reads data from arecord and passes to processors."""

        logger.info("started recording")

        # Check for race-condition when __exit__ is called at the same time as
        # the process is started by the background thread
        if self._closed:
            self._arecord.kill()
            return

        this_chunk = b''
        while True:
            if not self._record_event.is_set() and self._arecord:
                self._arecord.kill()
                self._arecord = None
            self._record_event.wait()
            if not self._arecord:
                self._arecord = subprocess.Popen(self._cmd, stdout=subprocess.PIPE)
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

    def stop(self):
        """Stops the recorder and cleans up all resources."""
        self._closed = True
        if self._arecord:
            self._arecord.kill()

    def _handle_chunk(self, chunk):
        """Send audio chunk to all processors."""
        for p in self._processors:
            p.add_data(chunk)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
