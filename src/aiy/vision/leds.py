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


def _tflash_reg(duration_ms):
    if duration_ms <= 128:
        return 0
    elif duration_ms <= 384:
        return 1
    else:
        return min((int(round(duration_ms / 128))) - 2, 126)


def _pwm1_reg(percent):
    return int(round(256.0 * percent))


def _trise_tfall_reg(duration_ms):
    if duration_ms <= 1.5:
        return 0
    else:
        return min(int(round(duration_ms / 96)), 15)


def _write(path, data):
    with open(path, 'w') as file:
        file.write(str(data))


def _device_file(prop):
    return '/sys/class/leds/ktd202x:led1/device/%s' % prop

class Pattern(object):
    """Class to define blinking pattern."""
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
        return Pattern(period_ms, 0.5)

    @staticmethod
    def breathe(period_ms):
        return Pattern(period_ms, 0.3, period_ms * 0.3, period_ms * 0.3)


class Leds(object):
    """Class to control KTD LED driver chip."""
    class Channel(object):
        """Configuration of each channel on KTD LED driver."""
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
        """Returns configuration for channels: 1 (red), 2 (green), 3 (blue)."""
        return {
            1: Leds.Channel(state, rgb[0]),
            2: Leds.Channel(state, rgb[1]),
            3: Leds.Channel(state, rgb[2]),
        }

    @staticmethod
    def rgb_off():
        return Leds.rgb(Leds.Channel.OFF, (0, 0, 0))

    @staticmethod
    def rgb_on(rgb):
        return Leds.rgb(Leds.Channel.ON, rgb)

    @staticmethod
    def rgb_pattern(rgb):
        return Leds.rgb(Leds.Channel.PATTERN, rgb)

    @staticmethod
    def privacy(enabled, brightness=255):
        """Returns configuration for channel 4 (privacy)."""
        if enabled:
            return {4: Leds.Channel(Leds.Channel.ON, brightness)}
        else:
            return {4: Leds.Channel(Leds.Channel.OFF, 0)}

    @staticmethod
    def privacy_on(brightness=255):
        return Leds.privacy(True, brightness)

    @staticmethod
    def privacy_off():
        return Leds.privacy(False, 0)

    def __init__(self, reset=True):
        if reset:
            self.reset()

    def reset(self):
        _write(_device_file('reset'), 1)

    @property
    def pattern(self):
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
        command = ''
        for index, channel in channels.items():
            if channel.brightness is not None:
                command += 'led%d=%d;' % (index, channel.brightness)
            if channel.state is not None:
                command += 'ch%d_enable=%d;' % (index, channel.state)
        if command:
            _write(_device_file('registers'), command)


class PrivacyLed(object):
    """Helper class to turn Privacy LED off automatically."""
    def __init__(self, leds, brightness=32):
        self._leds = leds
        self._brightness = brightness

    def __enter__(self):
        self._leds.update(Leds.privacy_on(self._brightness))

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._leds.update(Leds.privacy_off())

class RgbLeds(object):
    """Helper class to turn RGB LEDs off automatically."""
    def __init__(self, leds, channels):
        self._leds = leds
        self._channels = channels

    def __enter__(self):
        self._leds.update(self._channels)

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._leds.update(Leds.rgb_off())
