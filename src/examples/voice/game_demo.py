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

"""A demo of the Google CloudSpeech recognizer."""
import argparse
import locale
import logging
import time

from aiy.cloudspeech import CloudSpeechClient
import aiy.voice.tts
from aiy.leds import (Leds, Pattern, RgbLeds, Color)

from controller.game import (updown, deohagi, gugudan)
import code.game as GAME_CODE


def get_hints(language_code):
    if language_code.startswith('en_'):
        return ('turn on the light',
                'turn off the light',
                'blink the light',
                'goodbye')
    return None


def locale_language():
    language, _ = locale.getdefaultlocale()
    return language


def say(text):
    aiy.voice.tts.say(text)


def recognize (client, hints, language):
    text = None
    while not text:
        if hints:
            logging.info('Say something, e.g. %s.' % ', '.join(hints))
        else:
            logging.info('Say something.')
        text = client.recognize(language_code=language,
                                hint_phrases=hints)
        if text is None:
            logging.info('You said nothing.')

    return text.lower()


def main():
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Assistant service example.')
    parser.add_argument('--language', default='ko-KR')
    args = parser.parse_args()

    logging.info('Initializing for language %s...', args.language)
    hints = get_hints(args.language)
    client = CloudSpeechClient()

    def check_word (t, words):
        return any(word in t for word in words)

    with Leds() as leds:
        def hear():
            return recognize(client, hints, args.language)

        def success():
            leds.update(Leds.rgb_on(Color.BLUE))

        def fail():
            leds.update(Leds.rgb_on(Color.RED))

        while True:
            text = hear()
            logging.info('You said: "%s"' % text)

            if GAME_CODE.MAIN.GUGUDAN in text:
                leds.update(Leds.rgb_on(Color.GREEN))
                say("Start gugudan")
                gugudan(say, hear, success, fail)
            elif GAME_CODE.MAIN.DEOHAGI in text:
                leds.update(Leds.rgb_on(Color.PURPLE))
                say("Start deohagi")
                deohagi(say, hear, success, fail)
            elif GAME_CODE.MAIN.UPDOWN in text:
                leds.update(Leds.rgb_on(Color.YELLOW))
                say("Start updown")
                updown(say, hear, success, fail)
            elif check_word(text, GAME_CODE.MAIN.END):
                break


if __name__ == '__main__':
    main()
