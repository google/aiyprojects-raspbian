#!/usr/bin/env python3
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
"""Dish classification library demo."""

import argparse
from PIL import Image

from aiy.vision.inference import ImageInference
from aiy.vision.models import dish_classification

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', dest='input', required=True)
    args = parser.parse_args()

    with ImageInference(dish_classification.model()) as inference:
        image = Image.open(args.input)
        classes = dish_classification.get_classes(
            inference.run(image), top_k=5, threshold=0.1)
        for i, (label, score) in enumerate(classes):
            print('Result %d: %s (prob=%f)' % (i, label, score))


if __name__ == '__main__':
    main()
