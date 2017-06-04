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
import tempfile
import os
import stat

import actionbase


class TestSayHelper(object):

    def __init__(self):
        self.last_say = ""

    def say(self, what_to_say):
        self.last_say = what_to_say.strip()

    def last_said(self):
        return self.last_say


class TestUserScriptHelper(object):

    def __init__(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_script = os.path.join(self.test_dir, "test_user_script.py")
        f = open(self.test_script, "w")
        f.write("""#! /usr/bin/env python3
import sys
import os
import json
if __name__ == "__main__":
    if len(sys.argv) < 2:
        info = {
            "description": "Unit Test.",
            "keywords": [ "unit-test-keyword" ],
            "before-listen": "before-listen-trigger",
        }
        print(json.dumps(info, separators=(',',':'), indent=4))
    elif len(sys.argv) > 2 and sys.argv[2] == "before-listen-trigger":
        open(os.path.join(os.path.dirname(sys.argv[0]), "trigger-test"), "w")
    else:
        print("%s" % (' '.join(sys.argv[1:])))
    """)
        f.close()
        st = os.stat(self.test_script)
        os.chmod(self.test_script, st.st_mode | stat.S_IEXEC)
        self.trigger_file = os.path.join(self.get_dir_name(), "trigger-test")

    def trigger_file_exists(self):
        return os.path.isfile(self.trigger_file)

    def get_dir_name(self):
        return self.test_dir

    def clean_up(self):
        if self.trigger_file_exists():
            os.remove(self.trigger_file)
        os.remove(self.test_script)
        os.rmdir(self.test_dir)


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

    def test_invalid_user_script_directory(self):
        actor = actionbase.Actor()
        actor.add_user_scripts(None, None)
        actor.handle_state_trigger('test')
        self.assertEqual(actor.user_scripts.get_scripts(), [])

    def test_valid_user_script_directory(self):
        user_script_helper = TestUserScriptHelper()
        say_helper = TestSayHelper()
        actor = actionbase.Actor()
        actor.add_user_scripts(user_script_helper.get_dir_name(), say_helper.say)
        scripts = actor.user_scripts.get_scripts()
        actor.handle_state_trigger("before-listen")
        scripts[0].run("unit test")
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0].get_description(), "Unit Test.")
        self.assertTrue(actor.can_handle('unit-test-keyword'))
        self.assertTrue(user_script_helper.trigger_file_exists())
        self.assertEqual(say_helper.last_said(), "unit test")
        user_script_helper.clean_up()

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
