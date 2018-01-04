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

"""Utilities to identify the currently installed AIY device (if any)."""

import re
import os

HAT_PATH = '/proc/device-tree/hat/'
HAT_PRODUCT_ID_RE = re.compile('0x[0-9A-Fa-f]+')
AIY_HATS = {
    1: 'Voice Hat',
    2: 'Vision Bonnet',
    3: 'Voice Bonnet',
}

def _is_hat_attached():
  return os.path.exists(HAT_PATH)

def _get_hat_product():
  with open(os.path.join(HAT_PATH, 'product')) as f:
    return f.readline().strip()

def _get_hat_product_id():
  with open(os.path.join(HAT_PATH, 'product_id')) as f:
    matches = HAT_PRODUCT_ID_RE.match(f.readline().strip())
    if matches:
      return int(matches.group(0), 16)

def get_aiy_device_name():
  if not _is_hat_attached():
    return None
  product = _get_hat_product()
  if not 'AIY' in product:
    return None
  product_id = _get_hat_product_id()
  if not product_id:
    return None
  if not product_id in AIY_HATS:
    return None
  return AIY_HATS[product_id]
