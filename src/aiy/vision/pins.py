#!/usr/bin/env python3
# Copyright 2018 Google LLC
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

"""Legacy vision kit pin wrapper

The gpiozero pin control is shared between the various AIY kits but legacy
code explicitly imports aiy.vision.pins. This will import the correct top-level
pin driver (aiy.pins) and gently remind the user to update.
"""

from aiy.pins import *

print("""Your code is using an outdated import (aiy.vision.pins). Please switch
         to aiy.pins or pull the latest images for updated demos.""")
