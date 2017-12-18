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

"""Face detection library demo.

 - Takes an input image and tries to detect faces.
 - Draws bounding boxes around detected objects.
 - Saves an image with bounding boxes around detected objects.
"""
import argparse
from PIL import Image
from PIL import ImageDraw

from aiy.vision.inference import ImageInference
from aiy.vision.models import face_detection


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--input', '-i', dest='input', required=True)
  parser.add_argument('--output', '-o', dest='output')
  args = parser.parse_args()

  with ImageInference(face_detection.model()) as inference:
    image = Image.open(args.input)
    draw = ImageDraw.Draw(image)
    for i, face in enumerate(face_detection.get_faces(inference.run(image))):
      print('Face #%d: %s' % (i, str(face)))
      x, y, width, height = face.bounding_box
      draw.rectangle((x, y, x + width, y + height), outline='red')
    if args.output:
      image.save(args.output)


if __name__ == '__main__':
  main()
