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

'''Test the action base classes.'''

import unittest

import actionbase


class TestAction(object):

    def __init__(self):
        self.voice_command = None

    def run(self, voice_command):
        self.voice_command = voice_command


class TestKeywordHandler(unittest.TestCase):

    def test_keyword_phrases(self):
        phrases = actionbase.KeywordHandler('FooBar', None).get_phrases()
        self.assertEqual(phrases, ['foobar'])

    def test_handle_keyword_with_mixed_case(self):
        action = TestAction()
        actionbase.KeywordHandler('FooBar', action).handle('foobar')
        self.assertEqual(action.voice_command, 'foobar')

    def test_handle_keyword_in_command(self):
        action = TestAction()
        actionbase.KeywordHandler('FooBar', action).handle('frobnicate the foobar')
        self.assertEqual(action.voice_command, 'frobnicate the foobar')

    def test_can_handle_returns_true(self):
        action = TestAction()
        handler = actionbase.KeywordHandler('FooBar', action)
        self.assertTrue(handler.can_handle('frobnicate the foobar'))

    def test_can_handle_does_nothing(self):
        action = TestAction()
        actionbase.KeywordHandler('FooBar', action).can_handle('frobnicate the foobar')
        self.assertIsNone(action.voice_command)


class TestActor(unittest.TestCase):

    def test_empty_actor_has_no_phrases(self):
        phrases = actionbase.Actor().get_phrases()
        self.assertEqual(phrases, [])

    def test_empty_actor_does_not_handle_commands(self):
        self.assertFalse(actionbase.Actor().handle('foobar'))

    def test_actor_runs_action(self):
        actor = actionbase.Actor()
        actor.add_keyword('foo', TestAction())
        self.assertTrue(actor.handle('moo foo'))

    def test_actor_runs_matching_action(self):
        actor = actionbase.Actor()
        foo_action = TestAction()
        actor.add_keyword('foo', foo_action)
        bar_action = TestAction()
        actor.add_keyword('bar', bar_action)
        self.assertTrue(actor.handle('moo bar'))
        self.assertIsNone(foo_action.voice_command)
        self.assertIsNotNone(bar_action.voice_command)

    def test_can_handle_returns_true(self):
        actor = actionbase.Actor()
        foo_action = TestAction()
        actor.add_keyword('foo', foo_action)
        self.assertTrue(actor.can_handle('moo foo'))

    def test_can_handle_does_nothing(self):
        actor = actionbase.Actor()
        foo_action = TestAction()
        actor.add_keyword('foo', foo_action)
        self.assertIsNone(foo_action.voice_command)


if __name__ == '__main__':
    unittest.main()
