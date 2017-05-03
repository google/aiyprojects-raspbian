#!/usr/bin/env python3
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

"""Check that the Cloud Speech API can be used.
"""

import json
import os
import subprocess
import traceback

if os.path.exists('/home/pi/credentials.json'):
    # Legacy fallback: old location of credentials.
    CREDENTIALS_PATH = '/home/pi/credentials.json'
else:
    CREDENTIALS_PATH = '/home/pi/cloud_speech.json'

VOICE_RECOGNIZER_PATH = '/home/pi/voice-recognizer-raspi'
PYTHON3 = VOICE_RECOGNIZER_PATH + '/env/bin/python3'
SPEECH_PY = VOICE_RECOGNIZER_PATH + '/src/speech.py'
SPEECH_PY_ENV = {
    'VIRTUAL_ENV': VOICE_RECOGNIZER_PATH + '/env',
    'PATH': VOICE_RECOGNIZER_PATH + '/env/bin:' + os.getenv('PATH'),
}
TEST_AUDIO = VOICE_RECOGNIZER_PATH + '/checkpoints/test_hello.raw'
RECOGNIZED_TEXT = 'hello'


def check_credentials_valid():
    """Check the credentials are JSON service credentials."""
    try:
        obj = json.load(open(CREDENTIALS_PATH))
    except ValueError:
        return False

    return 'type' in obj and obj['type'] == 'service_account'


def check_speech_reco():
    """Try to test the speech reco code from voice-recognizer-raspi."""
    print('Testing the Google Cloud Speech API...')
    p = subprocess.Popen(  # pylint: disable=invalid-name
        [PYTHON3, SPEECH_PY, TEST_AUDIO], env=SPEECH_PY_ENV,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.communicate()[0].decode('utf-8')

    if p.returncode:
        print('Speech recognition failed with', p.returncode)
        print(output)
        return False
    else:
        # speech.py succeeded, check the text was recognized
        if RECOGNIZED_TEXT in output:
            return True
        else:
            print('Speech recognition output not as expected:')
            print(output)
            print('Expected:', RECOGNIZED_TEXT)
            return False


def main():
    """Run all checks and print status."""
    if not os.path.exists(CREDENTIALS_PATH):
        print(
            """Please follow these instructions to get Google Cloud credentials:
https://cloud.google.com/speech/docs/getting-started#set_up_your_project
and save them to""", CREDENTIALS_PATH)
        return

    if not check_credentials_valid():
        print(
            CREDENTIALS_PATH, """is not valid, please check that you have downloaded JSON
service credentials.""")
        return

    if not check_speech_reco():
        print('Failed to test the Cloud Speech API. Please see error above.')
        return

    print("Everything's set up to use the Google Cloud.")

if __name__ == '__main__':
    try:
        main()
        input('Press Enter to close...')
    except:  # pylint: disable=bare-except
        traceback.print_exc()
        input('Press Enter to close...')
