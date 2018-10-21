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
import os
from contextlib import contextmanager

from PIL import Image


def test_image_path(name):
    p = os.path.join(os.path.dirname(__file__), 'images', name)
    return os.path.abspath(p)

@contextmanager
def TestImage(name):
    with open(test_image_path(name), 'rb') as f:
        image = Image.open(f)
        try:
            yield image
        finally:
            image.close()
