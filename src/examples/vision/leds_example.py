#!/usr/bin/env python3
# Copyright 2018 Google Inc.
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
import math
import time

from aiy.vision.leds import Leds
from aiy.vision.leds import Pattern
from aiy.vision.leds import PrivacyLed
from aiy.vision.leds import RgbLeds

RED = (0xFF, 0x00, 0x00)
GREEN = (0x00, 0xFF, 0x00)
YELLOW = (0xFF, 0xFF, 0x00)
BLUE = (0x00, 0x00, 0xFF)
PURPLE = (0xFF, 0x00, 0xFF)
CYAN = (0x00, 0xFF, 0xFF)
WHITE = (0xFF, 0xFF, 0xFF)


def blend(color_a, color_b, alpha):
    return tuple([math.ceil(alpha * color_a[i] + (1.0 - alpha) * color_b[i]) for i in range(3)])


leds = Leds()

print('RGB: Solid RED for 1 second')
leds.update(Leds.rgb_on(RED))
time.sleep(1)

print('RGB: Solid GREEN for 1 second')
leds.update(Leds.rgb_on(GREEN))
time.sleep(1)

print('RGB: Solid YELLOW for 1 second')
leds.update(Leds.rgb_on(YELLOW))
time.sleep(1)

print('RGB: Solid BLUE for 1 second')
leds.update(Leds.rgb_on(BLUE))
time.sleep(1)

print('RGB: Solid PURPLE for 1 second')
leds.update(Leds.rgb_on(PURPLE))
time.sleep(1)

print('RGB: Solid CYAN for 1 second')
leds.update(Leds.rgb_on(CYAN))
time.sleep(1)

print('RGB: Solid WHITE for 1 second')
leds.update(Leds.rgb_on(WHITE))
time.sleep(1)

print('RGB: Off for 1 second')
leds.update(Leds.rgb_off())
time.sleep(1)

for _ in range(3):
    print('Privacy: On (brightness=default)')
    leds.update(Leds.privacy_on())
    time.sleep(1)
    print('Privacy: Off')
    leds.update(Leds.privacy_off())
    time.sleep(1)

for _ in range(3):
    print('Privacy: On (brightness=5)')
    leds.update(Leds.privacy_on(5))
    time.sleep(1)
    print('Privacy: Off')
    leds.update(Leds.privacy_off())
    time.sleep(1)

print('Set blink pattern: period=500ms (2Hz)')
leds.pattern = Pattern.blink(500)

print('RGB: Blink RED for 5 seconds')
leds.update(Leds.rgb_pattern(RED))
time.sleep(5)

print('RGB: Blink GREEN for 5 seconds')
leds.update(Leds.rgb_pattern(GREEN))
time.sleep(5)

print('RGB: Blink BLUE for 5 seconds')
leds.update(Leds.rgb_pattern(BLUE))
time.sleep(5)

print('Set breathe pattern: period=1000ms (1Hz)')
leds.pattern = Pattern.breathe(1000)

print('RGB: Breathe RED for 5 seconds')
leds.update(Leds.rgb_pattern(RED))
time.sleep(5)

print('RGB: Breathe GREEN for 5 seconds')
leds.update(Leds.rgb_pattern(GREEN))
time.sleep(5)

print('RGB: Breathe BLUE for 5 seconds')
leds.update(Leds.rgb_pattern(BLUE))
time.sleep(5)

print('RGB: Increase RED brightness for 3.2 seconds')
for i in range(32):
    leds.update(Leds.rgb_on((8 * i, 0, 0)))
    time.sleep(0.1)

print('RGB: Decrease RED brightness for 3.2 seconds')
for i in reversed(range(32)):
    leds.update(Leds.rgb_on((8 * i, 0, 0)))
    time.sleep(0.1)

print('RGB: Blend between GREEN and BLUE for 3.2 seconds')
for i in range(32):
    leds.update(Leds.rgb_on(blend(BLUE, GREEN, i / 32)))
    time.sleep(0.1)

print('RGB: Off for 1 second')
leds.update(Leds.rgb_off())
time.sleep(1)

print('Privacy: On for 2 seconds')
with PrivacyLed(leds):
    time.sleep(2)

print('RGB: Solid GREEN for 2 seconds')
with RgbLeds(leds, Leds.rgb_on(GREEN)):
    time.sleep(2)

print('Custom configuration for 5 seconds')
leds.update({
    1: Leds.Channel(Leds.Channel.PATTERN, 128),  # Red channel
    2: Leds.Channel(Leds.Channel.OFF, 0),        # Green channel
    3: Leds.Channel(Leds.Channel.ON, 128),       # Blue channel
    4: Leds.Channel(Leds.Channel.PATTERN, 64),   # Privacy channel
})
time.sleep(5)

print('Done')
leds.reset()
