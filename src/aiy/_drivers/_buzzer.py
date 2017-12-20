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

"""Buzzer driver."""

import threading
import time
import RPi.GPIO as GPIO


class Buzzer:
    """Controls the buzzer to make some noises for a certain period.

    Simple usage:
        my_buzzer = Buzzer(channel = 22)
        my_buzzer.buzz(30)
    """

    def __init__(self, channel):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.OUT)
        self.pwm = GPIO.PWM(channel, 4000)
        self.buzzing = False
        self.deadline = 0
        self.lock = threading.Lock()
        self.exit = False
        self.daemon = threading.Thread(target=self._daemon, daemon=True)
        self.daemon.start()

    def __del__(self):
        with self.lock:  # pylint: disable=E1129
            self.exit = True
        self.pwm.stop()
        self.daemon.Join()
        GPIO.cleanup(self.channel)

    def buzz(self, seconds):
        with self.lock:
            if not self.buzzing:
                self.pwm.start(50)
                self.buzzing = True
                print('buzz start')
            self.deadline = time.monotonic() + seconds

    def _daemon(self):
        while True:
            with self.lock:  # pylint: disable=E1129
                if self.exit:
                    return
                if self.buzzing and time.monotonic() > self.deadline:
                    self.pwm.stop()
                    self.buzzing = False
                    print('buzz start')
            time.sleep(1)
