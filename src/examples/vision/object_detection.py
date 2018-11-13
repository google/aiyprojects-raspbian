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
"""Object detection library demo.

 - Takes an input image and tries to detect person, dog, or cat.
 - Draws bounding boxes around detected objects.
 - Saves an image with bounding boxes around detected objects.
"""
import argparse

from PIL import Image, ImageDraw

from aiy.vision.inference import ImageInference
from aiy.vision.models import object_detection


def crop_center(image):
    width, height = image.size
    size = min(width, height)
    x, y = (width - size) / 2, (height - size) / 2
    return image.crop((x, y, x + size, y + size)), (x, y)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--input', '-i', dest='input', required=True,
                        help='Input image file.')
    parser.add_argument('--output', '-o', dest='output',
                        help='Output image file with bounding boxes.')
    parser.add_argument('--sparse', '-s', action='store_true', default=False,
                        help='Use sparse tensors.')
    parser.add_argument('--threshold', '-t', type=float, default=0.3,
                        help='Detection probability threshold.')
    args = parser.parse_args()

    with ImageInference(object_detection.model()) as inference:
        image = Image.open(args.input)
        image_center, offset = crop_center(image)

        if args.sparse:
            result = inference.run(image_center,
                                   sparse_configs=object_detection.sparse_configs(args.threshold))
            objects = object_detection.get_objects_sparse(result, offset)
        else:
            result = inference.run(image_center)
            objects = object_detection.get_objects(result, args.threshold, offset)

        for i, obj in enumerate(objects):
            print('Object #%d: %s' % (i, obj))

        if args.output:
            draw = ImageDraw.Draw(image)
            for i, obj in enumerate(objects):
                x, y, width, height = obj.bounding_box
                draw.rectangle((x, y, x + width, y + height), outline='red')
            image.save(args.output)


if __name__ == '__main__':
    main()
