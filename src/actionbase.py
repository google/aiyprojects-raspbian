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

import user_scripts
import logging

"""Handle voice commands locally.

This code lets you link keywords to actions. The actions are declared in
action.py.
"""

logger = logging.getLogger(__name__)

class Actor(object):

    """Passes commands on to a list of action handlers."""

    def __init__(self, args):
        self.handlers = []
        self.userscripts = user_scripts.script_list(args.user_script_directory)

    def add_keyword(self, keyword, action):
        self.handlers.append(KeywordHandler(keyword, action))

    def add_userscripts(self, say):
        for script in self.userscripts.get_scripts():
            script.set_say(say)
            for keyword in script.get_keywords():
                logger.info("Adding keyword (%s) - %s" %(keyword, script.get_description()))
                self.add_keyword(_(keyword), script)

    def handle_state_trigger(self, trigger):
        scripts = self.userscripts.get_scripts()
        if scripts:
            logger.info("Running %s state trigger ..." %(trigger))
            for script in scripts:
                script.state_trigger(trigger)

    def get_phrases(self):
        """Get a list of all phrases that are expected by the handlers."""
        return [phrase for h in self.handlers for phrase in h.get_phrases()]

    def can_handle(self, command):
        """Check if command is handled without running the handlers.

        Returns True if the command would be handled."""

        for handler in self.handlers:
            if handler.can_handle(command):
                return True
        return False

    def handle(self, command):
        """Pass command to handlers, stopping after one has handled the command.

        Returns True if the command was handled."""

        for handler in self.handlers:
            if handler.handle(command):
                return True
        return False


class KeywordHandler(object):

    """Perform the action when the given keyword is in the command."""

    def __init__(self, keyword, action):
        self.keyword = keyword.lower()
        self.action = action

    def get_phrases(self):
        return [self.keyword]

    def can_handle(self, command):
        return self.keyword in command.lower()

    def handle(self, command):
        if self.can_handle(command):
            self.action.run(command)
            return True
        return False
