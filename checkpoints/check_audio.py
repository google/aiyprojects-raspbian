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

"""Check that the voiceHAT audio input and output are both working."""


import fileinput
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import traceback

import aiy.audio  # noqa
from aiy._drivers._hat import get_aiy_device_name

AIY_PROJECTS_DIR = os.path.dirname(os.path.dirname(__file__))

CARDS_PATH = '/proc/asound/cards'
CARDS_ID = {
    "Voice Hat": "googlevoicehat",
    "Voice Bonnet": "aiy-voicebonnet",
}

STOP_DELAY = 1.0

TEST_SOUND_PATH = '/usr/share/sounds/alsa/Front_Center.wav'

RECORD_DURATION_SECONDS = 3


def get_sound_cards():
    """Read a dictionary of ALSA cards from /proc, indexed by number."""
    cards = {}

    with open(CARDS_PATH) as f:  # pylint: disable=invalid-name
        for line in f.read().splitlines():
            try:
                index = int(line.strip().split()[0])
            except (IndexError, ValueError):
                continue

            cards[index] = line

    return cards


def ask(prompt):
    """Get a yes or no answer from the user."""
    ans = input(prompt + ' (y/n) ')

    while not ans or ans[0].lower() not in 'yn':
        ans = input('Please enter y or n: ')

    return ans[0].lower() == 'y'


def check_voicehat_present():
    """Check that the voiceHAT audio driver is present."""
    card_id = CARDS_ID[get_aiy_device_name()]
    return any(card_id in card for card in get_sound_cards().values())


def check_voicehat_is_first_card():
    """Check that the voiceHAT is the first card on the system."""
    cards = get_sound_cards()
    card_id = CARDS_ID[get_aiy_device_name()]
    return 0 in cards and card_id in cards[0]


def check_asoundrc_is_not_bad():
    """Check that ~/.asoundrc is absent or has the AIY config."""
    asoundrc = os.path.expanduser('~/.asoundrc')
    if not os.path.exists(asoundrc):
        return True

    with open(os.path.join(AIY_PROJECTS_DIR, 'scripts', 'asound.conf')) as f:
        wanted_contents = f.read()
    with open(asoundrc) as f:
        contents = f.read()

    return contents == wanted_contents


def check_speaker_works():
    """Check the speaker makes a sound."""
    print('Playing a test sound...')
    aiy.audio.play_wave(TEST_SOUND_PATH)

    return ask('Did you hear the test sound?')


def check_mic_works():
    """Check the microphone records correctly."""
    temp_file, temp_path = tempfile.mkstemp(suffix='.wav')
    os.close(temp_file)

    try:
        input("When you're ready, press enter and say 'Testing, 1 2 3'...")
        print('Recording...')
        aiy.audio.record_to_wave(temp_path, RECORD_DURATION_SECONDS)
        print('Playing back recorded audio...')
        aiy.audio.play_wave(temp_path)
    finally:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass

    return ask('Did you hear your own voice?')


def do_checks():
    """Run all audio checks and print status."""
    if not check_voicehat_present():
        print(textwrap.fill(
            """Failed to find the voiceHAT soundcard. Refer to HACKING.md for
how to setup the voiceHAT driver: https://git.io/v99yK"""))
        return

    if not check_voicehat_is_first_card():
        print(textwrap.fill(
            """The voiceHAT not the first sound device, so the voice recognizer
may be unable to find it. Please try removing other sound drivers."""))
        return

    try:
        if not check_speaker_works():
            print(textwrap.fill(
                """There may be a problem with your speaker. Check that it's
connected properly."""))
            return
    except BrokenPipeError:
        # aplay crashed - check if ~/.asoundrc is the culprit
        if not check_asoundrc_is_not_bad():
            print(textwrap.fill(
                """~/.asoundrc exists, and it doesn't have the expected
contents. Try deleting it with `rm ~/.asoundrc`."""))
        else:
            print("aplay crashed - try checking your ALSA config.")
        return

    if not check_mic_works():
        print(textwrap.fill(
            """There may be a problem with your microphone. Check that it's
connected properly."""))
        return

    print('The audio seems to be working.')


def main():
    do_checks()


if __name__ == '__main__':
    try:
        main()
        input('Press Enter to close...')
    except Exception:  # pylint: disable=W0703
        traceback.print_exc()
        input('Press Enter to close...')
