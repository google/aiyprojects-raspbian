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

"""Trigger based on the existence of a specific file."""

from time import sleep  # Sleep to prevent the file checker from using 100% CPU
import os               # To monitor for files this will be required
import stat             # For setting permissions on the trigger file directory
import threading        # Separate file monitor thread from the voice recognizer

from triggers.trigger import Trigger  # Google AIY Trigger class

# The following allows us to print debugging information to the terminal
import logging
logger = logging.getLogger('trigger')


# Create a new class for the FileTrigger
class FileTrigger(Trigger):

    """Trigger based on the existence of a specific file."""

    POLLING_TIME = 0.5  # The file monitor will wait 0.5s between file checks
    # This file will trigger voice recognition
    TRIGGER_FILE = r"/tmp/voice_recognizer/trigger"
    # TODO: specify a group to have access to the trigger file directory

    def __init__(self):
        super().__init__()  # I'm not clear on what this does

    def start(self):
        # Delete trigger file if it exists at startup
        if os.path.isfile(self.TRIGGER_FILE):
            logger.info('cleaning up pre-existing trigger file')
            os.remove(self.TRIGGER_FILE)
        # Create the trigger directory if needed
        # Determine trigger directory
        trigger_dir = os.path.dirname(os.path.abspath(self.TRIGGER_FILE))
        if not os.path.exists(trigger_dir):
            os.makedirs(trigger_dir)  # Create directory and parents if required
            # Store existing permissions of the trigger directory
            permissions = stat.S_IMODE(os.lstat(trigger_dir)[stat.ST_MODE])
            # Make the trigger directory world writeable
            os.chmod(trigger_dir, permissions | stat.S_IWOTH)
        # Start the file monitor loop as a separate thread
        threading.Thread(target=self.file_monitor_loop).start()

    def file_monitor_loop(self):
        # Loop until the file exists
        while not os.path.isfile(self.TRIGGER_FILE):
            sleep(self.POLLING_TIME)  # Wait POLLING_TIME in seconds
        os.remove(self.TRIGGER_FILE)  # Delete trigger file
        self.callback()  # Trigger voice recognition
