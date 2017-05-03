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

"""Detect edges on the given GPIO channel."""

import time

import RPi.GPIO as GPIO

from triggers.trigger import Trigger


class GpioTrigger(Trigger):

    """Detect edges on the given GPIO channel."""

    DEBOUNCE_TIME = 0.05

    def __init__(self, channel, polarity=GPIO.FALLING,
                 pull_up_down=GPIO.PUD_UP):
        super().__init__()

        self.channel = channel
        self.polarity = polarity

        if polarity not in [GPIO.FALLING, GPIO.RISING]:
            raise ValueError('polarity must be GPIO.FALLING or GPIO.RISING')

        self.expected_value = polarity == GPIO.RISING
        self.event_detect_added = False

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.IN, pull_up_down=pull_up_down)

    def start(self):
        if not self.event_detect_added:
            GPIO.add_event_detect(self.channel, self.polarity, callback=self.debounce)
            self.event_detect_added = True

    def debounce(self, _):
        """Check that the input holds the expected value for the debounce period,
        to avoid false trigger on short pulses."""

        start = time.time()
        while time.time() < start + self.DEBOUNCE_TIME:
            if GPIO.input(self.channel) != self.expected_value:
                return
            time.sleep(0.01)

        self.callback()
