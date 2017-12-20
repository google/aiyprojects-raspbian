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

"""Button driver for the VoiceHat."""

import time
import RPi.GPIO as GPIO


class Button(object):
    """Detect edges on the given GPIO channel."""

    def __init__(self,
                 channel,
                 polarity=GPIO.FALLING,
                 pull_up_down=GPIO.PUD_UP,
                 debounce_time=0.08):
        """A simple GPIO-based button driver.

        This driver supports a simple GPIO-based button. It works by detecting
        edges on the given GPIO channel. Debouncing is automatic.

        Args:
          channel: the GPIO pin number to use (BCM mode)
          polarity: the GPIO polarity to detect; either GPIO.FALLING or
            GPIO.RISING.
          pull_up_down: whether the port should be pulled up or down; defaults to
            GPIO.PUD_UP.
          debounce_time: the time used in debouncing the button in seconds.
        """
        if polarity not in [GPIO.FALLING, GPIO.RISING]:
            raise ValueError(
                'polarity must be one of: GPIO.FALLING or GPIO.RISING')

        self.channel = int(channel)
        self.polarity = polarity
        self.expected_value = polarity == GPIO.RISING
        self.debounce_time = debounce_time

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.IN, pull_up_down=pull_up_down)

        self.callback = None

    def __del__(self):
        GPIO.cleanup(self.channel)

    def wait_for_press(self):
        """Wait for the button to be pressed.

        This method blocks until the button is pressed.
        """
        GPIO.add_event_detect(self.channel, self.polarity)
        while True:
            if GPIO.event_detected(self.channel) and self._debounce():
                GPIO.remove_event_detect(self.channel)
                return
            time.sleep(0.02)

    def on_press(self, callback):
        """Call the callback whenever the button is pressed.

        Args:
          callback: a function to call whenever the button is pressed. It should
            take a single channel number. If the callback is None, the previously
            registered callback, if any, is canceled.

        Example:
          def MyButtonPressHandler(channel):
              print "button pressed: channel = %d" % channel
          my_button.on_press(MyButtonPressHandler)
        """
        GPIO.remove_event_detect(self.channel)
        if callback:
            self.callback = callback
            GPIO.add_event_detect(
                self.channel, self.polarity, callback=self._debounce_and_callback)

    def _debounce_and_callback(self, _):
        if self._debounce():
            self.callback()

    def _debounce(self):
        """Debounce the GPIO signal.

        Check that the input holds the expected value for the debounce
        period, to avoid false trigger on short pulses.
        """
        start = time.time()
        while time.time() < start + self.debounce_time:
            if GPIO.input(self.channel) != self.expected_value:
                return False
            time.sleep(0.01)
        return True
