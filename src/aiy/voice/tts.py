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

"""
An API that performs text-to-speech.

You can also use this to perform text-to-speech from the command line::

    python ~/AIY-projects-python/src/aiy/voice/tts.py "hello world"

"""

import argparse
import os
import subprocess
import tempfile

RUN_DIR = '/run/user/%d' % os.getuid()

def say(text, lang='en-US', volume=60, pitch=130, speed=100, device='default'):
    """
    Speaks the provided text.

    Args:
        text: The text you want to speak.
        lang: The language to use. Supported languages are:
            en-US, en-GB, de-DE, es-ES, fr-FR, it-IT.
        volume: Volume level for the converted audio. The normal volume level is
            100. Valid volume levels are between 0 (no audible output) and 500 (increasing the
            volume by a factor of 5). Values higher than 100 might result in degraded signal
            quality due to saturation effects (clipping) and is not recommended. To instead adjust
            the volume output of your device, enter ``alsamixer`` at the command line.
        pitch: The pitch level for the voice. The normal pitch level is 100, the allowed values lie
            between 50 (one octave lower) and 200 (one octave higher).
        speed: The speed of the voice. The normal speed level is 100, the allowed values lie
            between 20 (slowing down by a factor of 5) and 500 (speeding up by a factor of 5).
        device: The PCM device name. Leave as ``default`` to use the default ALSA soundcard.
    """
    data = "<volume level='%d'><pitch level='%d'><speed level='%d'>%s</speed></pitch></volume>" % \
           (volume, pitch, speed, text)
    with tempfile.NamedTemporaryFile(suffix='.wav', dir=RUN_DIR) as f:
       cmd = 'pico2wave --wave %s --lang %s "%s" && aplay -q -D %s %s' % \
             (f.name, lang, data, device, f.name)
       subprocess.check_call(cmd, shell=True)


def _main():
    parser = argparse.ArgumentParser(description='Text To Speech (pico2wave)')
    parser.add_argument('--lang', default='en-US')
    parser.add_argument('--volume', type=int, default=60)
    parser.add_argument('--pitch', type=int, default=130)
    parser.add_argument('--speed', type=int, default=100)
    parser.add_argument('--device', default='default')
    parser.add_argument('text', help='path to disk image file ')
    args = parser.parse_args()
    say(args.text, lang=args.lang, volume=args.volume, pitch=args.pitch, speed=args.speed,
        device=args.device)


if __name__ == '__main__':
    _main()
