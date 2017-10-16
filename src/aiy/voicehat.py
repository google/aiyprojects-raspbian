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

"""Drivers for shared functionality provided by the VoiceHat."""

import aiy._drivers._button
import aiy._drivers._led
import aiy._drivers._status_ui

# GPIO definitions (BCM)
_GPIO_BUTTON = 23
_GPIO_LED = 25

# Import LED class to expose the LED constants.
LED = aiy._drivers._led.LED

# Global variables. They are lazily initialized.
_voicehat_button = None
_voicehat_led = None
_status_ui = None


def get_button():
    """Returns a driver to the VoiceHat button.

    The button driver detects edges on _GPIO_BUTTON. It can be used both
    synchronously and asynchrously.

    Synchronous usage:
        button = aiy.voicehat.get_button()
        button.wait_for_press()
        # The above function does not return until the button is pressed.
        my_recognizer.recognize()
        ...

    Asynchronous usage:
        def on_button_press(_):
            print('The button is pressed!')

        button = aiy.voicehat.get_button()
        button.on_press(on_button_press)
        # The console will print 'The button is pressed!' every time the button is
        # pressed.
        ...
        # To cancel the callback, pass None:
        button.on_press(None)
        # Calling wait_for_press() also cancels any callback.
    """
    global _voicehat_button
    if not _voicehat_button:
        _voicehat_button = aiy._drivers._button.Button(channel=_GPIO_BUTTON)
    return _voicehat_button


def get_led():
    """Returns a driver to control the VoiceHat LED light with various animations.

    led = aiy.voicehat.get_led()

    # You may set any LED animation:
    led.set_state(aiy.voicehat.LED.PULSE_QUICK)
    led.set_state(aiy.voicehat.LED.BLINK)

    # Or turn off the light but keep the driver running:
    led.set_state(aiy.voicehat.LED_OFF)
    """
    global _voicehat_led
    if not _voicehat_led:
        _voicehat_led = aiy._drivers._led.LED(channel=_GPIO_LED)
        _voicehat_led.start()
    return _voicehat_led


def get_status_ui():
    """Returns a driver to control the LED via statuses.

    The supported statuses are:
      - "starting"
      - "ready"
      - "listening"
      - "thinking"
      - "stopping"
      - "power-off"
      - "error"

    Optionally, a sound may be played once when the status changes to
    "listening". For example, if you have a wave file at ~/ding.wav, you may set
    the trigger sound by:
    aiy.voicehat.get_status_ui().set_trigger_sound_wave('~/ding.wav')

    To set the status, use:
    aiy.voicehat.get_status_ui().set_state('starting')
    aiy.voicehat.get_status_ui().set_state('thinking')
    """
    global _status_ui
    if not _status_ui:
        _status_ui = aiy._drivers._status_ui._StatusUi()
    return _status_ui
