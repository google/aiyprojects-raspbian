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

"""A status UI powered by the LED on the VoiceHat."""

import logging
import os.path

import aiy.audio

# Location of the LED status-ui service's FIFO file.
_LED_FIFO = "/tmp/status-led"

logger = logging.getLogger('status_ui')


class _StatusUi(object):

    """Gives the user status feedback.
    The LED and optionally a trigger sound tell the user when the box is
    ready, listening or thinking.
    """

    def __init__(self, led_fifo=_LED_FIFO):
        self.trigger_sound_wave = None
        if led_fifo and os.path.exists(led_fifo):
            self.led_fifo = led_fifo
        else:
            if led_fifo:
                logger.warning(
                    'File %s specified for --led-fifo does not exist.',
                    led_fifo)
            self.led_fifo = None

    def set_trigger_sound_wave(self, trigger_sound_wave):
        """Sets the trigger sound.
        A trigger sound is played when the status is 'listening' to indicate
        that the assistant is actively listening to the user.
        The trigger_sound_wave argument should be the path to a valid wave file.
        If it is None, the trigger sound is disabled.
        """
        if trigger_sound_wave and os.path.exists(os.path.expanduser(trigger_sound_wave)):
            self.trigger_sound_wave = os.path.expanduser(trigger_sound_wave)
        else:
            if trigger_sound_wave:
                logger.warning(
                    'File %s specified for --trigger-sound does not exist.',
                    trigger_sound_wave)
            self.trigger_sound_wave = None

    def status(self, status):
        """Activate the status.
        For a list of supported statuses, view src/led.py.
        """
        if self.led_fifo:
            with open(self.led_fifo, 'w') as led:
                led.write(status + '\n')
        logger.info('%s...', status)

        if status == 'listening' and self.trigger_sound_wave:
            aiy.audio.play_wave(self.trigger_sound_wave)
