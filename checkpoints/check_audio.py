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

"""Check that the voiceHAT audio input and output are both working.
"""

import os
import subprocess
import tempfile
import textwrap
import time
import traceback

CARDS_PATH = '/proc/asound/cards'
VOICEHAT_ID = 'googlevoicehat'

SERVICE_NAME = 'voice-recognizer'
ACTIVE_STR = 'ActiveState=active'
INACTIVE_STR = 'ActiveState=inactive'

STOP_DELAY = 1.0

VOICE_RECOGNIZER_PATH = os.path.realpath(os.path.join(__file__, '..', '..'))
PYTHON3 = 'python3'
AUDIO_PY = VOICE_RECOGNIZER_PATH + '/src/audio.py'

TEST_SOUND_PATH = '/usr/share/sounds/alsa/Front_Center.wav'

RECORD_DURATION_SECONDS = '3'


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


def is_service_active():
    """Returns True if the voice-recognizer service is active."""
    output = subprocess.check_output(['systemctl', 'show', SERVICE_NAME]).decode('utf-8')

    if ACTIVE_STR in output:
        return True
    elif INACTIVE_STR in output:
        return False
    else:
        print('WARNING: failed to parse output:')
        print(output)
        return False


def play_wav(wav_path):
    """Play a WAV file."""
    subprocess.check_call([PYTHON3, AUDIO_PY, 'play', wav_path],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ask(prompt):
    """Get a yes or no answer from the user."""
    ans = input(prompt + ' (y/n) ')

    while not ans or ans[0].lower() not in 'yn':
        ans = input('Please enter y or n: ')

    return ans[0].lower() == 'y'


def stop_service():
    """Stop the voice-recognizer so we can use the mic.

    Returns:
      True if the service has been stopped.
    """
    if not is_service_active():
        return False

    subprocess.check_call(['sudo', 'systemctl', 'stop', SERVICE_NAME], stdout=subprocess.PIPE)
    time.sleep(STOP_DELAY)
    if is_service_active():
        print('WARNING: failed to stop service, mic may not work.')
        return False

    return True


def start_service():
    """Start the voice-recognizer again."""
    subprocess.check_call(['sudo', 'systemctl', 'start', SERVICE_NAME], stdout=subprocess.PIPE)


def check_voicehat_present():
    """Check that the voiceHAT is present."""

    return any(VOICEHAT_ID in card for card in get_sound_cards().values())


def check_voicehat_is_first_card():
    """Check that the voiceHAT is the first card on the system."""

    cards = get_sound_cards()

    return 0 in cards and VOICEHAT_ID in cards[0]


def check_speaker_works():
    """Check the speaker makes a sound."""
    print('Playing a test sound...')
    play_wav(TEST_SOUND_PATH)

    return ask('Did you hear the test sound?')


def check_mic_works():
    """Check the microphone records correctly."""
    temp_file, temp_path = tempfile.mkstemp(suffix='.wav')
    os.close(temp_file)

    try:
        input("When you're ready, press enter and say 'Testing, 1 2 3'...")
        print('Recording...')
        subprocess.check_call(
            [PYTHON3, AUDIO_PY, 'dump', temp_path,
             '-d', RECORD_DURATION_SECONDS],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('Playing back recorded audio...')
        play_wav(temp_path)
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

    if not check_speaker_works():
        print(textwrap.fill(
            """There may be a problem with your speaker. Check that it's
connected properly."""))
        return

    if not check_mic_works():
        print(textwrap.fill(
            """There may be a problem with your microphone. Check that it's
connected properly."""))
        return

    print('The audio seems to be working.')


def main():
    """Run all checks, stopping the voice-recognizer if necessary."""
    should_restart = stop_service()

    do_checks()

    if should_restart:
        start_service()

if __name__ == '__main__':
    try:
        main()
        input('Press Enter to close...')
    except:  # pylint: disable=bare-except
        traceback.print_exc()
        input('Press Enter to close...')
