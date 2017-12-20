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
import aiy.voicehat

logger = logging.getLogger('status_ui')


class _StatusUi(object):
    """Gives the user status feedback.

    The LED and optionally a trigger sound tell the user when the box is
    ready, listening or thinking.
    """

    def __init__(self):
        self._trigger_sound_wave = None
        self._state_map = {
            "starting": aiy.voicehat.LED.PULSE_QUICK,
            "ready": aiy.voicehat.LED.BEACON_DARK,
            "listening": aiy.voicehat.LED.ON,
            "thinking": aiy.voicehat.LED.PULSE_QUICK,
            "stopping": aiy.voicehat.LED.PULSE_QUICK,
            "power-off": aiy.voicehat.LED.OFF,
            "error": aiy.voicehat.LED.BLINK_3,
        }
        aiy.voicehat.get_led().set_state(aiy.voicehat.LED.OFF)

    def set_trigger_sound_wave(self, trigger_sound_wave):
        """Set the trigger sound.

        A trigger sound is played when the status is 'listening' to indicate
        that the assistant is actively listening to the user.
        The trigger_sound_wave argument should be the path to a valid wave file.
        If it is None, the trigger sound is disabled.
        """
        if not trigger_sound_wave:
            self._trigger_sound_wave = None
            return
        expanded_path = os.path.expanduser(trigger_sound_wave)
        if os.path.exists(expanded_path):
            self._trigger_sound_wave = expanded_path
        else:
            logger.warning(
                'File %s specified as trigger sound does not exist.',
                trigger_sound_wave)
            self._trigger_sound_wave = None

    def status(self, status):
        """Activate the status.

        This method updates the LED animation. Returns True if the status is
        valid and has been updated.
        """
        if status not in self._state_map:
            logger.warning("unsupported state: %s, must be one of %s",
                           status, ",".join(self._state_map.keys()))
            return False
        aiy.voicehat.get_led().set_state(self._state_map[status])
        if status == 'listening' and self._trigger_sound_wave:
            aiy.audio.play_wave(self._trigger_sound_wave)
        return True
