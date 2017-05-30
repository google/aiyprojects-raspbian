#! /usr/bin/env python3

"""Integrate user scripts into the Google Voice AIY project.
For examples see https://github.com/pjbroad/aiy-user-scripts.
"""

# Copyright 2017 Paul Broadhead.
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

import os
import sys
import subprocess
import json
import logging


logger = logging.getLogger(__name__)


class user_script(object):

	"""Manage a single user script.

	If called without parameters, the script is expected to return via
	standard output, a JSON formatted dictionary object that describes
	the script.  Keys are:
		"description" - optional text string giving the script function
		"keywords" - a list of words that trigger the script
		"before-listen" - optional, before recognition command
		"after-listen" - optional, after recognition command
	When one of the keywords triggers, the script is called with the
	full voice command, each word as a separate parameter.  Any text
	written by the script to standard output will be spoken back using
	text-to-voice.
	"""

	def __init__(self, file_path):
		"""Create a new user script object.
		Call the user script without parameters to get it configuration.
		"""
		self.file_path = file_path
		self.info = {}
		self.say = None
		self.ready = False
		(exit_code, raw_info) = self.run_script()
		if exit_code == 0:
			try:
				self.info = json.loads(raw_info.decode("utf-8"))
			except BaseException as e:
				logger.exception("Error parsing info for command [%s]: [%s]" %(self.file_path, str(e)))
			else:
				if len(self.get_keywords()):
					self.ready = True
				else:
					logger.error("Need at least one keyword for %s" %(file_path))
		else:
			logger.error("Error code for %s :%d" %(file_path, exit_code))

	def is_ready(self):
		"Return true if the user script was set up successfully."
		return self.ready

	def get_keywords(self):
		"Return a list containing the keywords the script can action."
		return self.info.get("keywords", [])

	def get_description(self):
		"Return the script description."
		return self.info.get("description", "<no description>")

	def special_command(self, command):
		"If 'command' is registered as a handler, call the user script."
		if command in self.info:
			self.run_script("%s %s" %(command, self.info[command]))

	def run_script(self, arg_string=''):
		"Run the user script with the specified arguments."
		args = arg_string.split()
		args.insert(0, self.file_path)
		try:
			p = subprocess.Popen(args, stdout=subprocess.PIPE)
			(output, err) = p.communicate()
			exit_code = p.wait()
		except BaseException as e:
			return (1, "Error: %s" %(str(e)))
		return (exit_code, output)

	def set_say(self, say):
		"Remember the text to speech object for the AIY actor."
		self.say = say

	def run(self, voice_command):
		"""The AIY voice actor callback.
		The script is run and passed each word from the voice command as
		a parameter.  The output from the script is spoken back.
		"""
		(exit_code, output) = self.run_script(voice_command)
		if self.say:
			if exit_code == 0:
				self.say(output.decode('utf-8'))
			else:
				self.say('Oh dear, user script failed with error code %d', exit_code)
		else:
			logger.error("Need to call set_say() function.")



class script_list(object):

	"""Manages a list of user scripts for the Google AIY voice project.

	The specified directory is scanned for scripts, expected
	to provide actions for voice commands. Each script can offer to
	handle multiple keywords.  Each script can provide a handler called
	before and after recognition.
	"""

	def __init__(self, script_directory):
		"""Create a new user scripts object.
		Scan the specified directory for scripts with a name containing
		the text 'user_script'.  Each successfully created script
		object is appended to the list.
		"""
		self.scripts = []
		if os.path.isdir(script_directory):
			if os.access(script_directory, os.R_OK):
				logger.info("Scanning %s for user scripts" %(script_directory))
				for f in os.listdir(script_directory):
					if 'user_script' in f:
						file_path = os.path.join(script_directory, f)
						if os.access(file_path, os.X_OK):
							script = user_script(file_path)
							if script.is_ready():
								self.scripts.append(script)
			else:
				logger.error("directory [%s] is not readable" %(script_directory))
		else:
			logger.error("directory [%s] does not exist" %(script_directory))

	def special_command(self, command):
		"Try the specified special action for each script."
		logger.info("Calling %s action ..." %(command))
		for script in self.scripts:
			script.special_command(command)

	def get_scripts(self):
		"Return the list of user script objects."
		return self.scripts

if __name__ == "__main__":
	# Test the module
	if len(sys.argv) < 2:
		print("Test using: %s <user script directory>" %(os.path.basename(sys.argv[0])))
		sys.exit(0)
	logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
	userscripts = script_list(sys.argv[1])
	userscripts.special_command('before-listen')
	userscripts.special_command('after-listen')
