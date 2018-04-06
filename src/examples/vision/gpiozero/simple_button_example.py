#!/usr/bin/env python3
"""Example code that demonstrates using a standard pin along with a hat pin.

The button uses a standard GPIO pin through the raspberry pi's memory mapped io,
while the led uses the hat's sysfs driver. This implemenation difference is
transparent to the user.

The demo will light up the on board LED whenever the user presses the button.
"""
from gpiozero import Button
from gpiozero import LED
from aiy.pins import BUTTON_GPIO_PIN
from aiy.pins import LED_1

# Set up a gpiozero LED using the first onboard LED on the vision hat.
led = LED(LED_1)
# Set up a gpiozero Button using the button included with the vision hat.
button = Button(BUTTON_GPIO_PIN)

while True:
    if button.is_pressed:
        led.on()
    else:
        led.off()
