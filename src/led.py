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
"""Signal states on a LED"""

import logging
import os
import time

import aiy.voicehat
import RPi.GPIO as GPIO

logger = logging.getLogger('led')

CONFIG_DIR = os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
CONFIG_FILES = [
    '/etc/status-led.ini',
    os.path.join(CONFIG_DIR, 'status-led.ini')
]


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    )

    import configargparse
    parser = configargparse.ArgParser(
        default_config_files=CONFIG_FILES,
        description="Status LED daemon"
    )
    parser.add_argument('-G', '--gpio-pin', default=25, type=int,
                        help='GPIO pin for the LED (default: 25)')
    args = parser.parse_args()

    led = None
    state_map = {
        "starting": aiy.voicehat.LED.PULSE_QUICK,
        "ready": aiy.voicehat.LED.BEACON_DARK,
        "listening": aiy.voicehat.LED.ON,
        "thinking": aiy.voicehat.LED.PULSE_QUICK,
        "stopping": aiy.voicehat.LED.PULSE_QUICK,
        "power-off": aiy.voicehat.LED.OFF,
        "error": aiy.voicehat.LED.BLINK_3,
    }
    try:
        GPIO.setmode(GPIO.BCM)

        led = aiy.voicehat.get_led()
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
