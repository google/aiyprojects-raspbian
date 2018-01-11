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

"""
Simple piezo buzzer controller for the pwm-soft driver.

This is designed to both expose the raw controller so that the user can adjust
frequency, period, and pulse width, and also provide a simple means for playing
melodic sounds.
"""
import os
import time

USEC = 1000000


def HzToPeriodUsec(freq_hz):
    """Converts a frequency given in Hz to a period expressed in microseconds."""
    return USEC / freq_hz


class PWMController(object):
    """Controller that simplifies the interface to pwm-soft Linux driver.

    Simple usage:
        from aiy._drivers._buzzer import PWMController
        with PWMController(gpio=22) as controller:
            controller.set_frequency(440.00)
            time.sleep(1)
            controller.set_frequency(0)

    Note: The pwm-soft driver is a little cantankerous and weird in terms of the
    model that it uses for controlling the PWM output. Instead of specifying a
    period and a duty cycle percentage, this driver explicitly allows the user
    to specify how long in microseconds to keep the GPIO high, and how long the
    entire period is.

    This can make things a little strange when it comes to changing the
    apparent frequency of the PWM output, as simply adjusting the period time
    while leaving the pulse time constant will produce phasing effects rather
    than frequency shifts.

    For more melodious uses, set_frequency should be enough.
    """

    PWM_SOFT_BASE_PATH = '/sys/class/pwm-soft'
    PWM_SOFT_EXPORT_PATH = PWM_SOFT_BASE_PATH + '/export'
    PWM_SOFT_UNEXPORT_PATH = PWM_SOFT_BASE_PATH + '/unexport'

    def __init__(self, gpio):
        """Initializes and configures the pwm-soft driver for the given GPIO.

        Args:
            gpio: the number of the GPIO to use for PWM output.
        """
        self.gpio = gpio
        self._pulse_fh = None
        self._period_fh = None
        self._exported = False

    def __enter__(self):
        """Context manager method to automatically open up."""
        self._export_pwm()
        return self

    def __exit__(self, *args):
        """Context manager method to clean up."""
        self._unexport_pwm()

    def _make_pwm_path(self, pwm_number):
        """Makes a path into the an exported PWM pin.

        Args:
            pwm_number: the number of the PWM previously exported.
        """
        return '%s/pwm%d' % (self.PWM_SOFT_BASE_PATH, pwm_number)

    def _wait_for_access(self, path):
        retry_count = 5
        retry_time = 0.01
        while not os.access(path, os.W_OK) and retry_count != 0:
            retry_count -= 1
            time.sleep(retry_time)
            retry_time *= 2

        if not os.access(path, os.W_OK):
            raise IOError('Could not open %s' % path)

    def _pwrite_int(self, path, data):
        """Helper method to quickly write a value to a sysfs node.

        Args:
            path: string of the path to the sysfs node to write the data to.
            data: an integer to write to the sysfs node.
        """
        self._wait_for_access(path)
        with open(path, 'w') as output:
            self._write_int(output, data)

    def _write_int(self, fh, data):
        """Helper method to write a value to a pre-opened handle.

        Note: this flushes the output to disk to ensure that it actually makes
        it to the sysfs node.

        Args:
            fh: the file handle to write to (as returned by open).
            data: the integer to write to the file.
        """
        fh.write('%d\n' % data)
        fh.flush()

    def _export_pwm(self):
        """Exports the given GPIO via the pwm-soft driver.

        This writes the given GPIO number to the export sysfs node and opens two
        file handles for later use to the period and pulse sysfs nodes inside
        the given PWM path. If it fails, this will raise an exception.
        """
        try:
            self._pwrite_int(self.PWM_SOFT_EXPORT_PATH, self.gpio)
        except BaseException:
            self._exported = False
            raise

        self._exported = True

        period_path = self._make_pwm_path(self.gpio) + '/period'
        try:
            self._wait_for_access(period_path)
            self._period_fh = open(period_path, 'w')
        except BaseException:
            self._unexport_pwm()
            raise

        pulse_path = self._make_pwm_path(self.gpio) + '/pulse'
        try:
            self._wait_for_access(pulse_path)
            self._pulse_fh = open(pulse_path, 'w')
        except BaseException:
            self._unexport_pwm()
            raise

    def _unexport_pwm(self):
        """Unexports the given GPIO from the pwm-soft driver.

        This effectively reverses _export_pwm by closing the two file handles it
        previously opened, and then unexporting the given gpio.
        """
        if self._exported:
            if self._period_fh is not None:
                self._period_fh.close()

            if self._pulse_fh is not None:
                self._pulse_fh.close()

            self._pwrite_int(self.PWM_SOFT_UNEXPORT_PATH, self.gpio)
            self._exported = False

    def open(self):
        """Opens the PWNController, exports the GPIO and gets ready to play."""
        self._export_pwm()

    def _update_pwm(self):
        """Helper method to update the pulse and period settings in the driver."""
        self._write_int(self._pulse_fh, self._pulse_usec)
        self._write_int(self._period_fh, self._period_usec)
        self._write_int(self._pulse_fh, self._pulse_usec)
        self._write_int(self._period_fh, self._period_usec)
        self._write_int(self._pulse_fh, self._pulse_usec)
        self._write_int(self._period_fh, self._period_usec)

    def open(self):
        """Opens the PWNController, exports the GPIO and gets ready to play."""
        self._export_pwm()

    def close(self):
        """Shuts down the PWMController and unexports the GPIO."""
        self._unexport_pwm()

    def set_frequency(self, freq_hz):
        """Sets the frequency in Hz to output.

        Note: This assumes a 50% duty cycle for the PWM output to provide a nice
        clear tone on any attached piezo buzzer. For more advanced techniques
        and effects, please see set_period_usec and set_pulse_usec.

        Args:
            freq_hz: The frequency in Hz to output.
        """
        if freq_hz == 0:
            self._frequency_hz = 0
            self._period_usec = 0
            self._pulse_usec = 0
        else:
            self._frequency_hz = freq_hz
            self._period_usec = int(HzToPeriodUsec(freq_hz))
            self._pulse_usec = int(self._period_usec / 2)

        self._update_pwm()

    def set_pulse_usec(self, pulse_usec):
        """Sets the pulse length in microseconds.

        Args:
            pulse_usec: how long to keep the GPIO high during the PWM period.
        """
        self._pulse_usec = pulse_usec
        self._update_pwm()

    def set_period_usec(self, period_usec):
        """Sets the period length in microseconds.

        Args:
            period_usec: how long each PWM cycle will take in microseconds.
        """
        self._period_usec = period_usec
        self._update_pwm()

    def pulse_usec(self):
        """Getter for getting the current pulse width in microseconds."""
        return self._pulse_usec

    def period_usec(self):
        """Getter for getting the current period width in microseconds."""
        return self._period_usec

    def frequency_hz(self):
        """Getter for getting the current frequency in Hertz."""
        return self._frequency_hz
