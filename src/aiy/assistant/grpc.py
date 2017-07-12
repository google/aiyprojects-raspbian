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

"""An API to access the Google Assistant."""

import os.path

import aiy._apis._speech
import aiy.assistant._auth_helpers
import aiy.audio
import aiy.voicehat

# Global variables. They are lazily initialized.
assistant_recognizer = None

# Expected location of the Assistant credentials file:
ASSISTANT_CREDENTIALS_FILE = os.path.expanduser('~/assistant.json')


class _AssistantRecognizer(object):
    """Your personal Google Assistant."""

    def __init__(self, credentials_file):
        self._request = aiy._apis._speech.AssistantSpeechRequest(credentials_file)
        self._recorder = aiy.audio.get_recorder()

    def recognize(self):
        """Recognizes the user's speech and gets answers from Google Assistant.

        This function listens to the user's speech via the VoiceHat speaker and
        sends the audio to the Google Assistant Library. The response is returned in
        both text and audio.

        Usage:
            transcript, audio = my_recognizer.recognize()
            if transcript is not None:
                print('You said ', transcript)
                aiy.audio.play_audio(audio)
        """
        self._request.reset()
        self._request.set_endpointer_cb(self._endpointer_callback)
        self._recorder.add_processor(self._request)
        response = self._request.do_request()
        return response.transcript, response.response_audio

    def _endpointer_callback(self):
        self._recorder.remove_processor(self._request)


def get_assistant():
    """Returns a recognizer that uses Google Assistant APIs.

    Sample usage:
        button = aiy.voicehat.get_button()
        recognizer = aiy.assistant.grpc.get_recognizer()
        print('Your Google Assistant is ready.')
        while True:
            print('Press the button and speak')
            button.wait_for_press()
            print('Listening...')
            transcript, audio = recognizer.recognize()
            if transcript is not None:
                print('Assistant said ', transcript)
            if audio is not None:
                aiy.audio.play_audio(audio)
    """
    global assistant_recognizer
    if assistant_recognizer is None:
        credentials = aiy.assistant._auth_helpers.try_to_get_credentials(ASSISTANT_CREDENTIALS_FILE)
        assistant_recognizer = _AssistantRecognizer(credentials)
    return assistant_recognizer
