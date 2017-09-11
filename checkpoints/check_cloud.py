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

"""Check that the Cloud Speech API can be used."""

import json
import os
import os.path
import sys
import traceback

sys.path.append(os.path.realpath(os.path.join(__file__, '..', '..')) + '/src/')

import aiy._apis._speech  # noqa

OLD_CREDENTIALS_FILE = os.path.expanduser('~/credentials.json')
NEW_CREDENTIALS_FILE = os.path.expanduser('~/cloud_speech.json')
if os.path.exists(OLD_CREDENTIALS_FILE):
    # Legacy fallback: old location of credentials.
    CREDENTIALS_PATH = OLD_CREDENTIALS_FILE
else:
    CREDENTIALS_PATH = NEW_CREDENTIALS_FILE

ROOT_PATH = os.path.realpath(os.path.join(__file__, '..', '..'))
PYTHON3 = ROOT_PATH + '/env/bin/python3'
SPEECH_PY = ROOT_PATH + '/src/aiy/_apis/_speech.py'
SPEECH_PY_ENV = {
    'VIRTUAL_ENV': ROOT_PATH + '/env',
    'PATH': ROOT_PATH + '/env/bin:' + os.getenv('PATH'),
}
TEST_AUDIO = ROOT_PATH + '/checkpoints/test_hello.raw'
RECOGNIZED_TEXT = 'hello'


def check_credentials_valid():
    """Check the credentials are JSON service credentials."""
    try:
        obj = json.load(open(CREDENTIALS_PATH))
    except ValueError:
        return False

    return 'type' in obj and obj['type'] == 'service_account'


def check_speech_reco():
    """Try to test the speech recognition code from AIY APIs."""
    print('Testing the Google Cloud Speech API...')
    req = aiy._apis._speech.CloudSpeechRequest(CREDENTIALS_PATH)
    with open(TEST_AUDIO, 'rb') as f:
        while True:
            chunk = f.read(64000)
            if not chunk:
                break
            req.add_data(chunk)
    req.end_audio()
    output = req.do_request()

    if RECOGNIZED_TEXT in output:
        return True

    print('Speech recognition failed or output not as expected:')
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
