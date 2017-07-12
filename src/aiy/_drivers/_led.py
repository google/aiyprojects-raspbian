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
"""LED driver for the VoiceHat."""

import itertools
import os
import threading
import time

import RPi.GPIO as GPIO


class LED:
    """Starts a background thread to show patterns with the LED.

  Simple usage:
    my_led = LED(channel = 25)
    my_led.start()
    my_led.set_state(LED_BEACON)
    my_led.stop()
  """

    LED_OFF = 0
    LED_ON = 1
    LED_BLINK = 2
    LED_BLINK_3 = 3
    LED_BEACON = 4
    LED_BEACON_DARK = 5
    LED_DECAY = 6
    LED_PULSE_SLOW = 7
    LED_PULSE_QUICK = 8

    def __init__(self, channel):
        self.animator = threading.Thread(target=self._animate)
        self.channel = channel
        self.iterator = None
        self.running = False
        self.state = None
        self.sleep = 0

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.OUT)
        self.pwm = GPIO.PWM(channel, 100)

        self.lock = threading.Lock()

    def start(self):
        """Starts the LED driver."""
        with self.lock:
            if not self.running:
                self.running = True
                self.pwm.start(0)  # off by default
                self.animator.start()

    def stop(self):
        """Stops the LED driver and sets the LED to off."""
        with self.lock:
            if self.running:
                self.running = False
                self.animator.join()
                self.pwm.stop()

    def set_state(self, state):
        """Sets the LED driver's new state.

    Note the LED driver must be started for this to have any effect.
    """
        with self.lock:
            self.state = state

    def _animate(self):
        while True:
            state = None
            running = False
            with self.lock:
                state = self.state
                self.state = None
                running = self.running
            if not running:
                return
            if state is not None:
                if not self._parse_state(state):
                    raise ValueError('unsupported state: %d' % state)
            if self.iterator:
                self.pwm.ChangeDutyCycle(next(self.iterator))
                time.sleep(self.sleep)
            else:
                # We can also wait for a state change here with a Condition.
                time.sleep(1)

    def _parse_state(self, state):
        self.iterator = None
        self.sleep = 0.0
        if state == self.LED_OFF:
            self.pwm.ChangeDutyCycle(0)
            return True
        if state == self.LED_ON:
            self.pwm.ChangeDutyCycle(100)
            return True
        if state == self.LED_BLINK:
            self.iterator = itertools.cycle([0, 100])
            self.sleep = 0.5
            return True
        if state == self.LED_BLINK_3:
            self.iterator = itertools.cycle([0, 100] * 3 + [0, 0])
            self.sleep = 0.25
            return True
        if state == self.LED_BEACON:
            self.iterator = itertools.cycle(
                itertools.chain([30] * 100, [100] * 8, range(100, 30, -5)))
            self.sleep = 0.05
            return True
        if state == self.LED_BEACON_DARK:
            self.iterator = itertools.cycle(
                itertools.chain([0] * 100, range(0, 30, 3), range(30, 0, -3)))
            self.sleep = 0.05
            return True
        if state == self.LED_DECAY:
            self.iterator = itertools.cycle(range(100, 0, -2))
            self.sleep = 0.05
            return True
        if state == self.LED_PULSE_SLOW:
            self.iterator = itertools.cycle(
                itertools.chain(range(0, 100, 2), range(100, 0, -2)))
            self.sleep = 0.1
            return True
        if state == self.LED_PULSE_QUICK:
            self.iterator = itertools.cycle(
                itertools.chain(range(0, 100, 5), range(100, 0, -5)))
            self.sleep = 0.05
            return True
        return False
