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

from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote_plus, unquote
import xml.etree.ElementTree as ET 

def get_hints(language_code):
    if language_code.startswith('du_'):
        return ('dust')
    return None

def locale_language():
    language, _ = locale.getdefaultlocale()
    return language

def dust(data) :
    with Leds as leds :
        if(0 < int(data) <= 30) :
            aiy.voice.tts.say("Very Good")
            leds.update(Leds.rgb_on(Color.GREEN))
            time.sleep(1)
        elif (30 < int(data) <= 80) :
            aiy.voice.tts.say("So so")
            leds.update(Leds.rgb_on(Color.CYAN))
            time.sleep(1)
        elif (80 < int(data) <= 150) :
            aiy.voice.tts.say("Bad")
            leds.update(Leds.rgb_on(Color.BLUE))
            time.sleep(1)
        else :
            aiy.voice.tts.say("Really Bad")
            leds.update(Leds.rgb_on(Color.PURPLE))
            time.sleep(1)


def find_the_data_from_API() :
    API_key = unquote('8F%2FwcGQo%2F2QFC6E6OSCcsZbiCB2osaGs2pUBFDYE%2FwsXbFe66Fb8RDwxAtm23zsrAT%2BshyxhbKh5S4eD5jp5Rw%3D%3D')
    url = 
    'http://openapi.airkorea.or.kr/openapi/services/rest/ArpltnInforInqireSvc/getCtprvnMesureLIst'
    queryParams = '?' + urlencode({quote_plus('ServiceKey') : API_key, quote_plus('numOfRows') : '10', quote_plus('PageNo') : '1', quote_plus('itemCode') : 'PM10', quote_plus('dataGubun') : 'HOUR', quote_plus('searchCondition') :'MONTH'})

    request = Request(url + queryParams)
    request.get_method = lambda :'Get'
    response_body = urlopen(request).read().decode('utf-8')
    root = ET.fromstring(response_body)

    seoul = root.find('body').find('items').find('item').find('seoul')

    return seoul


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
            if '미세먼지' in text:
                board.led.state = Led.ON
                aiy.voice.tts.say("Today dust condition of Seoul")
                time.sleep(1)
                dust(find_the_data_from_API(), board)
            
            elif '잘가' in text:
                break

if __name__ == '__main__':
    main()
