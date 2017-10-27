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

"""An API to access Google Speech recognition service."""

import os.path

import aiy._apis._speech
import aiy.audio
import aiy.voicehat

# Global variables. They are lazily initialized.
_cloudspeech_recognizer = None

# Expected location of the CloudSpeech credentials file:
CLOUDSPEECH_CREDENTIALS_FILE = os.path.expanduser('~/cloud_speech.json')


class _CloudSpeechRecognizer(object):
    """A speech recognizer backed by the Google CloudSpeech APIs.
    """

    def __init__(self, credentials_file):
        self._request = aiy._apis._speech.CloudSpeechRequest(credentials_file)
        self._recorder = aiy.audio.get_recorder()
        self._hotwords = []

    def recognize(self):
        """Recognizes the user's speech and transcript it into text.

        This function listens to the user's speech via the VoiceHat speaker. Then it
        contacts Google CloudSpeech APIs and returns a textual transcript if possible.
        If hotword list is populated this method will only respond if hotword is said.
        """
        self._request.reset()
        self._request.set_endpointer_cb(self._endpointer_callback)
        self._recorder.add_processor(self._request)
        text = self._request.do_request().transcript
        if self._hotwords and text:
            text = text.lower()
            loc_min = len(text)
            hotword_found = ''
            for hotword in self._hotwords:
                loc_temp = text.find(hotword)
                if loc_temp > -1 and loc_min > loc_temp:
                    loc_min = loc_temp
                    hotword_found = hotword
            if hotword_found:
                parse_text = text.split(hotword_found)[1]
                return parse_text.strip()
            else:
                return ''
        else:
            return '' if self._hotwords else text

    def expect_hotword(self, hotword_list):
        """Enables hotword detection for a selected list
        This method is optional and populates the list of hotwords
        to be used for hotword activation.

        For example, to create a recognizer for Google:

        recognizer.expect_hotword('Google')
        recognizer.expect_hotword(['Google','Raspberry Pi'])
        """
        if isinstance(hotword_list, list):
            for hotword in hotword_list:
                self._hotwords.append(hotword.lower())
        else:
            self._hotwords.append(hotword_list.lower())

    def expect_phrase(self, phrase):
        """Explicitly tells the engine that the phrase is more likely to appear.

        This method is optional and makes speech recognition more accurate
        especially when certain commands are expected.

        For example, a light control system may want to add the following commands:

        recognizer.expect_phrase('light on')
        recognizer.expect_phrase('light off')
        """
        self._request.add_phrase(phrase)

    def _endpointer_callback(self):
        self._recorder.remove_processor(self._request)


def get_recognizer():
    """Returns a recognizer that uses Google CloudSpeech APIs.

    Sample usage:
        button = aiy.voicehat.get_button()
        recognizer = aiy.cloudspeech.get_recognizer()
        while True:
            print('Press the button and speak')
            button.wait_for_press()
            text = recognizer.recognize()
            if 'light on' in text:
                turn_on_light()
            elif 'light off' in text:
                turn_off_light()
    """
    global _cloudspeech_recognizer
    if not _cloudspeech_recognizer:
        _cloudspeech_recognizer = _CloudSpeechRecognizer(CLOUDSPEECH_CREDENTIALS_FILE)
    return _cloudspeech_recognizer
