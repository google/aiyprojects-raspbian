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

    def __init__(self, channel, polarity=GPIO.FALLING, pull_up_down=GPIO.PUD_UP,
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
        self.debounce_time = debounce_time

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.IN, pull_up_down=pull_up_down)

    def __del__(self):
        GPIO.cleanup(self.channel)

    def wait_for_press(self):
        """Wait for the button to be pressed.

        This method blocks until the button is pressed.
        """
        expected = True if self.polarity == GPIO.RISING else False
        while True:
            GPIO.wait_for_edge(self.channel, self.polarity)
            if GPIO.input(self.channel) == expected:
                time.sleep(self.debounce_time)
                break

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
        expected = True if self.polarity == GPIO.RISING else False

        def gpio_callback(channel):
            if GPIO.input(self.channel) == expected:
                callback()

        GPIO.remove_event_detect(self.channel)
        if callback:
            GPIO.add_event_detect(self.channel, self.polarity, callback=gpio_callback,
                bouncetime=int(self.debounce_time * 1000))
