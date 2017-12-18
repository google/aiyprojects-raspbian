"""Example code that demonstrates using a standard pin along with a hat pin.

The button uses a standard GPIO pin through the raspberry pi's memory mapped io,
while the led uses the hat's sysfs driver. This implemenation difference is
transparent to the user.

The demo will light up the on board LED whenever the user presses the button.
"""
from signal import pause
from gpiozero import Button
from gpiozero import LED
from aiy.vision.pins import BUTTON_GPIO_PIN
from aiy.vision.pins import LED_1

# Set up a gpiozero LED using the first onboard LED on the vision hat.
led = LED(LED_1)
# Set up a gpiozero Button using the button included with the vision hat.
button = Button(BUTTON_GPIO_PIN)

# When the button is pressed, call the led.on() function (turn the led on)
button.when_pressed = led.on
# When the button is released, call the led.off() function (turn the led off)
button.when_released = led.off

# Wait for the user to kill the example.
pause()
