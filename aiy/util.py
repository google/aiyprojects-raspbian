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

import itertools
import queue
import threading
import time

from collections import namedtuple

from RPi import GPIO

class Button:
    """ An interface for the button connected to the AIY board's
    button connector."""
    @staticmethod
    def _trigger(event_queue, callback):
        try:
            while True:
                event_queue.get_nowait().set()
        except queue.Empty:
            pass

        if callback:
            callback()

    def _run(self):
        when_pressed = 0.0
        pressed = False
        while not self._done.is_set():
            now = time.monotonic()
            if now - when_pressed > self._debounce_time:
                if GPIO.input(self._channel) == self._expected:
                    if not pressed:
                        pressed = True
                        when_pressed = now
                        self._trigger(self._pressed_queue, self._pressed_callback)
                else:
                    if pressed:
                        pressed = False
                        self._trigger(self._released_queue, self._released_callback)
            self._done.wait(0.05)

    def __init__(self, channel, edge='falling', pull_up_down='up',
                 debounce_time=0.08):
        if pull_up_down not in ('up', 'down'):
            raise ValueError('Must be "up" or "down"')

        if edge not in ('falling', 'rising'):
            raise ValueError('Must be "falling" or "rising"')

        self._channel = channel
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.IN,
                   pull_up_down={'up': GPIO.PUD_UP, 'down': GPIO.PUD_DOWN}[pull_up_down])

        self._pressed_callback = None
        self._released_callback = None

        self._debounce_time = debounce_time
        self._expected = True if edge == 'rising' else False

        self._pressed_queue = queue.Queue()
        self._released_queue = queue.Queue()

        self._done = threading.Event()
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def close(self):
        """Internal method to clean up the object when done."""
        self._done.set()
        self._thread.join()
        GPIO.cleanup(self._channel)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _when_pressed(self, callback):
        self._pressed_callback = callback
    when_pressed = property(None, _when_pressed)
    """A function to run when the button is pressed."""

    def _when_released(self, callback):
        self._released_callback = callback
    when_released = property(None, _when_released)
    """A function to run when the button is released."""

    def wait_for_press(self, timeout=None):
        """Pauses the script until the button is pressed or the timeout is reached.

        Args:
            timeout: Seconds to wait before proceeding. By default, this is ``None``,
                which means wait indefinitely."""
        event = threading.Event()
        self._pressed_queue.put(event)
        return event.wait(timeout)

    def wait_for_release(self, timeout=None):
        """Pauses the script until the button is released or the timeout is reached.

        Args:
            timeout: Seconds to wait before proceeding. By default, this is ``None``,
                which means wait indefinitely."""
        event = threading.Event()
        self._released_queue.put(event)
        return event.wait(timeout)


class Led:
    Config = namedtuple('Config', ['duty_cycles', 'pause'])

    OFF         = Config(duty_cycles=lambda: [0], pause=1.0)
    ON          = Config(duty_cycles=lambda: [100], pause=1.0)
    BLINK       = Config(duty_cycles=lambda: [0, 100], pause=0.5)
    BLINK_3     = Config(duty_cycles=lambda: [0, 100] * 3 + [0, 0],
                         pause=0.25)
    BEACON      = Config(duty_cycles=lambda: itertools.chain([30] * 100,
                                                             [100] * 8,
                                                             range(100, 30, -5)),
                         pause=0.05)
    BEACON_DARK = Config(duty_cycles=lambda: itertools.chain([0] * 100,
                                                             range(0, 30, 3),
                                                             range(30, 0, -3)),
                         pause=0.05)
    DECAY       = Config(duty_cycles=lambda: range(100, 0, -2),
                         pause=0.05)
    PULSE_SLOW  = Config(duty_cycles=lambda: itertools.chain(range(0, 100, 2),
                                                             range(100, 0, -2)),
                         pause=0.1)
    PULSE_QUICK = Config(duty_cycles=lambda: itertools.chain(range(0, 100, 5),
                                                                range(100, 0, -5)),
                         pause=0.05)

    def _run(self):
        while True:
            try:
                state = self._queue.get_nowait()
                if state is None:
                    break
                it = itertools.cycle(state.duty_cycles())
            except queue.Empty:
                pass

            self._pwm.ChangeDutyCycle(int(self._brightness * next(it)))
            self._updated.wait(state.pause)
            self._updated.clear()

    def __init__(self, channel):
        self._brightness = 1.0  # Read and written atomically.
        self._channel = channel
        self._queue = queue.Queue(maxsize=1)
        self._queue.put(self.OFF)
        self._updated = threading.Event()

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(channel, GPIO.OUT)
        self._pwm = GPIO.PWM(channel, 100)
        self._pwm.start(0)

        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def close(self):
        self._queue.put(None)
        self._thread.join()
        self._pwm.stop()
        GPIO.cleanup(self._channel)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        if value < 0.0 or value > 1.0:
            raise ValueError('Brightness must be between 0.0 and 1.0.')
        self._brightness = value

    def _set_state(self, state):
        self._queue.put(state)
        self._updated.set()
    state = property(None, _set_state)
