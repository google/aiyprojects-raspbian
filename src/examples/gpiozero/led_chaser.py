#!/usr/bin/env python3
"""Demonstrates on board LED support with correct polarity.

Implements simple LED chaser.
"""

from time import sleep
from gpiozero import LED
from aiy.pins import (PIN_A, PIN_B, PIN_C, PIN_D)

leds = (LED(PIN_A), LED(PIN_B), LED(PIN_C), LED(PIN_D))
while True:
    for led in leds:
        led.on()
        sleep(0.5)
        led.off()
