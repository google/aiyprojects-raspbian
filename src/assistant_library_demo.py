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

"""A demo of the Google Assistant Library"""

import sys

import aiy.assistant.auth_helpers
import aiy.voicehat


def main():
    """Run a recognizer using the Google Assistant Library.

    The Google Assistant Library has direct access to the audio API, so this
    Python code doesn't need to record audio.
    Hot word detection "OK, Google" is supported.
    """

    try:
        from google.assistant.library import Assistant
        from google.assistant.library.event import EventType
    except ImportError:
        print('''
ERROR: failed to import the Google Assistant Library. This is required for
"OK Google" hotwording, but is only available for Raspberry Pi 2/3. It can be
installed with:
    env/bin/pip install google-assistant-library==0.0.2''')
        sys.exit(1)

    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()

    def process_event(event):
        status_ui = aiy.voicehat.get_status_ui()
        if event.type == EventType.ON_START_FINISHED:
            status_ui.status('ready')
            if sys.stdout.isatty():
                print('Say "OK, Google" then speak, or press Ctrl+C to quit...')

        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            status_ui.status('listening')

        elif event.type == EventType.ON_END_OF_UTTERANCE:
            status_ui.status('thinking')

        elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
            status_ui.status('ready')

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    with Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(event)


if __name__ == '__main__':
    main()
