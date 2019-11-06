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

"""
APIs to control the RGB LED in the button that connects to the
Vision/Voice Bonnet, and the privacy LED with the Vision Kit.

These APIs are **not compatible** with the Voice HAT (V1 Voice Kit).
To control the Voice HAT's button LED, instead use :class:`aiy.board.Led`.

For example, here's how to blink the button's red light::

    import time
    from aiy.leds import Leds, Color

    with Leds() as leds:
        for _ in range(4):
            leds.update(Leds.rgb_on(Color.RED))
            time.sleep(1)
            leds.update(Leds.rgb_off())
            time.sleep(1)

For more examples, see `leds_example.py
<https://github.com/google/aiyprojects-raspbian/blob/aiyprojects/src/examples/leds_example.py>`_.

These APIs are only for the RGB LED in the button and the Vision Kit's privacy LED.
To control LEDs you've attached to the bonnet's GPIO pins or the LEDs named
``LED_1`` and ``LED_2`` on the Vision/Voice Bonnet, instead use :mod:`aiy.pins`.
"""

import math
import os

_DEVICE_PATH = '/sys/class/leds/ktd202x:led1/device/'

def _tflash_reg(duration_ms):
    if duration_ms <= 128:
        return 0
    if duration_ms <= 384:
        return 1
    return min((int(round(duration_ms / 128))) - 2, 126)


def _pwm1_reg(percent):
    return int(round(256.0 * percent))


def _trise_tfall_reg(duration_ms):
    if duration_ms <= 1.5:
        return 0
    return min(int(round(duration_ms / 96)), 15)


def _write(path, data):
    with open(path, 'w') as f:
        f.write(str(data))


def _device_file(prop):
    return os.path.join(_DEVICE_PATH, prop)

class Color:
    """Defines colors as RGB tuples that can be used as color values with
    :class:`Leds`.
    """
    @staticmethod
    def blend(color_a, color_b, alpha):
        """Creates a color that is a blend between two colors.

        Args:
            color_a: One of two colors to blend.
            color_b: One of two colors to blend.
            alpha: The alpha blend to apply between ``color_a`` and
                ``color_b``, from 0.0 to 1.0, respectively. That is,
                0.0 makes ``color_a`` transparent so only ``color_b`` is
                visible; 0.5 blends the two colors evenly; 1.0 makes
                ``color_b`` transparent so  only ``color_a`` is visible.
        Returns:
            An RGB tuple.
        """
        return tuple([math.ceil(alpha * color_a[i] + (1.0 - alpha) * color_b[i]) for i in range(3)])

    BLACK  = (0x00, 0x00, 0x00)
    RED    = (0xFF, 0x00, 0x00)
    GREEN  = (0x00, 0xFF, 0x00)
    YELLOW = (0xFF, 0xFF, 0x00)
    BLUE   = (0x00, 0x00, 0xFF)
    PURPLE = (0xFF, 0x00, 0xFF)
    CYAN   = (0x00, 0xFF, 0xFF)
    WHITE  = (0xFF, 0xFF, 0xFF)


class Pattern:
    r"""Defines an LED blinking pattern. Pass an instance of this to
    :attr:`Leds.pattern`.

    Args:
        period_ms: The period of time (in milliseconds) for each on/off
            sequence.
        on_percent: Percent of time during the period to turn on the LED
            (the LED turns on at the beginning of the period).
        rise_ms: Duration of time to fade the light on.
        fall_ms: Duration of time to fade the light off.

    The parameters behave as illustrated below.

    .. code-block:: text

        rise_ms /----------\ fall_ms
               /            \
              /  on_percent  \
             #--------------------------------#
                          period_ms

    """

    def __init__(self, period_ms, on_percent=0.5, rise_ms=0, fall_ms=0):
        if on_percent < 0 or on_percent > 0.996:
            raise ValueError('on_percent must be in the range [0..0.996]')

        if period_ms < 0 or rise_ms < 0 or fall_ms < 0:
            raise ValueError('durations must be non-negative')

        self.period_ms = period_ms
        self.on_percent = on_percent
        self.rise_ms = rise_ms
        self.fall_ms = fall_ms

    @staticmethod
    def blink(period_ms):
        """Convenience method to create a blinking pattern.

        Args:
            period_ms: The period of time (in milliseconds) for each on/off
                sequence.
        Returns:
            A :class:`Pattern`.
        """
        return Pattern(period_ms, 0.5)

    @staticmethod
    def breathe(period_ms):
        """Convenience method to create a breathing pattern (a blink that fades
        in and out).

        Args:
            period_ms: The period of time (in milliseconds) for each on/off
                sequence.
        Returns:
            A :class:`Pattern`.
        """
        return Pattern(period_ms, 0.3, period_ms * 0.3, period_ms * 0.3)


class Leds:
    """Class to control the KTD LED driver chip in the button used with the
    Vision and Voice Bonnet.
    """
    class Channel:
        """Defines the configuration for each channel in the KTD LED driver.

        You should not instantiate this class directly; instead create a
        dictionary of ``Channel`` objects with the other methods below,
        which you can then pass to :meth:`~Leds.update`.

        Args:
            state: Either :attr:`ON`, :attr:`OFF`, or
                :attr:`PATTERN`.
            brightness: A value between 0 and 255.
        """
        OFF = 0
        ON = 1
        PATTERN = 2

        def __init__(self, state, brightness):
            if state not in (self.ON, self.OFF, self.PATTERN):
                raise ValueError('state must be OFF, ON, or PATTERN')

            if brightness < 0 or brightness > 255:
                raise ValueError('brightness must be in the range [0..255]')

            self.state = state
            self.brightness = brightness

    @staticmethod
    def rgb(state, rgb):
        """Creates a configuration for the RGB channels: 1 (red), 2 (green), 3 (blue).

        Generally, you should instead use convenience constructors such as
        :func:`rgb_on` and :func:`rgb_pattern`.

        Args:
            state: Either :attr:`Channel.ON`, :attr:`Channel.OFF`, or
                :attr:`Channel.PATTERN`.
            rgb: Either one of the :class:`Color` constants or your own tuple
                of RGB values.
        Returns:
            A dictionary of 3 :class:`Channel` objects, representing red, green,
            and blue values.
        """
        return {i + 1 : Leds.Channel(state, rgb[i]) for i in range(3)}

    @staticmethod
    def rgb_off():
        """Creates an "off" configuration for the button's RGB LED.

        Returns:
            A dictionary of 3 :class:`Channel` objects, representing red,
            green, and blue values, all turned off.
        """
        return Leds.rgb(Leds.Channel.OFF, Color.BLACK)

    @staticmethod
    def rgb_on(rgb):
        """Creates an "on" configuration for the button's RGB LED.

        Args:
            rgb: Either one of the :class:`Color` constants or your own tuple
                of RGB values.
        Returns:
            A dictionary of 3 :class:`Channel` objects, representing red,
            green, and blue values.
        """
        return Leds.rgb(Leds.Channel.ON, rgb)

    @staticmethod
    def rgb_pattern(rgb):
        """Creates a "pattern" configuration for the button's RGB LED, using
        the light pattern set with :attr:`pattern` and the color set here.
        For example::

            with Leds() as leds:
                leds.pattern = Pattern.blink(500)
                leds.update(Leds.rgb_pattern(Color.RED))
                time.sleep(5)

        Args:
            rgb: Either one of the :class:`Color` constants or your own tuple
                of RGB values.
        Returns:
            A dictionary of 3 :class:`Channel` objects, representing red,
            green, and blue values.
        """
        return Leds.rgb(Leds.Channel.PATTERN, rgb)

    @staticmethod
    def privacy(enabled, brightness=255):
        """Creates a configuration for the privacy LED (channel 4).

        You can instead use :meth:`privacy_on` and :meth:`privacy_off`.

        Args:
            enabled: ``True`` to turn on the light; ``False`` to turn it off.
            brightness: A value from 0 to 255.
        Returns:
            A dictionary with one :class:`Channel` for the privacy LED
            (channel 4).
        """
        if enabled:
            return {4: Leds.Channel(Leds.Channel.ON, brightness)}

        return {4: Leds.Channel(Leds.Channel.OFF, 0)}

    @staticmethod
    def privacy_on(brightness=255):
        """Creates an "on" configuration for the privacy LED
        (the front LED on the Vision Kit).

        Args:
            brightness: A value from 0 to 255.
        Returns:
            A dictionary with one :class:`Channel` for the privacy LED
            (channel 4).
        """
        return Leds.privacy(True, brightness)

    @staticmethod
    def privacy_off():
        """Creates an "off" configuration for the privacy LED
        (the front LED on the Vision Kit).

        Returns:
            A dictionary with one :class:`Channel` for the privacy LED
            (channel 4).
        """
        return Leds.privacy(False, 0)

    @staticmethod
    def installed():
        """Internal method to verify the ``Leds`` class is available."""
        return os.path.exists(_DEVICE_PATH)

    def __init__(self, reset=True):
        if not Leds.installed():
            raise RuntimeError('Leds are not available on this board.')

        self._pattern = None
        if reset:
            self.reset()

    def reset(self):
        """Resets the LED driver to a clean state."""
        _write(_device_file('reset'), 1)

    @property
    def pattern(self):
        """Defines a blink pattern for the button's LED. Must be set with a
        :class:`Pattern` object. For example::

            with Leds() as leds:
                leds.pattern = Pattern.blink(500)
                leds.update(Leds.rgb_pattern(Color.RED))
                time.sleep(5)

        """
        return self._pattern

    @pattern.setter
    def pattern(self, value):
        self._pattern = value
        command = 'tflash=%d;pwm1=%d;trise=%d;tfall=%d;' % (
            _tflash_reg(value.period_ms),
            _pwm1_reg(value.on_percent),
            _trise_tfall_reg(value.rise_ms),
            _trise_tfall_reg(value.fall_ms))
        _write(_device_file('registers'), command)

    def update(self, channels):
        """Changes the state of an LED. Takes a dictionary of LED channel
        configurations, provided by various methods such as
        :meth:`rgb_on`, :meth:`rgb_off`, and :meth:`rgb_pattern`.

        For example, turn on the red light::

            with Leds() as leds:
                leds.update(Leds.rgb_on(Color.RED))
                time.sleep(2)
                leds.update(Leds.rgb_off())

        Or turn on the privacy LED (Vision Kit only)::

            with Leds() as leds:
                leds.update(Leds.privacy_on())
                time.sleep(2)
                leds.update(Leds.privacy_off())

        Args:
            channels: A dictionary of one or more :class:`Channel` objects.
                Use the ``rgb_`` and ``privacy_`` methods to create a
                dictionary.
        """
        command = ''
        for index, channel in channels.items():
            if channel.brightness is not None:
                command += 'led%d=%d;' % (index, channel.brightness)
            if channel.state is not None:
                command += 'ch%d_enable=%d;' % (index, channel.state)
        if command:
            _write(_device_file('registers'), command)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.reset()


class PrivacyLed:
    """Helper class to turn Privacy LED off automatically.

    When instantiated, the privacy LED turns on. It turns off whenever
    the code exits the scope in which this was created. For example::

        # Turn the privacy LED on for 2 seconds
        with PrivacyLed(Leds()):
            time.sleep(2)

    Args:
        leds: An instance of :class:`Leds`.
        brightness: A value between 0 and 255.
    """

    def __init__(self, leds, brightness=32):
        self._leds = leds
        self._brightness = brightness

    def __enter__(self):
        self._leds.update(Leds.privacy_on(self._brightness))

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._leds.update(Leds.privacy_off())


class RgbLeds:
    """Helper class to turn RGB LEDs off automatically.

    When instantiated, the privacy LED turns on. It turns off whenever
    the code exits the scope in which this was created. For example::

        # Turn on the green LED for 2 seconds
        with RgbLeds(Leds(), Leds.rgb_on(Color.GREEN)):
            time.sleep(2)

    Args:
        leds: An instance of :class:`Leds`.
        channels: A dictionary of one or more :class:`Channel` objects.
            Use the ``Leds.rgb_`` and ``Leds.privacy_`` methods to create a
            dictionary.

    """

    def __init__(self, leds, channels):
        self._leds = leds
        self._channels = channels

    def __enter__(self):
        self._leds.update(self._channels)

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._leds.update(Leds.rgb_off())
