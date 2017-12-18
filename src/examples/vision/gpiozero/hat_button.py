"""Example code that demonstrates using a button connected through the hat.

The button uses a hat pin through the sysfs driver illustrating the edge
detection polling.

The demo will light up the on board LED whenever PIN_D is drawn high.
"""
from signal import pause
from gpiozero import Button
from gpiozero import LED
from aiy.vision.pins import LED_1
from aiy.vision.pins import PIN_D


# Set up a gpiozero LED using the first onboard LED on the vision hat.
led = LED(LED_1)
# Set up a gpiozero Button using the 4th pin on the vision hat expansion.
button = Button(PIN_D)

# When the button is pressed, call the led.on() function (turn the led on)
button.when_pressed = led.on
# When the button is released, call the led.off() function (turn the led off)
button.when_released = led.off

# Wait for the user to kill the example.
pause()
