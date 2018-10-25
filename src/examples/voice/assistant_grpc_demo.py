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

from aiy.board import Board, Led

def main():
    logging.basicConfig(level=logging.INFO)

    with Board() as board:
        board.led.state = Led.PULSE_QUICK  # Starting.
        assistant = aiy.assistant.grpc.get_assistant()
        with aiy.audio.get_recorder():
            while True:
                board.led.state = Led.BEACON_DARK  # Ready.
                logging.info('Press the button and speak')
                board.button.wait_for_press()
                board.led.state = Led.ON  # Listening.
                logging.info('Listening...')
                text, audio = assistant.recognize()
                if text:
                    if text == 'goodbye':
                        board.led.state = Led.PULSE_QUICK  # Stopping.
                        logging.info('Bye!')
                        break
                    logging.info('You said "%s"', text)
                if audio:
                    aiy.audio.play_audio(audio, assistant.get_volume())


if __name__ == '__main__':
    main()
