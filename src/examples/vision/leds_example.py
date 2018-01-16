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

leds = Leds()

# Iterate over different colors
for rgb in (RED, GREEN, YELLOW, BLUE, PURPLE, CYAN, WHITE):
    leds.update(Leds.rgb_on(rgb))
    time.sleep(1)

# Turn rgb off
leds.update(Leds.rgb_off())

# Blink privacy led 3 times
for _ in range(3):
    leds.update(Leds.privacy_on())
    time.sleep(1)
    leds.update(Leds.privacy_off())
    time.sleep(1)

# Blink privacy led 3 times with reduced brightness
for _ in range(3):
    leds.update(Leds.privacy_on(5))
    time.sleep(1)
    leds.update(Leds.privacy_off())
    time.sleep(1)

# Blink one time two times per second (period=500ms, 2Hz)
leds.pattern = Pattern.blink(500)

# Only red led
leds.update(Leds.rgb_pattern(RED))
time.sleep(5)

# Only green led
leds.update(Leds.rgb_pattern(GREEN))
time.sleep(5)

# Only blue led
leds.update(Leds.rgb_pattern(BLUE))
time.sleep(5)

# Change pattern and blink one time per second (period=1000ms, 1Hz)
leds.pattern = Pattern.breathe(1000)

# Only red led
leds.update(Leds.rgb_pattern(RED))
time.sleep(5)

# Only green led
leds.update(Leds.rgb_pattern(GREEN))
time.sleep(5)

# Only blue led
leds.update(Leds.rgb_pattern(BLUE))
time.sleep(5)

# Manually increase red led brightness
for i in range(32):
    leds.update(Leds.rgb_on((8 * i, 0, 0)))
    time.sleep(0.1)

# Manually decrease red led brightness
for i in reversed(range(32)):
    leds.update(Leds.rgb_on((8 * i, 0, 0)))
    time.sleep(0.1)

# Turn on privacy led for 2 seconds
with PrivacyLed(leds):
    time.sleep(2)

# Turn on rgb leds for 2 seconds
with RgbLeds(leds, Leds.rgb_on(RED)):
    time.sleep(2)

# Custom configuration for each channel
leds.update({
    1: Leds.Channel(Leds.Channel.PATTERN, 128),
    2: Leds.Channel(Leds.Channel.OFF, 0),
    3: Leds.Channel(Leds.Channel.ON, 128),
    4: Leds.Channel(Leds.Channel.PATTERN, 64),
})
time.sleep(5)

# Reset and finish
leds.reset()
