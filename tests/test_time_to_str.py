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

'''Test the time-to-string conversion.'''

import datetime
import unittest

import action


class TestTimeToStr(unittest.TestCase):

    def assertTimeToStr(self, time, expected):
        self.assertEqual(action.SpeakTime(None).to_str(time), expected)

    def test_midnight(self):
        self.assertTimeToStr(datetime.time(0, 0), 'It is midnight.')

    def test_just_after_midnight(self):
        self.assertTimeToStr(datetime.time(0, 2), 'It is midnight.')

    def test_five_past_midnight(self):
        self.assertTimeToStr(datetime.time(0, 5), 'It is five past midnight.')

    def test_five_to_midnight(self):
        self.assertTimeToStr(datetime.time(23, 55), 'It is five to midnight.')

    def test_quarter_to_one(self):
        self.assertTimeToStr(datetime.time(0, 45), 'It is quarter to one.')

    def test_twenty_past_four(self):
        self.assertTimeToStr(datetime.time(4, 20), 'It is twenty past four.')

    def test_before_midday(self):
        self.assertTimeToStr(datetime.time(11, 50), 'It is ten to twelve.')

    def test_midday(self):
        self.assertTimeToStr(datetime.time(11, 59), "It is twelve o'clock.")

    def test_after_midday(self):
        self.assertTimeToStr(datetime.time(12, 32), 'It is half past twelve.')

    def test_twenty_past_four_pm(self):
        self.assertTimeToStr(datetime.time(16, 20), 'It is twenty past four.')

if __name__ == '__main__':
    unittest.main()
