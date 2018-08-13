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

import aiy.audio
import aiy.cloudspeech

from aiy.leds import Leds
from aiy.leds import Pattern
from aiy.leds import RgbLeds

leds = Leds()

"Choose Led colors here."

RED = (0xFF, 0x00, 0x00)
GREEN = (0x00, 0xFF, 0x00)
YELLOW = (0xFF, 0xFF, 0x00)
BLUE = (0x00, 0x00, 0xFF)
PURPLE = (0xFF, 0x00, 0xFF)
CYAN = (0x00, 0xFF, 0xFF)
WHITE = (0xFF, 0xFF, 0xFF)


def main():
    recognizer = aiy.cloudspeech.get_recognizer()
    recognizer.expect_phrase('turn off the light')
    recognizer.expect_phrase('turn on the light')
    recognizer.expect_phrase('blink')

    button = aiy.voicehat.get_button()
    aiy.audio.get_recorder().start()

    while True:
        print('Press the button and speak')
        button.wait_for_press()
        print('Listening...')
        text = recognizer.recognize()
        if not text:
            print('Sorry, I did not hear you.')
        else:
            print('You said "', text, '"')
            if 'turn on the light' in text:
                leds.update(Leds.rgb_on(WHITE))
            elif 'turn off the light' in text:
                leds.update(Leds.rgb_off())
            elif 'blink' in text:
                leds.pattern = Pattern.blink(500)
                leds.update(Leds.rgb_pattern(WHITE))
            elif 'goodbye' in text:
                break


if __name__ == '__main__':
    main()
