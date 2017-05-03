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

"""Detect claps in the audio stream."""

import logging
import numpy as np

from triggers.trigger import Trigger

logger = logging.getLogger('trigger')


class ClapTrigger(Trigger):

    """Detect claps in the audio stream."""

    def __init__(self, recorder):
        super().__init__()

        self.have_clap = True  # don't start yet
        self.prev_sample = 0
        recorder.add_processor(self)

    def start(self):
        self.prev_sample = 0
        self.have_clap = False

    def add_data(self, data):
        """ audio is mono 16bit signed at 16kHz """
        audio = np.fromstring(data, 'int16')
        if not self.have_clap:
            # alternative: np.abs(audio).sum() > thresh
            shifted = np.roll(audio, 1)
            shifted[0] = self.prev_sample
            val = np.max(np.abs(shifted - audio))
            if val > (65536 // 4):  # quarter max delta
                logger.info("clap detected")
                self.have_clap = True
                self.callback()
        self.prev_sample = audio[-1]
