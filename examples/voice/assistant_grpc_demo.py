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

"""A demo of the Google Assistant GRPC recognizer."""

import logging

import aiy.assistant.grpc
import aiy.audio
from aiy.util import Button, LED

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)


def main():
    button = Button(channel=23)
    led = LED(channel=25)
    led.set_state(LED.PULSE_QUICK)
    led.start()

    assistant = aiy.assistant.grpc.get_assistant()
    with aiy.audio.get_recorder():
        while True:
            led.set_state(LED.BEACON_DARK)
            print('Press the button and speak')
            button.wait_for_press()
            led.set_state(LED.ON)
            print('Listening...')
            text, audio = assistant.recognize()
            if text:
                if text == 'goodbye':
                    led.set_state(LED.PULSE_QUICK)
                    print('Bye!')
                    break
                print('You said "', text, '"')
            if audio:
                aiy.audio.play_audio(audio)


if __name__ == '__main__':
    main()
