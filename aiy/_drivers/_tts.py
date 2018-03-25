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

"""Wrapper around a TTS system."""

import functools
import logging
import os
import subprocess
import tempfile
from aiy import i18n

# Path to a tmpfs directory to avoid SD card wear
TMP_DIR = '/run/user/%d' % os.getuid()

logger = logging.getLogger('tts')


def create_say(player):
    """Return a function say(words) for the given player."""
    lang = i18n.get_language_code()
    return functools.partial(say, player, lang=lang)


def say(player, words, lang='en-US', volume=60, pitch=130):
    """Say the given words with TTS.

    Args:
      player: To play the text-to-speech audio.
      words: string to say aloud.
      lang: language for the text-to-speech engine.
      volume: volume for the text-to-speech engine.
      pitch: pitch for the text-to-speech engine.
    """
    try:
        (fd, tts_wav) = tempfile.mkstemp(suffix='.wav', dir=TMP_DIR)
    except IOError:
        logger.exception('Using fallback directory for TTS output')
        (fd, tts_wav) = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    words = '<volume level="' + str(volume) + '"><pitch level="' + str(pitch) + \
            '">' + words + '</pitch></volume>'
    try:
        subprocess.call(['pico2wave', '--lang', lang, '-w', tts_wav, words])
        player.play_wav(tts_wav)
    finally:
        os.unlink(tts_wav)


def _main():
    import argparse
    from aiy import audio

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Test TTS wrapper')
    parser.add_argument('words', nargs='*', help='Words to say')
    args = parser.parse_args()

    if args.words:
        words = ' '.join(args.words)
        player = audio.get_player()
        create_say(player)(words)


if __name__ == '__main__':
    _main()
