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

"""A driver for audio playback."""

import logging
import subprocess
import wave

import aiy._drivers._alsa

logger = logging.getLogger('audio')


class Player(object):
    """Plays short audio clips from a buffer or file."""

    def __init__(self, output_device='default'):
        self._output_device = output_device

    def play_bytes(self, audio_bytes, sample_rate, sample_width=2):
        """Play audio from the given bytes-like object.

        Args:
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
            # pylint: disable=W0212
            '-f', aiy._drivers._alsa.sample_width_to_string(sample_width),
            '-r', str(sample_rate),
        ]

        aplay = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        aplay.stdin.write(audio_bytes)
        aplay.stdin.close()
        retcode = aplay.wait()

        if retcode:
            logger.error('aplay failed with %d', retcode)

    def play_wav(self, wav_path):
        """Play audio from the given WAV file.

        The file should be mono and small enough to load into memory.
        Args:
          wav_path: path to the wav file
        """
        with wave.open(wav_path, 'r') as wav:
            if wav.getnchannels() != 1:
                raise ValueError(wav_path + ' is not a mono file')

            frames = wav.readframes(wav.getnframes())
            self.play_bytes(frames, wav.getframerate(), wav.getsampwidth())
