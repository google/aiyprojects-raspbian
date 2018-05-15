#!/usr/bin/env python3
"""Demonstrates on board LED support with correct polarity.

Demo will turn on, then off the first LED on the hat.
"""

from time import sleep
from gpiozero import LED
from aiy.pins import LED_1

led = LED(LED_1)
# Alternate turning the LED off and on until the user terminates the example.
while True:
    led.on()
    sleep(1)
    led.off()
    sleep(1)
