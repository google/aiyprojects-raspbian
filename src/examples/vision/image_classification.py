#!/usr/bin/env python
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

"""Image classification library demo."""

import argparse
from PIL import Image

from aiy.vision.inference import ImageInference
from aiy.vision.models import image_classification


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--input', '-i', dest='input', required=True)
  args = parser.parse_args()

  with ImageInference(image_classification.model()) as inference:
    image = Image.open(args.input)
    classes = image_classification.get_classes(inference.run(image))
    for i, (label, score) in enumerate(classes):
      print('Result %d: %s (prob=%f)' % (i, label, score))

if __name__ == '__main__':
  main()
