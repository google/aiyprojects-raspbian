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
import threading

import aiy.assistant.auth_helpers
import aiy.voicehat
from google.assistant.library import Assistant
from google.assistant.library.event import EventType


class MyAssistant(object):
    def __init__(self, assistant):
        self._assistant = assistant
        self._ready = False
        self._status_ui = aiy.voicehat.get_status_ui()
        self._recognizer = threading.Thread(target=self._run_recognizer)

    def start(self):
        self._recognizer.start()

    def _run_recognizer(self):
        for event in self._assistant.start():
            self._process_event(event)

    def _process_event(self, event):
        if event.type == EventType.ON_START_FINISHED:
            self._status_ui.status('ready')
            self._ready = True
            aiy.voicehat.get_button().on_press(self._on_button_press)
            if sys.stdout.isatty():
                print('Say "OK, Google" or press the VoiceHat button then speak,'
                      'or press Ctrl+C to quit...')

        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            self._ready = False
            self._status_ui.status('listening')

        elif event.type == EventType.ON_END_OF_UTTERANCE:
            self._status_ui.status('thinking')

        elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
            self._status_ui.status('ready')
            self._ready = True

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def _on_button_press(self):
        print('on_button_press')
        if self._ready:
            self._ready = False
            self._assistant.start_conversation()


def main():
    """Run a recognizer using the Google Assistant Library.

    The Google Assistant Library has direct access to the audio API, so this
    Python code doesn't need to record audio. Hot word detection "OK, Google" is
    supported.

    The Google Assistant Library can be installed with:
    env/bin/pip install google-assistant-library==0.0.2

    It is available for Raspberry Pi 2/3 only.
    """
    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
    with Assistant(credentials) as assistant:
        my_assistant = MyAssistant(assistant)
        for event in assistant.start():
            my_assistant._process_event(event)


if __name__ == '__main__':
    main()
