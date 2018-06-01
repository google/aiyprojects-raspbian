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
# Modified By Gilbert Medel on 30May2018

"""A demo of the Google CloudSpeech to recognize System Specs"""

import aiy.audio
import aiy.cloudspeech
import aiy.voicehat
import platform #added platform-identifying data
import webbrowser
def main():
    recognizer = aiy.cloudspeech.get_recognizer()
    recognizer.expect_phrase('turn off the light')
    recognizer.expect_phrase('turn on the light')
    recognizer.expect_phrase('blink')

    button = aiy.voicehat.get_button()
    led = aiy.voicehat.get_led()
    aiy.audio.get_recorder().start()
    response = "" # added variable for storing answer
    

    while True:
        print('Press the button and speak')
        button.wait_for_press()
        print('Listening...')
        text = recognizer.recognize()
        if not text:
            print('Sorry, I did not hear you.')
        else:
            print('You said "', text, '"')
            #turn on the light
            if 'turn on' in text:
                led.set_state(aiy.voicehat.LED.ON)
			#'turn off the light'
            elif 'off' in text:
                led.set_state(aiy.voicehat.LED.OFF)
            elif 'blink' in text:
                led.set_state(aiy.voicehat.LED.BLINK)
            ## System Spec Code
            elif 'python version' in text:
                led.set_state(aiy.voicehat.LED.BLINK)
                response = platform.python_version()
                print("python version: "+ str(response) )
                led.set_state(aiy.voicehat.LED.OFF)
            elif 'Linux version' in text:
                led.set_state(aiy.voicehat.LED.BLINK)
                response = "Linux version: " + str(platform.linux_distribution("distname="))
                print(response)
                aiy.audio.say( response)
                led.set_state(aiy.voicehat.LED.OFF)
            elif 'open web browser' in text:
                webbrowser.open("http://www.google.com")
            elif 'close web browser' in text:
                webbrowser.close()
            elif 'goodbye' in text:
                break


if __name__ == '__main__':
    main()

