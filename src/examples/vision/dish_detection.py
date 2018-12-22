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
"""Dish detector library demo.

 - Takes an input image and tries to detect dish types.
 - Draws bounding boxes around detected dishes.
 - Saves an image with bounding boxes around detected dishes.
"""
import argparse

from PIL import Image, ImageDraw

from aiy.vision.inference import ImageInference
from aiy.vision.models import dish_detection

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', dest='input', required=True)
    parser.add_argument('--output', '-o', dest='output')
    args = parser.parse_args()

    with ImageInference(dish_detection.model()) as inference:
        image = Image.open(args.input)
        draw = ImageDraw.Draw(image)
        dishes = dish_detection.get_dishes(inference.run(image))
        for i, dish in enumerate(dishes):
            print('Dish #%d: %s' % (i, dish))
            x, y, width, height = dish.bounding_box
            draw.rectangle((x, y, x + width, y + height), outline='red')
        if args.output:
            image.save(args.output)


if __name__ == '__main__':
    main()
