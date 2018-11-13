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

import argparse
import os
import subprocess
import tempfile

RUN_DIR = '/run/user/%d' % os.getuid()

def say(text, lang='en-US', volume=60, pitch=130, speed=100, device='default'):
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
