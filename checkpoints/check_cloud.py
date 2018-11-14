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
import traceback

from aiy.cloudspeech import CloudSpeechClient

OLD_CREDENTIALS_FILE = os.path.expanduser('~/credentials.json')
NEW_CREDENTIALS_FILE = os.path.expanduser('~/cloud_speech.json')
if os.path.exists(OLD_CREDENTIALS_FILE):
    # Legacy fallback: old location of credentials.
    CREDENTIALS_PATH = OLD_CREDENTIALS_FILE
else:
    CREDENTIALS_PATH = NEW_CREDENTIALS_FILE

def check_credentials_valid():
    """Check the credentials are JSON service credentials."""
    try:
        obj = json.load(open(CREDENTIALS_PATH))
    except ValueError:
        return False

    return 'type' in obj and obj['type'] == 'service_account'

def check_speech_reco():
    path = os.path.join(os.path.dirname(__file__), 'test_hello.raw')
    with open(path, 'rb') as f:
        client = CloudSpeechClient()
        result = client.recognize_bytes(f.read())
        return result.strip() == 'hello'

def main():
    """Run all checks and print status."""
    if not os.path.exists(CREDENTIALS_PATH):
        print(
            """Please follow the Custom Voice User Interface instructions on the AIY website
to download credentials:
https://aiyprojects.withgoogle.com/voice-v1/#makers-guide-3-custom-voice-user-interface
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

    print("Everything is set up to use the Google Cloud.")

if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
    finally:
        input('Press Enter to close...')
