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

'''Test the command ouput action.'''

import datetime
import unittest

import action


class TestSpeakShellCommandOutput(unittest.TestCase):

    def _say(self, text):
        self._say_text = text

    def setUp(self):
        self._say_text = None

    def test_say_receives_output(self):
        action.SpeakShellCommandOutput(self._say, 'echo test', None).run(None)
        self.assertEqual(self._say_text, 'test')

    def test_say_receives_failure_text(self):
        action.SpeakShellCommandOutput(self._say, 'echo', 'failure').run(None)
        self.assertEqual(self._say_text, 'failure')


if __name__ == '__main__':
    unittest.main()
