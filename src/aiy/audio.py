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

"""Drivers for audio functionality provided by the VoiceHat."""

import aiy._drivers._player
import aiy._drivers._recorder
import aiy._drivers._tts

AUDIO_SAMPLE_SIZE = 2  # bytes per sample
AUDIO_SAMPLE_RATE_HZ = 16000

# Global variables. They are lazily initialized.
_voicehat_recorder = None
_voicehat_player = None
_status_ui = None


def get_player():
    """Returns a driver to control the VoiceHat speaker.

    The aiy modules automatically use this player. So usually you do not need to
    use this. Instead, use 'aiy.audio.play_wave' if you would like to play some
    audio.
    """
    global _voicehat_player
    if _voicehat_player is None:
        _voicehat_player = aiy._drivers._player.Player()
    return _voicehat_player


def get_recorder():
    """Returns a driver to control the VoiceHat microphones.

    The aiy modules automatically use this recorder. So usually you do not need to
    use this.
    """
    global _voicehat_recorder
    if _voicehat_recorder is None:
        _voicehat_recorder = aiy._drivers._recorder.Recorder()
    return _voicehat_recorder


def play_wave(wave_file):
    """Plays the given wave file.

    The wave file has to be mono and small enough to be loaded in memory.
    """
    player = get_player()
    player.play_wav(wave_file)


def play_audio(audio_data):
    """Plays the given audio data."""
    player = get_player()
    player.play_bytes(audio_data, sample_width=AUDIO_SAMPLE_SIZE, sample_rate=AUDIO_SAMPLE_RATE_HZ)


def say(words, lang=None):
    """Says the given words in the given language with Google TTS engine.

    If lang is specified, e.g. "en-US', it will be used to say the given words.
    Otherwise, the language from aiy.i18n will be used.
    """
    if not lang:
        lang = aiy.i18n.get_language_code()
    aiy._drivers._tts.say(aiy.audio.get_player(), words, lang=lang)


def get_status_ui():
    """Returns a driver to access the StatusUI daemon.

    The StatusUI daemon controls the LEDs in the background. It supports a list
    of statuses it is able to communicate with the LED on the Voicehat.
    """
    global _status_ui
    if _status_ui is None:
        _status_ui = aiy._drivers._StatusUi()
    return _status_ui
