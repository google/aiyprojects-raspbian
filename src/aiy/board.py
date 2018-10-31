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

import contextlib
import itertools
import queue
import threading
import time

from collections import namedtuple

import RPi.GPIO as GPIO

from aiy.leds import Color, Leds, Pattern

class Button:
    def _run(self):
        pressed = 0.0
        active = False
        while not self._done.is_set():
            now = time.monotonic()
            if now - pressed > self._debounce_time:
                if GPIO.input(self._channel) == self._expected:
                    if not active:
                        active = True
                        pressed = now
                        self._trigger()
                else:
                    active = False
            self._done.wait(0.05)

    def _trigger(self):
        # Release wait_for_press waiters.
        try:
            while True:
                self._pressed.get_nowait().set()
        except queue.Empty:
            pass

        # Call callback.
        callback = self._callback  # Atomic read.
        if callback:
            callback()

    def __init__(self, channel, edge=GPIO.FALLING, pull_up_down=GPIO.PUD_UP,
                 debounce_time=0.08):
        self._callback = None
        self._channel = channel
        self._debounce_time = debounce_time
        self._expected = True if edge == GPIO.RISING else False

        GPIO.setup(channel, GPIO.IN, pull_up_down=pull_up_down)

        self._pressed = queue.Queue()

        self._done = threading.Event()
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def close(self):
        self._done.set()
        self._thread.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _on_press(self, callback):
        self._callback = callback  # Atomic write.
    on_press = property(None, _on_press)

    def wait_for_press(self):
        event = threading.Event()
        self._pressed.put(event)
        event.wait()

class MultiColorLed:
    Config = namedtuple('Config', ['channels', 'pattern'])

    OFF         = Config(channels=lambda color: Leds.rgb_off(),
                         pattern=None)
    ON          = Config(channels=Leds.rgb_on,
                         pattern=None)
    BLINK       = Config(channels=Leds.rgb_pattern,
                         pattern=Pattern.blink(500))
    BLINK_3     = BLINK
    BEACON      = BLINK
    BEACON_DARK = BLINK
    DECAY       = BLINK
    PULSE_SLOW  = Config(channels=Leds.rgb_pattern,
                         pattern=Pattern.breathe(500))
    PULSE_QUICK = Config(channels=Leds.rgb_pattern,
                         pattern=Pattern.breathe(100))

    def _update(self, state, brightness):
        with self._lock:
            if state is not None:
                self._state = state
            if brightness is not None:
                self._brightness = brightness

            color = (int(255 * self._brightness), 0, 0)
            if self._state.pattern:
                self._leds.pattern = self._state.pattern
            self._leds.update(self._state.channels(color))

    def __init__(self, channel):
        self._lock = threading.Lock()
        self._brightness = 1.0  # Read and written atomically.
        self._state = self.OFF
        self._leds = Leds()

    def close(self):
        self._leds.reset()

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
        self._update(state=None, brightness=value)

    def _set_state(self, state):
        self._update(state=state, brightness=None)
    state = property(None, _set_state)



class SingleColorLed:
    Config = namedtuple('Config', ['duty_cycles', 'pause'])

    OFF         = Config(duty_cycles=lambda: [0], pause=1.0)
    ON          = Config(duty_cycles=lambda: [100], pause=1.0)
    BLINK       = Config(duty_cycles=lambda: [0, 100], pause=0.5)
    BLINK_3     = Config(duty_cycles=lambda: [0, 100] * 3 + [0, 0],
                         pause=0.25),
    BEACON      = Config(duty_cycles=lambda: itertools.chain([30] * 100,
                                                             [100] * 8,
                                                             range(100, 30, -5)),
                         pause=0.05)
    BEACON_DARK = Config(duty_cycles=lambda: itertools.chain([0] * 100,
                                                             range(0, 30, 3),
                                                             range(30, 0, -3)),
                         pause=0.05)
    DECAY       = Config(duty_cycles=lambda: range(100, 0, -2),
                         pause=0.05),
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

        self._queue = queue.Queue(maxsize=1)
        self._queue.put(self.OFF)
        self._updated = threading.Event()

        GPIO.setup(channel, GPIO.OUT)
        self._pwm = GPIO.PWM(channel, 100)
        self._pwm.start(0)

        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def close(self):
        self._queue.put(None)
        self._thread.join()
        self._pwm.stop()

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


if Leds.installed():
    Led = MultiColorLed
else:
    Led = SingleColorLed


BUTTON_PIN = 23
LED_PIN = 25

class Board:

    def __init__(self, button_pin=BUTTON_PIN, led_pin=LED_PIN):
        self._button_pin = button_pin
        self._button = None
        self._led = None
        self._led_pin = led_pin
        self._stack = contextlib.ExitStack()
        self._lock = threading.Lock()

        GPIO.setmode(GPIO.BCM)

    def close(self):
        self._stack.close()
        GPIO.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    @property
    def button(self):
        with self._lock:
            if not self._button:
                self._button = self._stack.enter_context(Button(self._button_pin))
            return self._button

    @property
    def led(self):
        with self._lock:
            if not self._led:
                self._led = self._stack.enter_context(Led(self._led_pin))
            return self._led
