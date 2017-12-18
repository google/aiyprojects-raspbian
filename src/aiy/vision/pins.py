"""Pin definitions for use with gpiozero devices.

Defines pin objects, and overrides the pin factory used by gpiozero devices to
support the pins routed through the hat. Should not disrupt usage of other pins.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from collections import namedtuple
from copy import deepcopy
from os import listdir
import time
from gpiozero import Device
from gpiozero import Factory
from gpiozero import Pin
from gpiozero.exc import GPIOPinInUse
from gpiozero.exc import InputDeviceError
from gpiozero.exc import PinFixedPull
from gpiozero.exc import PinInvalidBounce
from gpiozero.exc import PinInvalidEdges
from gpiozero.exc import PinPWMUnsupported
from gpiozero.exc import PinSetInput
from gpiozero.exc import PinUnsupported
from gpiozero.threads import GPIOThread


def _detect_gpio_offset(module_path):
  for folder in listdir(module_path):
    try:
      with open('%s/%s/base' % (module_path, folder), 'r') as offset:
        return int(offset.read())
    except IOError:
      pass
  return None


_FsNodeSpec = namedtuple('_FsNodeSpec', ['pin', 'name'])


class GpioSpec(_FsNodeSpec):
  _MODULE_PATH = '/sys/bus/i2c/drivers/aiy-io-i2c/1-0051/gpio-aiy-io/gpio'
  _PIN_OFFSET = _detect_gpio_offset(_MODULE_PATH)

  def __new__(cls, pin, name):
    return super(GpioSpec, cls).__new__(cls, GpioSpec._PIN_OFFSET + pin, name)

  def __str__(self):
    return 'gpio %s (%d)' % (self.name, self.pin - self._PIN_OFFSET)


class PwmSpec(_FsNodeSpec):

  def __str__(self):
    return 'pwm %d' % self.pin


AIYPinSpec = namedtuple('AIYPinSpec', ['gpio_spec', 'pwm_spec'])

PIN_A = AIYPinSpec(GpioSpec(2, 'AIY_USER0'), PwmSpec(0, 'pwm0'))
PIN_B = AIYPinSpec(GpioSpec(3, 'AIY_USER1'), PwmSpec(1, 'pwm1'))
PIN_C = AIYPinSpec(GpioSpec(8, 'AIY_USER2'), PwmSpec(2, 'pwm2'))
PIN_D = AIYPinSpec(GpioSpec(9, 'AIY_USER3'), PwmSpec(3, 'pwm3'))
LED_1 = AIYPinSpec(GpioSpec(13, 'AIY_LED0'), None)
LED_2 = AIYPinSpec(GpioSpec(14, 'AIY_LED1'), None)

BUZZER_GPIO_PIN = 22
BUTTON_GPIO_PIN = 23

_NS_PER_SECOND = 1000000000


class SysFsPin(object):
  """Generic SysFsPin which implements generic SysFs driver functionality."""

  def __init__(self, spec, fs_root):
    self._pin = spec.pin
    self._name = spec.name
    self._fs_root = fs_root
    # Ensure things start out unexported.
    try:
      self.unexport()
    except IOError:
      pass

  def set_function(self, function):
    raise NotImplementedError('Setting function not supported')

  def get_function(self):
    raise NotImplementedError('Getting function not supported')

  def export(self):
    try:
      with open(self.root_path('export'), 'w') as export:
        export.write('%d' % self._pin)
    except IOError:
      raise GPIOPinInUse('Pin already in use')

  def unexport(self):
    with open(self.root_path('unexport'), 'w') as unexport:
      unexport.write('%d' % self._pin)

  def open(self):
    self.export()

  def close(self):
    self.unexport()

  def wait_for_permissions(self, prop):
    """Wait for write permissions on the given property.

    We must wait because the the file system needs to grant permissions for the
    newly created node."""
    while True:
      try:
        with open(self.property_path(prop), 'w'):
          pass
        return
      except IOError:
        time.sleep(.01)

  def get_value(self):
    raise NotImplementedError('Value getting not implemented')

  def set_value(self, value):
    raise NotImplementedError('Value setting not implemented')

  def write_property(self, prop, value):
    """Writes the given sysfs node property to the pin."""
    with open(self.property_path(prop), 'w') as node:
      node.write(value)

  def read_property(self, prop):
    """Reads the given sysfs node property from the pin."""
    with open(self.property_path(prop), 'r') as node:
      return node.read()

  def root_path(self, node):
    return '%s/%s' % (self._fs_root, node)

  def property_path(self, prop):
    return '%s/%s/%s' % (self._fs_root, self._name, prop)


class SysFsGpioPin(SysFsPin):
  """SysFs support for GPIO pins.

  Supports the SysFs node for GPIO control.
  """
  _FS_ROOT = '/sys/class/gpio'

  def __init__(self, spec):
    super(SysFsGpioPin, self).__init__(spec, self._FS_ROOT)
    if not isinstance(spec, GpioSpec):
      raise TypeError('Pin specification not compatible with SysFS GPIO')
    self._spec = spec
    self._out = False
    self._value = None

  def _get_direction(self):
    return self.read_property('direction')

  def _set_direction(self, direction):
    if direction not in ('in', 'out'):
      raise ValueError('Direction must be either in or out')
    self.write_property('direction', direction)

  def _get_value(self):
    return self.read_property('value')

  def _set_value(self, value):
    self.write_property('value', value)

  def _get_active_low(self):
    return self.read_property('active_low')

  def _set_active_low(self, active_low):
    self.write_property('active_low', '1' if active_low else '0')

  def set_function(self, function):
    if function == 'input':
      self._set_direction('in')
      self._out = False
    elif function == 'output':
      self._set_direction('out')
      self._out = True
    else:
      raise ValueError('pin function must be either input or output')

  def get_function(self):
    direction = self._get_direction()
    if direction == 'input':
      return 'in'
    if direction == 'output':
      return 'out'

  def set_value(self, value):
    if not self._out:
      raise PinSetInput('Pin is not open for output')
    self._set_value('1' if value else '0')
    self._value = value

  def get_value(self):
    if self._out:
      return self._value
    return bool(int(self._get_value()))

  def open(self):
    super(SysFsGpioPin, self).open()
    self.wait_for_permissions('active_low')
    self.wait_for_permissions('direction')
    # GPIO pins on the hat seem to be inverted by default.
    self._set_active_low(True)

  def close(self):
    # Restore the default direction (turns off LED) before closing.
    self._set_direction('in')
    super(SysFsGpioPin, self).close()


class SysFsPwmPin(SysFsPin):
  """SysFs support for PWM pins.

  Supports the SysFs node for pwm control.
  """
  _FS_ROOT = '/sys/class/pwm/pwmchip0'

  class PwmState(object):
    """Container for the state of the pwm.

    Used to recover after disable/enable and ensure consistency.
    """

    def __init__(self):
      self.duty_cycle = 0
      self.period_ns = _NS_PER_SECOND / 50
      self.enabled = False
      self.function = None

  def __init__(self, spec):
    super(SysFsPwmPin, self).__init__(spec, self._FS_ROOT)
    if not isinstance(spec, PwmSpec):
      raise TypeError('Pin specification not compatible with SysFS PWM')
    if spec.pin < 0 or spec.pin > 3:
      raise ValueError('Pin must be between 0 and 3 (inclusive)')
    self._spec = spec
    self._state = SysFsPwmPin.PwmState()

  def _set_enabled(self, enabled):
    self.write_property('enable', '1' if enabled else '0')
    self._state.enabled = enabled

  def _get_enabled(self):
    return int(self.read_property('enable')) != 0

  def _set_period_ns(self, period_ns):
    self.write_property('period', '%d' % period_ns)
    self._state.period_ns = int(period_ns)

  def _get_period_ns(self):
    return int(self.read_property('period'))

  def _set_duty_cycle(self, duty_cycle):
    self.write_property('duty_cycle', '%d' % duty_cycle)
    self._state.duty_cycle = duty_cycle

  def _get_duty_cycle(self):
    return int(self.read_property('duty_cycle'))

  def _update_state(self, new_state):
    # Each time we enable, we need to first re-set the period and duty cycle (in
    # that order).
    if new_state.period_ns != self._state.period_ns or (not self._state.enabled
                                                        and new_state.enabled):
      self._set_period_ns(new_state.period_ns)
    if new_state.duty_cycle != self._state.duty_cycle or (
        not self._state.enabled and new_state.enabled):
      self._set_duty_cycle(new_state.duty_cycle)
    if new_state.enabled != self._state.enabled:
      self._set_enabled(new_state.enabled)

  def _read_state(self):
    self._state.period_ns = self._get_period_ns()
    self._state.enabled = self._get_enabled()
    self._state.duty_cycle = self._get_duty_cycle()

  def set_function(self, function):
    if function != 'pwm' and function != 'output':
      raise ValueError('PWM pins only support pwm and output functionality')
    self._state.function = function

  def get_function(self):
    return self._state.function

  def get_value(self):
    return self._state.duty_cycle / self._state.period_ns

  def set_value(self, value):
    new_state = deepcopy(self._state)
    if value is None:
      new_state.enabled = False
    else:
      new_state.enabled = True
      new_state.duty_cycle = value * self._state.period_ns
    self._update_state(new_state)

  def set_period_ns(self, period_ns):
    new_state = deepcopy(self._state)
    new_state.period_ns = period_ns
    self._update_state(new_state)

  def get_period_ns(self):
    return self._state.period_ns

  def open(self):
    super(SysFsPwmPin, self).open()
    self.wait_for_permissions('period')
    self.wait_for_permissions('enable')
    self._read_state()
    new_state = deepcopy(self._state)
    new_state.period_ns = _NS_PER_SECOND / 50
    new_state.enabled = True
    self._update_state(new_state)

  def close(self):
    self._set_enabled(False)
    super(SysFsPwmPin, self).close()


# Debounce by making sure the last change wasn't less than d_time in the past ->
# should be agnostic to direction.
class DebouncingPoller(object):
  """Manages debouncing and polling a function periodically in the background.

  Calls a given getter periodically and when the debounced value changes such
  that detector(old, new) returns true, the callback is called. Only runs while
  detector, getter, and callback are set.
  """
  _MIN_POLL_INTERVAL = .0001

  def __init__(self, value_getter, callback, detector=lambda old, new: True):
    self._poll_thread = None
    self._debounce_time = .001
    self._poll_interval = .00051
    self._getter = value_getter
    self._detector = detector
    self._callback = callback

  @property
  def poll_interval(self):
    return self._poll_interval

  @poll_interval.setter
  def poll_interval(self, interval):
    self._poll_interval = max(interval, self._MIN_POLL_INTERVAL)
    self.restart_polling()

  @property
  def debounce_time(self):
    return self._debounce_time

  @debounce_time.setter
  def debounce_time(self, debounce_time):
    self._debounce_time = debounce_time
    self.restart_polling()

  @property
  def callback(self):
    return self._callback

  @callback.setter
  def callback(self, callback):
    self.stop_polling()
    self._callback = callback
    self.try_start_polling()

  @property
  def detector(self):
    return self._detector

  @detector.setter
  def detector(self, detector):
    self._detector = detector
    self.restart_polling()

  def try_start_polling(self):
    if (not self._poll_thread and self._getter and self._callback and
        self._detector):
      self._poll_thread = GPIOThread(
          target=self._poll,
          args=(self._poll_interval, self._debounce_time, self._getter,
                self._detector, self._callback))
      self._poll_thread.start()

  def stop_polling(self):
    if self._poll_thread:
      self._poll_thread.stop()
      self._poll_thread = None

  def restart_polling(self):
    self.stop_polling()
    self.try_start_polling()

  # Only called from the polling thread.
  def _poll(self, poll_interval, debounce_interval, getter, detector, callback):
    """Debounces and monitors the value retrieved by _getter.

    Triggers callback if detector(old_value, new_value) returns true.
    Args:
      poll_interval: positive float, time in seconds between polling the getter.
      debounce_interval: positive float, time in seconds to wait after a change
        to allow a future change to the value to trigger the callback.
      getter: function() -> value, gets the value. This will be called
        periodically and the value type will be the same type passed to the
        detector function.
      detector: function(old, new) -> bool, filters changes to determine when
        the callback should be called. Can be used for edge detection
      callback: function() to be invoked when detector conditions are met.
    """
    last_time = time.time()
    last_value = getter()
    while not self._poll_thread.stopping.wait(poll_interval):
      value = getter()
      new_time = time.time()
      if not debounce_interval or (new_time - last_time) > debounce_interval:
        if detector(last_value, value):
          callback()
        last_value = value
        last_time = new_time


class HatPin(Pin):
  """A Pin implemenation that supports pins controlled by the hat's MCU.

  Only one HatPin should exist at a given time for a given pin system wide.
  Behavior is completely unpredictable if more than one pin exists concurrently.
  If the factory is used for construction there are protections in place to
  prevent this, however if multiple programs are running simultaneously the
  protections do not limit cross program duplication.
  """
  _EDGE_DETECTORS = {
      'both': lambda old, new: old != new,
      'rising': lambda old, new: not old and new,
      'falling': lambda old, new: old and not new,
      None: None,
  }

  def __init__(self, spec, pwm=False):
    super(HatPin, self).__init__()
    self.gpio_pin = None
    self.pwm_pin = None
    self.pwm_active = False
    self.gpio_active = False
    if spec.gpio_spec is not None:
      self.gpio_pin = SysFsGpioPin(spec.gpio_spec)

    if spec.pwm_spec is not None:
      self.pwm_pin = SysFsPwmPin(spec.pwm_spec)

    self._closed = False
    self._poller = DebouncingPoller(self._get_state, None)
    self._edges = None
    self._set_bounce(.001)
    # Start out with gpio enabled for compatibility.
    self._enable_gpio()

  def _enable_pwm(self):
    if self._closed:
      return
    if self.pwm_pin is None:
      raise PinPWMUnsupported(
          'PWM was enabled, but is not supported on pin %r' % self.pwm_pin)
    self._disable_gpio()
    if not self.pwm_active:
      self.pwm_pin.open()
      self.pwm_active = True

  def _disable_pwm(self):
    if self.pwm_active and self.pwm_pin is not None:
      self.pwm_pin.close()
    self.pwm_active = False

  def _enable_gpio(self):
    if self._closed:
      return
    if self.gpio_pin is None:
      raise PinUnsupported(
          'GPIO was enabled, but is not supported on pin %r' % self.gpio_pin)
    self._disable_pwm()
    if not self.gpio_active:
      self.gpio_pin.open()
      self.gpio_active = True

  def _disable_gpio(self):
    if self.gpio_active and self.gpio_pin is not None:
      self.gpio_pin.close()
    self.gpio_active = False

  def close(self):
    self._closed = True
    self._poller.stop_polling()
    self._disable_pwm()
    self._disable_gpio()

  def _active_pin(self):
    if self.pwm_active:
      return self.pwm_pin
    if self.gpio_active:
      return self.gpio_pin
    return None

  def _get_function(self):
    return self._active_pin().get_function()

  def _set_function(self, value):
    if value == 'input':
      if self.pwm_active:
        raise InputDeviceError('PWM Pin cannot be set to input')
      self._enable_gpio()
    elif value == 'pwm':
      if self.gpio_active:
        raise PinPWMUnsupported('GPIO Pin cannot be set to pwm')
      self._enable_pwm()
    elif self._active_pin() is None:
      self._enable_gpio()

    if value != 'input':
      self._poller.stop_polling()
    self._active_pin().set_function(value)

  def _get_state(self):
    return self._active_pin().get_value()

  def _set_state(self, state):
    self._active_pin().set_value(state)

  def _get_frequency(self):
    if self.pwm_pin is None or not self.pwm_active:
      return None
    return _NS_PER_SECOND / self.pwm_pin.get_period_ns()

  def _set_frequency(self, frequency):
    if frequency is None:
      self._enable_gpio()
    else:
      self._enable_pwm()
      self.pwm_pin.set_period_ns(_NS_PER_SECOND / frequency)

  def _set_pull(self, pull):
    if pull != 'up':
      raise PinFixedPull('Only pull up is supported right now (%s)' % pull)

  def _get_pull(self):
    return 'up'

  def _set_edges(self, edges):
    if edges not in HatPin._EDGE_DETECTORS.keys():
      raise PinInvalidEdges('Edge must be "both", "falling", "rising", or None')
    self._poller.detector = HatPin._EDGE_DETECTORS[edges]
    self._edges = edges

  def _get_edges(self):
    return self._edges

  def _set_when_changed(self, callback):
    self._poller.callback = callback

  def _get_when_changed(self):
    return self._poller.callback

  def set_poll_interval(self, poll_interval):
    """Sets the time between polling the pin value.

    If a debounce time is set, this will be set to .51 * the debounce time.
    There is a natural minimum value of _MIN_POLL_INTERVAL to which all smaller
    values will be clipped.
    Args:
      poll_interval: positve float, time in seconds between polling the pin.
    """
    self._poller.poll_interval = poll_interval

  def _set_bounce(self, debounce_time):
    if debounce_time is None:
      self._poller.debounce_time = debounce_time
    elif debounce_time < 0:
      raise PinInvalidBounce('Bounce must be positive.')
    else:
      self._poller.debounce_time = debounce_time
      self.set_poll_interval(debounce_time * .51)

  def _get_bounce(self):
    return self._poller.debounce_time


class HybridFactory(Factory):
  """Factory for selecting between other factories based on priority/success."""

  def __init__(self, *factories):
    super(HybridFactory, self).__init__()
    self.factories = factories

  def close(self):
    for factory in self.factories:
      factory.close()

  def pin(self, spec):
    for factory in self.factories:
      try:
        # Try to make the pin from each factory (in order), until one works.
        return factory.pin(spec)
      except (TypeError, ValueError):
        pass
    raise TypeError(
        'No registered factory was able to construct a pin for the given '
        'specification')


class HatFactory(Factory):
  """Factory for pins accessed through the hat's MCU."""
  pins = {}

  def __init__(self):
    super(HatFactory, self).__init__()

    self.pins = HatFactory.pins

  def close(self):
    for pin in self.pins.values():
      pin.close()

  def pin(self, spec):
    if spec in self.pins:
      return self.pins.get(spec)
    if isinstance(spec, AIYPinSpec):
      pin = HatPin(spec)
      self.pins[spec] = pin
      return pin
    raise TypeError('Hat factory invoked on non-hat pin')


# This overrides the default factory being used by all gpiozero devices. It will
# defer to the previous default for all non-hat pins.
hat_factory = HatFactory()
Device.pin_factory = HybridFactory(hat_factory, Device.pin_factory)
