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
"""Image classification library demo."""

import argparse
import io
import sys
from PIL import Image

from aiy.vision.inference import ImageInference
from aiy.vision.models import image_classification

def read_stdin():
    return io.BytesIO(sys.stdin.buffer.read())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', dest='input', required=True)
    parser.add_argument('--use_squeezenet', action='store_true', default=False,
                        help='Uses SqueezeNet based model.')
    args = parser.parse_args()

    # There are two models available for image classification task:
    # 1) MobileNet based (image_classification.MOBILENET), which has 59.9% top-1
    # accuracy on ImageNet;
    # 2) SqueezeNet based (image_classification.SQUEEZENET), which has 45.3% top-1
    # accuracy on ImageNet;
    model_type = (image_classification.SQUEEZENET if args.use_squeezenet
                  else image_classification.MOBILENET)
    with ImageInference(image_classification.model(model_type)) as inference:
        image = Image.open(read_stdin() if args.input == '-' else args.input)
        classes = image_classification.get_classes(inference.run(image),
            max_num_objects=5, object_prob_threshold=0.1)
        for i, (label, score) in enumerate(classes):
            print('Result %d: %s (prob=%f)' % (i, label, score))


if __name__ == '__main__':
    main()
