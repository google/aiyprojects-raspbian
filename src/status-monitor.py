#!/usr/bin/env python3
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

"""Script to monitor liveness of processes and update led status."""

import argparse
import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger('status-monitor')

PID_FILE = '/run/user/%d/voice-recognizer.pid' % os.getuid()


def get_pid(pid_file):
    try:
        with open(pid_file, 'r') as pid:
            return int(pid.read())
    except IOError:
        return None


def set_led_status(led_fifo):
    with open(led_fifo, 'w') as led:
        led.write('power-off\n')


def check_liveness(pid_file, led_fifo):
    pid = get_pid(pid_file)
    if pid:
        if not os.path.exists("/proc/%d" % pid):
            logger.info("monitored process not running")
            set_led_status(led_fifo)
            try:
                os.unlink(pid_file)
            except IOError:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Monitor liveness of processes and update led status.")
    parser.add_argument('-l', '--led-fifo', default='/tmp/status-led',
                        help='Status led control fifo')
    parser.add_argument('-p', '--pid-file', default=PID_FILE,
                        help='File containing our process id for monitoring')
    args = parser.parse_args()

    while True:
        check_liveness(args.pid_file, args.led_fifo)
        time.sleep(1)


if __name__ == '__main__':
    main()
