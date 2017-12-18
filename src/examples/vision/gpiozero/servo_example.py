"""Demonstrates simultaneous control of two servos on the hat.

One servo uses the simple default configuration, the other servo is tuned to
ensure the full range is reachable.
"""

from time import sleep
from gpiozero import Servo
from aiy.vision.pins import PIN_A
from aiy.vision.pins import PIN_B

# Create a default servo that will not be able to use quite the full range.
simple_servo = Servo(PIN_A)
# Create a servo with the custom values to give the full dynamic range.
tuned_servo = Servo(PIN_B, min_pulse_width=.0005, max_pulse_width=.0019)

# Move the Servos back and forth until the user terminates the example.
while True:
  simple_servo.min()
  tuned_servo.max()
  sleep(1)
  simple_servo.mid()
  tuned_servo.mid()
  sleep(1)
  simple_servo.max()
  tuned_servo.min()
  sleep(1)
