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

import numpy as np
from scipy import signal

import i18n

# Path to a tmpfs directory to avoid SD card wear
TMP_DIR = '/run/user/%d' % os.getuid()

# Expected sample rate from the TTS tool
SAMPLE_RATE = 16000

# Parameters for the equalization filter. These remove low-frequency sound
# from the result, avoiding resonance on the speaker and making the TTS easier
# to understand. Calculated with:
#   python3 src/tts.py --hpf-order 4 --hpf-freq-hz 1400 --hpf-gain-db 4
FILTER_A = np.array([1., -3.28274474, 4.09441957, -2.29386174, 0.48627065])
FILTER_B = np.array([1.10519522, -4.4207809, 6.63117135, -4.4207809, 1.10519522])

logger = logging.getLogger('tts')


def print_eq_coefficients(hpf_order, hpf_freq_hz, hpf_gain_db):
    """Calculate and print the coefficients of the equalization filter."""
    b, a = signal.butter(hpf_order, hpf_freq_hz / SAMPLE_RATE, 'highpass')
    gain_factor = pow(10, hpf_gain_db / 20)

    print('FILTER_A = np.%r' % a)
    print('FILTER_B = np.%r' % (b * gain_factor))


def create_eq_filter():
    """Return a function that applies equalization to a numpy array."""

    def eq_filter(raw_audio):
        return signal.lfilter(FILTER_B, FILTER_A, raw_audio)

    return eq_filter


def create_say(player):
    """Return a function say(words) for the given player, using the default EQ
    filter.
    """
    lang = i18n.get_language_code()
    return functools.partial(say, player, eq_filter=create_eq_filter(), lang=lang)


def say(player, words, eq_filter=None, lang='en-US'):
    """Say the given words with TTS.

    Args:
      player: To play the text-to-speech audio.
      words: string to say aloud.
      eq_filter: function (operates on a numpy int16 array) to equalize audio
      lang: language for the text-to-speech engine.
    """

    try:
        (fd, raw_wav) = tempfile.mkstemp(suffix='.wav', dir=TMP_DIR)
    except IOError:
        logger.exception('Using fallback directory for TTS output')
        (fd, raw_wav) = tempfile.mkstemp(suffix='.wav')

    os.close(fd)

    try:
        subprocess.call(['pico2wave', '--lang', lang, '-w', raw_wav, words])
        subprocess.call(['play', raw_wav, '--no-show-progress', '--guard'])
    finally:
        os.unlink(raw_wav)


def main():
    import argparse

    import aiy.audio

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Test TTS wrapper')
    parser.add_argument('words', nargs='*', help='Words to say')
    parser.add_argument('--hpf-order', type=int, help='Order of high-pass filter')
    parser.add_argument('--hpf-freq-hz', type=int, help='Corner frequency of high-pass filter')
    parser.add_argument('--hpf-gain-db', type=int, help='High-frequency gain of filter')
    args = parser.parse_args()

    if args.words:
        words = ' '.join(args.words)
        player = aiy.audio.Player()
        create_say(player)(words)

    if args.hpf_order:
        print_eq_coefficients(args.hpf_order, args.hpf_freq_hz, args.hpf_gain_db)


if __name__ == '__main__':
    main()
