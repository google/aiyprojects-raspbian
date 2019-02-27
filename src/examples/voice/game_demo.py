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
import random

from aiy.board import Board, Led
from aiy.cloudspeech import CloudSpeechClient
import aiy.voice.tts

from aiy.leds import (Leds, Pattern, PrivacyLed, RgbLeds, Color)

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

def updown():
    #듣기 위해 setup 해줘야하는 환경을 전역으로 선언해야할 듯 

    int final_ans = random.randint(1,100)
    int count = 1
    aiy.voice.tts.say("Random number from one to one hundred is set")
    aiy.voice.tts.say("Start to guess")
    while True:
        #잘 못 알아 들었을 경우 예외 처리 해야함  
        logging.info('You said: "%d"' % guess_ans)

        #updown 의 경우에는 답을 맞출때까지 끝낼 수 없다고 가정 
        if (guess_ans > final_ans) :
            #leds.update(Leds.rgb_on(Color.RED))
            #board.led.state = Led.BLINK
            aiy.voice.tts.say("Up")
            count ++


        elif (guess_ans < final_ans) :
            #leds.update(Leds.rgb_on(Color.RED))
            #board.led.state = Led.BLINK
            aiy.voice.tts.say("Down")
            count ++

        elif (guess_ans == final_ans) :
            #leds.update(Leds.rgb_on(Color.BLUE))
            #board.led.state = Led.BLINK
            aiy.voice.tts.say("Correct answer")
            aiy.voice.tts.say("You are correct by %d times", count)
            break
	


def gugudan():
    while True: #일단 2~15단 안에서???
        n1 = random.randint(2,15)
        n2 = random.randint(2,15)
        ans = n1*n2

         #n1곱하기n2는? 이라고 말해야하는데 저 숫자 어떻게말하지
        aiy.voice.tts.say("")

        logging.info('You said: "%s"' % text)
        text = text.lower()

        if '그만' in text:
            break
        
        elif text==ans: #이거도 어떻게.....??
            leds.update(Leds.rgb_on(Color.BLUE))
            board.led.state = Led.BLINK
            aiy.voice.tts.say("Correct answer")

        else:
            leds.update(Leds.rgb_on(Color.RED))
            board.led.state = Led.BLINK
            aiy.voice.tts.say("Wrong answer")

def deohagi():
    while True:
        n1 = random.randint(1,999)
        n2 = random.randint(1,999)
        ans = n1+n2

         #n1더하기n2는?
        aiy.voice.tts.say("")

        logging.info('You said: "%s"' % text)
        text = text.lower()

        if '그만' in text:
            break
        
        elif text==ans:
            leds.update(Leds.rgb_on(Color.BLUE))
            board.led.state = Led.BLINK
            aiy.voice.tts.say("Correct answer")

        else:
            leds.update(Leds.rgb_on(Color.RED))
            board.led.state = Led.BLINK
            aiy.voice.tts.say("Wrong answer")


def main():
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Assistant service example.')
    parser.add_argument('--language', default='ko-KR')
    args = parser.parse_args()

    logging.info('Initializing for language %s...', args.language)
    hints = get_hints(args.language)
    client = CloudSpeechClient()
    with Board() as board:
        while True:
            if hints:
                logging.info('Say something, e.g. %s.' % ', '.join(hints))
            else:
                logging.info('Say something.')
            text = client.recognize(language_code=args.language,
                                    hint_phrases=hints)
            if text is None:
                logging.info('You said nothing.')
                continue

            logging.info('You said: "%s"' % text)
            text = text.lower()
            if '구구단' in text:
                leds.update(Leds.rgb_on(Color.GREEN))
                #board.led.state = Led.ON
                aiy.voice.tts.say("Start gugudan")
                time.sleep(1)
                gugudan()
            elif '더하기' in text:
                leds.update(Leds.rgb_on(Color.PURPLE))
                #board.led.state = Led.ON
                aiy.voice.tts.say("Start deohagi")
                time.sleep(1)
                deohagi()
            elif '업다운' in text:
                leds.update(Leds.rgb_on(Color.YELLOW))
                #board.led.state = Led.ON
                aiy.voice.tts.say("Start updown")
                time.sleep(1)
				updown()
            elif '잘가' in text:
                break

if __name__ == '__main__':
    main()
