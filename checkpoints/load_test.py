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

"""Synthetic load test simillar to running the actual app.
"""

import json
import os
import subprocess
import tempfile
import time
import traceback

if os.path.exists('/home/pi/credentials.json'):
    # Legacy fallback: old location of credentials.
    CREDENTIALS_PATH = '/home/pi/credentials.json'
else:
    CREDENTIALS_PATH = '/home/pi/cloud_speech.json'

SERVICE_NAME = 'voice-recognizer'
ACTIVE_STR = 'ActiveState=active'
INACTIVE_STR = 'ActiveState=inactive'

STOP_DELAY = 1.0

VOICE_RECOGNIZER_PATH = '/home/pi/voice-recognizer-raspi'
PYTHON3 = VOICE_RECOGNIZER_PATH + '/env/bin/python3'
AUDIO_PY = VOICE_RECOGNIZER_PATH + '/src/audio.py'
SPEECH_PY = VOICE_RECOGNIZER_PATH + '/src/speech.py'
SPEECH_PY_ENV = {
    'VIRTUAL_ENV': VOICE_RECOGNIZER_PATH + '/env',
    'PATH': VOICE_RECOGNIZER_PATH + '/env/bin:' + os.getenv('PATH'),
}
TEST_AUDIO = '/usr/share/sounds/alsa/Front_Center.wav'
LED_FIFO = '/tmp/status-led'

RECORD_DURATION_SECONDS = '3'


def check_credentials_valid():
    """Check the credentials are JSON service credentials."""
    try:
        obj = json.load(open(CREDENTIALS_PATH))
    except ValueError:
        return False

    return 'type' in obj and obj['type'] == 'service_account'


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


def check_speech_reco():
    """Try to test the speech reco code from voice-recognizer-raspi."""
    p = subprocess.Popen(  # pylint: disable=invalid-name
        [PYTHON3, SPEECH_PY, TEST_AUDIO], env=SPEECH_PY_ENV,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.communicate()[0].decode('utf-8')

    if p.returncode:
        return False
    else:
        return True


def play_wav():
    """Play a WAV file."""
    subprocess.check_call([PYTHON3, AUDIO_PY, 'play', TEST_AUDIO],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def record_wav():
    """Record a wav file."""
    temp_file, temp_path = tempfile.mkstemp(suffix='.wav')
    os.close(temp_file)
    subprocess.check_call(
        [PYTHON3, AUDIO_PY, 'dump', temp_path,
         '-d', RECORD_DURATION_SECONDS],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


def led_status(status):
    with open(LED_FIFO, 'w') as led:
        led.write(status + '\n')


def run_test():
    print('Running test forever - press Ctrl+C to stop...')
    try:
        while True:
            print('\rrecognizing', end='')
            led_status('listening')
            check_speech_reco()
            time.sleep(0.5)
            print('\rrecording  ', end='')
            led_status('thinking')
            record_wav()
            time.sleep(0.5)
            print('\rplaying    ', end='')
            led_status('ready')
            play_wav()
            time.sleep(0.5)
    except KeyboardInterrupt:
        led_status('power-off')
        print('\nTest finished')


def main():
    """Run all checks and print status."""
    if not os.path.exists(CREDENTIALS_PATH):
        print(
            """Please follow these instructions to get Google Cloud credentials:
https://cloud.google.com/speech/docs/getting-started#set_up_your_project
and save them to""", CREDENTIALS_PATH)
        return

    if not check_credentials_valid():
        print(
            CREDENTIALS_PATH, """is not valid, please check that you have downloaded JSON
service credentials.""")
        return

    should_restart = stop_service()

    run_test()

    if should_restart:
        start_service()


if __name__ == '__main__':
    try:
        main()
        input('Press Enter to close...')
    except:  # pylint: disable=bare-except
        traceback.print_exc()
        input('Press Enter to close...')
