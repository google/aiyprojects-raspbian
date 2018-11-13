#!/usr/bin/env python3
#
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

"""Checks that the AIY sound card is working."""

import os
import tempfile
import time
import traceback

from aiy.voice.audio import AudioFormat, play_wav, record_file

AIY_CARDS = {
    'sndrpigooglevoi': 'Voice HAT (v1)',
    'aiyvoicebonnet': 'Voice Bonnet (v2)'
}

TEST_SOUND_PATH = '/usr/share/sounds/alsa/Front_Center.wav'

RECORD_DURATION_SECONDS = 3

ERROR_NO_SOUND_CARDS = '''
You do not have any sound cards installed. Please check that AIY sound card is
properly connected.

For some Voice HATs (not Voice Bonnets!) you need to add the following line
to /boot/config.txt:

dtoverlay=googlevoicehat-soundcard

To do that simply run from a separate terminal:

echo "dtoverlay=googlevoicehat-soundcard" | sudo tee -a /boot/config.txt

'''

ERROR_NO_AIY_SOUND_CARDS = '''
You have sound cards installed but you do not have any AIY ones. Please check
that AIY sound card is properly connected.
'''

ERROR_NOT_A_FIRST_SOUND_CARD = '''
Your AIY sound card is not a first sound device. The voice recognizer may be
unable to find it. Please try removing other sound drivers.
'''

ERROR_NO_SPEAKER_SOUND = '''
There may be a problem with your speaker. Check that it is connected properly.
'''

ERROR_NO_RECORDED_SOUND = '''
There may be a problem with your microphone. Check that it is connected
properly.
'''

def ask(prompt):
    answer = input('%s (y/n) ' % prompt).lower()
    while answer not in ('y', 'n'):
        answer = input('Please enter y or n: ')
    return answer == 'y'

def error(message):
    print(message.strip())

def find_sound_cards(max_count=16):
    cards = []
    for i in range(max_count):
        path = '/proc/asound/card%d/id' % i
        if not os.path.exists(path):
            break
        with open(path) as f:
            cards.append(f.read().strip())
    return cards


def check_sound_card_present():
    cards = find_sound_cards()
    if not cards:
        error(ERROR_NO_SOUND_CARDS)
        return False

    aiy_cards = set.intersection(set(cards), AIY_CARDS.keys())
    if len(aiy_cards) != 1:
        error(ERROR_NO_AIY_SOUND_CARDS)
        return False

    for card in aiy_cards:
        index = cards.index(card)
        print('You have %s installed at index %d!' % (AIY_CARDS[card], index))
        if index != 0:
            error(ERROR_NOT_A_FIRST_SOUND_CARD)
            return False

    return True

def check_speaker_works():
    print('Playing a test sound...')
    play_wav(TEST_SOUND_PATH)

    if not ask('Did you hear the test sound?'):
        error(ERROR_NO_SPEAKER_SOUND)
        return False

    return True

def check_microphone_works():
    with tempfile.NamedTemporaryFile() as f:
        input('When you are ready, press Enter and say "Testing, 1 2 3"...')
        print('Recording for %d seconds...' % RECORD_DURATION_SECONDS)

        record_file(AudioFormat.CD, filename=f.name, filetype='wav',
                    wait=lambda: time.sleep(RECORD_DURATION_SECONDS))
        print('Playing back recorded audio...')
        play_wav(f.name)

    if not ask('Did you hear your own voice?'):
        error(ERROR_NO_RECORDED_SOUND)
        return False

    return True

def main():
    if not check_sound_card_present():
        return

    if not check_speaker_works():
        return

    if not check_microphone_works():
        return

    print('AIY sound card seems to be working!')

if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
    finally:
        input('Press Enter to close...')
