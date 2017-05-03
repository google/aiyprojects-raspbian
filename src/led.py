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

'''Signal states on a LED'''

import itertools
import logging
import os
import threading
import time

import RPi.GPIO as GPIO

logger = logging.getLogger('led')

CONFIG_DIR = os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
CONFIG_FILES = [
    '/etc/status-led.ini',
    os.path.join(CONFIG_DIR, 'status-led.ini')
]


class LED:

    """Starts a background thread to show patterns with the LED."""

    def __init__(self, channel):
        self.animator = threading.Thread(target=self._animate)
        self.channel = channel
        self.iterator = None
        self.running = False
        self.state = None
        self.sleep = 0

        GPIO.setup(channel, GPIO.OUT)
        self.pwm = GPIO.PWM(channel, 100)

    def start(self):
        self.pwm.start(0)  # off by default
        self.running = True
        self.animator.start()

    def stop(self):
        self.running = False
        self.animator.join()
        self.pwm.stop()
        GPIO.output(self.channel, GPIO.LOW)

    def set_state(self, state):
        self.state = state

    def _animate(self):
        # TODO(ensonic): refactor or add justification
        # pylint: disable=too-many-branches
        while self.running:
            if self.state:
                if self.state == 'on':
                    self.iterator = None
                    self.sleep = 0.0
                    self.pwm.ChangeDutyCycle(100)
                elif self.state == 'off':
                    self.iterator = None
                    self.sleep = 0.0
                    self.pwm.ChangeDutyCycle(0)
                elif self.state == 'blink':
                    self.iterator = itertools.cycle([0, 100])
                    self.sleep = 0.5
                elif self.state == 'blink-3':
                    self.iterator = itertools.cycle([0, 100] * 3 + [0, 0])
                    self.sleep = 0.25
                elif self.state == 'beacon':
                    self.iterator = itertools.cycle(
                        itertools.chain([30] * 100, [100] * 8, range(100, 30, -5)))
                    self.sleep = 0.05
                elif self.state == 'beacon-dark':
                    self.iterator = itertools.cycle(
                        itertools.chain([0] * 100, range(0, 30, 3), range(30, 0, -3)))
                    self.sleep = 0.05
                elif self.state == 'decay':
                    self.iterator = itertools.cycle(range(100, 0, -2))
                    self.sleep = 0.05
                elif self.state == 'pulse-slow':
                    self.iterator = itertools.cycle(
                        itertools.chain(range(0, 100, 2), range(100, 0, -2)))
                    self.sleep = 0.1
                elif self.state == 'pulse-quick':
                    self.iterator = itertools.cycle(
                        itertools.chain(range(0, 100, 5), range(100, 0, -5)))
                    self.sleep = 0.05
                else:
                    logger.warning("unsupported state: %s", self.state)
                self.state = None
            if self.iterator:
                self.pwm.ChangeDutyCycle(next(self.iterator))
                time.sleep(self.sleep)
            else:
                time.sleep(1)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    )

    import configargparse
    parser = configargparse.ArgParser(
        default_config_files=CONFIG_FILES,
        description="Status LED daemon")
    parser.add_argument('-G', '--gpio-pin', default=25, type=int,
                        help='GPIO pin for the LED (default: 25)')
    args = parser.parse_args()

    led = None
    state_map = {
        "starting": "pulse-quick",
        "ready": "beacon-dark",
        "listening": "on",
        "thinking": "pulse-quick",
        "stopping": "pulse-quick",
        "power-off": "off",
        "error": "blink-3",
    }
    try:
        GPIO.setmode(GPIO.BCM)

        led = LED(args.gpio_pin)
        led.start()
        while True:
            try:
                state = input()
                if not state:
                    continue
                if state not in state_map:
                    logger.warning("unsupported state: %s, must be one of: %s",
                                   state, ",".join(state_map.keys()))
                    continue

                led.set_state(state_map[state])
            except EOFError:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        led.stop()
        GPIO.cleanup()

if __name__ == '__main__':
    main()
