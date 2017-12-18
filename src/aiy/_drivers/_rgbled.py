# Copyright 2017 Google Inc.
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
"""RGB LED driver for the vision bonnet."""


class RGBLED(object):
  """Sets the KTD2026 driver chip to show patterns with the attached RGB LED.

  Simple usage:
    from aiy._drivers._rgbled import RGBLED
    rgbled = RGBLED()
    rgbled.SetAnimation(color=RGBLED.BLUE, pattern=RGBLED.BLINK, rate_hz=4)
  """

  OFF = 0
  ON = 1
  BLINK = 2
  BREATHE = 3

  # These values use a mapping of red, green, blue. Changing the channel map
  # will affect this.
  RED = (0xFF, 0x00, 0x00)
  GREEN = (0x00, 0xFF, 0x00)
  YELLOW = (0xFF, 0xFF, 0x00)
  BLUE = (0x00, 0x00, 0xFF)
  PURPLE = (0xFF, 0x00, 0xFF)
  CYAN = (0x00, 0xFF, 0xFF)
  WHITE = (0xFF, 0xFF, 0xFF)

  ENABLE_OFF = 0
  ENABLE_ON = 1
  ENABLE_PWM1 = 2
  ENABLE_PWM2 = 3

  DEFAULT_CHANNEL_MAP = {'red': 1, 'green': 2, 'blue': 3, 'privacy': 4}

  def __init__(self, channel_map=None, debug=False):
    """Initializes the RGB LED driver.

    Args:
      channel_map: a dictionary of name -> channel number. Determined
        experimentally. Typically this will be red, gree, blue, with the
        values 1, 2, 3, respectively. Defaults to the aforementioned map.
      debug: whether or not to output what is being written raw to the
        various sysfs nodes.
    """
    if channel_map is None:
      self._channel_map = self.DEFAULT_CHANNEL_MAP
    else:
      self._channel_map = channel_map
    self._debug = debug
    self.Reset()

  def __del__(self):
    self.Reset()

  def _MakeChannelPath(self, channel):
    """Generates a ktd202x sysfs node path from a given channel name.

    Args:
      channel: a string naming the channel to select.
    Returns:
      A string containing the base path to the channel's LED class device
      sysfs path.
    """
    return '/sys/class/leds/ktd202x:led%d/' % self._channel_map[channel]

  def _PWriteInt(self, channel, filename, data):
    """Helper method to quickly write a value to a channel sysfs node.

    This is functionally equivalent to the pwrite system call, though does
    not have the same OS semantics.

    Args:
      channel: string, the name of the channel to write to.
      filename: string, the name of the file in the channel's sysfs directory to
        write to.
      data: integer, the value to write to the file.
    """
    path = self._MakeChannelPath(channel) + filename
    if self._debug:
      print('_PWriteInt(channel=%s, file=%s, data=%s)' % (channel, filename,
                                                          data))
    with open(path, 'w') as output:
      output.write('%d\n' % data)

  def SetChannelMapping(self, mapping):
    """Set the channel mapping from color to channel number.

    Args:
      mapping: dictionary of channel name (red, green, blue) to channel
        number (1, 2, 3).
    """
    self._channel_map = mapping

  def EnableChannel(self, channel, enable_state=ENABLE_ON):
    """Sets the enable value for a given channel name.

    Args:
      channel: string, the name of the channel to set the enable bits for.
      enable_state: integer, one of ENABLE_OFF, ENABLE_ON, ENABLE_PWM1, or
        ENABLE_PWM2.
    """
    channel_num = self._channel_map[channel]
    self._PWriteInt(channel, 'device/ch%d_enable' % channel_num, enable_state)

  def SetBrightness(self, channel, brightness):
    """Sets a given channel's brightness value.

    Args:
      channel: string, the name of the channel to set the brightness for.
      brightness: integer, the brightness to set. 255 is brightest.
    """
    self._PWriteInt(channel, 'brightness', brightness)

  def SetFlashPeriod(self, times_per_second):
    """Sets the flash period in Hz for the whole device.

    Args:
      times_per_second: float, the frequency in Hz of how frequently to
        flash the LEDs.
    """
    seconds_per_time = 1 / times_per_second
    period = seconds_per_time * (126 / 16.38)
    if period > 126:
      period = 126
    self._PWriteInt('red', 'device/tflash', period)

  def SetRiseTime(self, time):
    """Sets the rising time for the LED flashing.

    Args:
      time: the amount of time to take to do a rise. Max 15.
    """
    self._PWriteInt('red', 'device/trise', time)

  def SetFallTime(self, time):
    """Sets the falling time for the LED flashing.

    Args:
      time: the amount of time to take to do a fall. Max 15.
    """
    self._PWriteInt('red', 'device/tfall', time)

  def SetPWM1Percentage(self, percentage=1):
    """Sets the percentage of the flash period for PWM1 channels to be on.

    Args:
      percentage: float, from 0.0 to 1.0, percentage of the flash time to
        keep the channels on.
    """
    self._PWriteInt('red', 'device/pwm1', int(255 * percentage))

  def SetPWM2Percentage(self, percentage=1):
    """Sets the percentage of the flash period for PWM2 channels to be on.

    Args:
      percentage: float, from 0.0 to 1.0, percentage of the flash time to
        keep the channels on.
    """
    self._PWriteInt('red', 'device/pwm2', int(255 * percentage))

  def SetColorMix(self, red=0, green=0, blue=0):
    """Sets the solid color mix to display on all three channels.

    Note: this will reset the chip and force it into solid color mode.

    Args:
      red: integer, max 255, the brightness of the red channel.
      green: integer, max 255, the brightness of the green channel.
      blue: integer, max 255, the brightness of the blue channel.
    """
    # self.Reset()
    colors = {'red': red, 'green': green, 'blue': blue}
    for channel_name, color in colors.items():
      self.SetBrightness(channel_name, color)

  def Reset(self):
    """Forces a KTD202x chip reset.
    """
    self._PWriteInt('red', 'device/reset', 1)

  def _SetAnimationPattern(self, pattern=BLINK, rate_hz=1):
    """Helper function to setup the given blink pattern with the given rate.

    Note: resets the chip.

    Args:
      pattern: integer, one of OFF, ON, BLINK, or BREATHE. ON is solid on,
        BLINK is a 50% duty cycle hard blink with no ramps enabled, BREATHE
        is a 30% duty cycle soft blink with ramps set to 5.
      rate_hz: float, the rate in Hz of how often to blink the given
        pattern. Irrelevant for OFF or ON.
    """
    self.Reset()
    if pattern == self.ON:
      self.SetPWM1Percentage(1)
    elif pattern == self.BLINK:
      self.SetFlashPeriod(rate_hz)
      self.SetPWM1Percentage(0.5)
    elif pattern == self.BREATHE:
      self.SetFlashPeriod(rate_hz)
      self.SetRiseTime(5)
      self.SetFallTime(5)
      self.SetPWM1Percentage(0.3)

  def SetAnimation(self, color=RED, pattern=BLINK, rate_hz=1):
    """Sets the given animation for the given color at the given rate.

    Note: resets the chip.

    Args:
      color: tuple, one of RED, GREEN, YELLOW, BLUE, PURPLE, CYAN, WHITE, or
        a tuple of three values signifying which channels to enable (1
        enables, 0 disables) for the given flashing sequence.
      pattern: integer, one of OFF, ON, BLINK, or BREATHE. ON is solid on,
        BLINK is a 50% duty cycle hard blink with no ramps enabled, BREATHE
        is a 30% duty cycle soft blink with ramps set to 5.
      rate_hz: float, the rate in Hz of how often to blink the given
        pattern. Irrelevant for OFF or ON.
    """
    self._SetAnimationPattern(pattern, rate_hz)
    for (color, value) in zip(('red', 'green', 'blue'), color):
      print((color, value))
      state = self.ENABLE_OFF
      if value > 0:
        state = self.ENABLE_PWM1
      self.EnableChannel(color, state)


class PrivacyLED(RGBLED):
  """Wrapper for LED driver to enable/disable privacy LED

  Simple usage:
    from aiy._drivers._rgbled import PrivacyLED
    with PrivacyLED() # Illuminated on entry.
  """

  def __init__(self):
    """Initializes the parent LED driver.

    Configures PWM2 to breathe on the privacy channel.

    """
    super().__init__()

  def __enter__(self):
    """Configures the privacy channel to be fully illuminated."""
    super().EnableChannel(channel='privacy', enable_state=RGBLED.ENABLE_ON)

  def __exit__(self, exc_type, exc_value, exc_tb):
    """On exit, turn off the LED."""
    super().EnableChannel(channel='privacy', enable_state=RGBLED.ENABLE_OFF)
