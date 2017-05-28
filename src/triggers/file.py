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
  
"""Trigger based on the existence of a specific file."""

  
from time import sleep # This is used to prevent the file checker thread from running at 100% CPU
import os              # To monitor for files this will be required
import stat            # For setting permissions on the trigger file directory
import threading       # This keeps the file monitor as a separate thread from the voice recognizer

from triggers.trigger import Trigger # Google AIY Trigger class

# The following allows us to print debugging information to the terminal  
import logging  
logger = logging.getLogger('trigger')  
  
# Create a new class for the FileTrigger  
class FileTrigger(Trigger):  
  
    """Trigger based on the existence of a specific file."""  
  
    POLLING_TIME = 0.5 # The file monitor will wait 0.5s between file checks 
    TRIGGER_FILE = r"/tmp/voice_recognizer/trigger" # This file will trigger voice recognition
    # TODO: specify a group to have access to the trigger file directory 
  
    def __init__(self): 
        super().__init__() # I'm not clear on what this does 
  
    def start(self): 
        # Delete trigger file if it exists at startup 
        if os.path.isfile(self.TRIGGER_FILE): 
            logger.info('cleaning up pre-existing trigger file') 
            os.remove(self.TRIGGER_FILE) 
        # Create the trigger directory if needed 
        trigger_dir = os.path.dirname(os.path.abspath(self.TRIGGER_FILE)) # Determine trigger direcotry
        if not os.path.exists(trigger_dir): 
            os.makedirs(trigger_dir) # Create directory and any parents required 
            permissions = stat.S_IMODE(os.lstat(trigger_dir)[stat.ST_MODE]) # Store existing permissions on the trigger directory 
            os.chmod(trigger_dir, permissions | stat.S_IWOTH) # Ensure the new directory is writeable by all
  
        threading.Thread(target=self.file_monitor_loop).start() # Start the file monitor infinite loop as a separate thread
  
    def file_monitor_loop(self): 
        # Endless loop 
        while True: 
            # If the trigger file exists 
            if os.path.isfile(self.TRIGGER_FILE): 
                os.remove(self.TRIGGER_FILE) # Delete existing file 
                self.callback() # Trigger voice recognition 
            else: 
                sleep(self.POLLING_TIME) # Wait as long as specified by POLLING_TIME in seconds before checking again
