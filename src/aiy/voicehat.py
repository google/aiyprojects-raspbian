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

# GPIO definitions (BCM)
GPIO_BUTTON = 23
GPIO_LED = 25

# Global variables. They are lazily initialized.
voicehat_button = None
voicehat_led = None

def get_button():
  """Returns a driver to the VoiceHat button.

  The button driver detects edges on GPIO_BUTTON. It can be used both
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
  global voicehat_button
  if voicehat_button is None:
    voicehat_button = aiy._drivers._button.Button(channel=GPIO_BUTTON)
  return voicehat_button

# All supported LED animations.
LED_OFF = aiy._drivers._led.LED.LED_OFF
LED_ON = aiy._drivers._led.LED.LED_ON
LED_BLINK = aiy._drivers._led.LED.LED_BLINK
LED_BLINK_3 = aiy._drivers._led.LED.LED_BLINK_3
LED_BEACON = aiy._drivers._led.LED.LED_BEACON
LED_BEACON_DARK = aiy._drivers._led.LED.LED_BEACON_DARK
LED_DECAY = aiy._drivers._led.LED.LED_DECAY
LED_PULSE_SLOW = aiy._drivers._led.LED.LED_PULSE_SLOW
LED_PULSE_QUICK = aiy._drivers._led.LED.LED_PULSE_QUICK

def get_led():
  """Returns a driver to control the VoiceHat LED light with various animations.

  led = aiy.voicehat.get_led()

  # You may set any LED animation:
  led.set_state(aiy.voicehat.LED_PULSE_QUICK)
  led.set_state(aiy.voicehat.LED_BLINK)

  # Or turn off the light but keep the driver running:
  led.set_state(aiy.voicehat.LED_OFF)
  """
  global voicehat_led
  if voicehat_led is None:
    voicehat_led = aiy._drivers._led.LED(channel=GPIO_LED)
    voicehat_led.start()
  return voicehat_led
