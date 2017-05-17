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

"""Main recognizer loop: wait for a trigger then perform and handle
recognition."""

import logging
import os
import sys
import threading
import time

import configargparse
from googlesamples.assistant import auth_helpers

import audio
import action
import i18n
import speech
import tts

# =============================================================================
#
# Hey, Makers!
#
# Are you looking for actor.add_keyword? Do you want to add a new command?
# You need to edit src/action.py. Check out the instructions at:
# https://aiyprojects.withgoogle.com/voice/#makers-guide-3-3--create-a-new-voice-command-or-action
#
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger('main')

CACHE_DIR = os.getenv('XDG_CACHE_HOME') or os.path.expanduser('~/.cache')
VR_CACHE_DIR = os.path.join(CACHE_DIR, 'voice-recognizer')

CONFIG_DIR = os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
CONFIG_FILES = [
    '/etc/voice-recognizer.ini',
    os.path.join(CONFIG_DIR, 'voice-recognizer.ini')
]

# Legacy fallback: old locations of secrets/credentials.
OLD_CLIENT_SECRETS = os.path.expanduser('~/client_secrets.json')
OLD_SERVICE_CREDENTIALS = os.path.expanduser('~/credentials.json')

ASSISTANT_CREDENTIALS = os.path.join(VR_CACHE_DIR, 'assistant_credentials.json')
ASSISTANT_OAUTH_SCOPE = 'https://www.googleapis.com/auth/assistant-sdk-prototype'

PID_FILE = '/run/user/%d/voice-recognizer.pid' % os.getuid()


def try_to_get_credentials(client_secrets):
    """Try to get credentials, or print an error and quit on failure."""

    if os.path.exists(ASSISTANT_CREDENTIALS):
        return auth_helpers.load_credentials(
            ASSISTANT_CREDENTIALS, scopes=[ASSISTANT_OAUTH_SCOPE])

    if not os.path.exists(VR_CACHE_DIR):
        os.mkdir(VR_CACHE_DIR)

    if not os.path.exists(client_secrets) and os.path.exists(OLD_CLIENT_SECRETS):
        client_secrets = OLD_CLIENT_SECRETS

    if not os.path.exists(client_secrets):
        print('You need client secrets to use the Assistant API.')
        print('Follow these instructions:')
        print('    https://developers.google.com/api-client-library/python/auth/installed-app'
              '#creatingcred')
        print('and put the file at', client_secrets)
        sys.exit(1)

    if not os.getenv('DISPLAY') and not sys.stdout.isatty():
        print("""
To use the Assistant API, manually start the application from the dev terminal.
See the "Turn on the Assistant API" section of the Voice Recognizer
User's Guide for more info.""")
        sys.exit(1)

    credentials = auth_helpers.credentials_flow_interactive(
        client_secrets, scopes=[ASSISTANT_OAUTH_SCOPE])
    auth_helpers.save_credentials(ASSISTANT_CREDENTIALS, credentials)
    logging.info('OAuth credentials initialized: %s', ASSISTANT_CREDENTIALS)
    return credentials


def create_pid_file(file_name):
    with open(file_name, 'w') as pid_file:
        pid_file.write("%d" % os.getpid())


def main():
    parser = configargparse.ArgParser(
        default_config_files=CONFIG_FILES,
        description="Act on voice commands using Google's speech recognition")
    parser.add_argument('-I', '--input-device', default='default',
                        help='Name of the audio input device')
    parser.add_argument('-O', '--output-device', default='default',
                        help='Name of the audio output device')
    parser.add_argument('-T', '--trigger', default='gpio',
                        help='Trigger to use {\'clap\', \'gpio\'}')
    parser.add_argument('--cloud-speech', action='store_true',
                        help='Use the Cloud Speech API instead of the Assistant API')
    parser.add_argument('-L', '--language', default='en-US',
                        help='Language code to use for speech (default: en-US)')
    parser.add_argument('-l', '--led-fifo', default='/tmp/status-led',
                        help='Status led control fifo')
    parser.add_argument('-p', '--pid-file', default=PID_FILE,
                        help='File containing our process id for monitoring')
    parser.add_argument('--audio-logging', action='store_true',
                        help='Log all requests and responses to WAV files in /tmp')
    parser.add_argument('--assistant-secrets',
                        default=os.path.expanduser('~/assistant.json'),
                        help='Path to client secrets for the Assistant API')
    parser.add_argument('--cloud-speech-secrets',
                        default=os.path.expanduser('~/cloud_speech.json'),
                        help='Path to service account credentials for the '
                        'Cloud Speech API')

    args = parser.parse_args()

    create_pid_file(args.pid_file)
    i18n.set_language_code(args.language, gettext_install=True)

    player = audio.Player(args.output_device)

    if args.cloud_speech:
        credentials_file = os.path.expanduser(args.cloud_speech_secrets)
        if not os.path.exists(credentials_file) and os.path.exists(OLD_SERVICE_CREDENTIALS):
            credentials_file = OLD_SERVICE_CREDENTIALS
        recognizer = speech.CloudSpeechRequest(credentials_file)
    else:
        credentials = try_to_get_credentials(
            os.path.expanduser(args.assistant_secrets))
        recognizer = speech.AssistantSpeechRequest(credentials)

    recorder = audio.Recorder(
        input_device=args.input_device, channels=1,
        bytes_per_sample=speech.AUDIO_SAMPLE_SIZE,
        sample_rate_hz=speech.AUDIO_SAMPLE_RATE_HZ)
    with recorder:
        do_recognition(args, recorder, recognizer, player)


def do_recognition(args, recorder, recognizer, player):
    """Configure and run the recognizer."""
    say = tts.create_say(player)

    actor = action.make_actor(say)

    if args.cloud_speech:
        action.add_commands_just_for_cloud_speech_api(actor, say)

    recognizer.add_phrases(actor)
    recognizer.set_audio_logging_enabled(args.audio_logging)

    if args.trigger == 'gpio':
        import triggers.gpio
        triggerer = triggers.gpio.GpioTrigger(channel=23)
        msg = 'Press the button on GPIO 23'
    elif args.trigger == 'clap':
        import triggers.clap
        triggerer = triggers.clap.ClapTrigger(recorder)
        msg = 'Clap your hands'
    else:
        logger.error("Unknown trigger '%s'", args.trigger)
        return

    mic_recognizer = SyncMicRecognizer(
        actor, recognizer, recorder, player, say, triggerer, led_fifo=args.led_fifo)

    with mic_recognizer:
        if sys.stdout.isatty():
            print(msg + ' then speak, or press Ctrl+C to quit...')

        # wait for KeyboardInterrupt
        while True:
            time.sleep(1)


class SyncMicRecognizer(object):

    """Detects triggers and runs recognition in a background thread.

    This is a context manager, so it will clean up the background thread if the
    main program is interrupted.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, actor, recognizer, recorder, player, say, triggerer, led_fifo):
        self.actor = actor
        self.player = player
        self.recognizer = recognizer
        self.recognizer.set_endpointer_cb(self.endpointer_cb)
        self.recorder = recorder
        self.say = say
        self.triggerer = triggerer
        self.triggerer.set_callback(self.recognize)

        self.running = False

        if led_fifo and os.path.exists(led_fifo):
            self.led_fifo = led_fifo
        else:
            if led_fifo:
                logger.warning(
                    'File %s specified for --led-fifo does not exist.',
                    led_fifo)
            self.led_fifo = None
        self.recognizer_event = threading.Event()

    def __enter__(self):
        self.running = True
        threading.Thread(target=self._recognize).start()
        self.triggerer.start()
        self._status('ready')

    def __exit__(self, *args):
        self.running = False
        self.recognizer_event.set()

        self.recognizer.end_audio()

    def _status(self, status):
        if self.led_fifo:
            with open(self.led_fifo, 'w') as led:
                led.write(status + '\n')
        logger.info('%s...', status)

    def recognize(self):
        if self.recognizer_event.is_set():
            # Duplicate trigger (eg multiple button presses)
            return

        self.recognizer.reset()
        self.recorder.add_processor(self.recognizer)
        self._status('listening')
        # Tell recognizer to run
        self.recognizer_event.set()

    def endpointer_cb(self):
        self.recorder.del_processor(self.recognizer)
        self._status('thinking')

    def _recognize(self):
        while self.running:
            self.recognizer_event.wait()
            if not self.running:
                break

            logger.info('recognizing...')
            action.pauseActors()
            try:
                self._handle_result(self.recognizer.do_request())
            except speech.Error:
                logger.exception('Unexpected error')
                self.say(_('Unexpected error. Try again or check the logs.'))

            self.recognizer_event.clear()
            action.resumeActors()
            self.triggerer.start()
            self._status('ready')

    def _handle_result(self, result):
        if result.transcript and self.actor.handle(result.transcript):
            logger.info('handled local command: %s', result.transcript)
        elif result.response_audio:
            self._play_assistant_response(result.response_audio)
        elif result.transcript:
            logger.warning('%r was not handled', result.transcript)
            self.say(_("I don’t know how to answer that."))
        else:
            logger.warning('no command recognized')
            self.say(_("Could you try that again?"))

    def _play_assistant_response(self, audio_bytes):
        bytes_per_sample = speech.AUDIO_SAMPLE_SIZE
        sample_rate_hz = speech.AUDIO_SAMPLE_RATE_HZ
        logger.info('Playing %.4f seconds of audio...',
                    len(audio_bytes) / (bytes_per_sample * sample_rate_hz))
        self.player.play_bytes(audio_bytes, sample_width=bytes_per_sample,
                               sample_rate=sample_rate_hz)


if __name__ == '__main__':
    main()
