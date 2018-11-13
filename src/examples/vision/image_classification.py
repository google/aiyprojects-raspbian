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

from PIL import Image

from aiy.vision.inference import ImageInference
from aiy.vision.models import image_classification


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--input', '-i', required=True,
                        help='Input image file.')
    parser.add_argument('--threshold', '-t', type=float, default=0.1,
                        help='Classification probability threshold.')
    parser.add_argument('--top_k', '-n', type=int, default=5,
                        help='Max number of returned classes.')
    parser.add_argument('--sparse', '-s', action='store_true', default=False,
                        help='Use sparse tensors.')
    parser.add_argument('--model', '-m', choices=('squeezenet', 'mobilenet'), default='mobilenet',
                        help='Model to run.')
    args = parser.parse_args()

    # There are two models available for image classification task:
    # 1) MobileNet based (image_classification.MOBILENET), which has 59.9% top-1
    # accuracy on ImageNet;
    # 2) SqueezeNet based (image_classification.SQUEEZENET), which has 45.3% top-1
    # accuracy on ImageNet;
    model_type = {'squeezenet': image_classification.SQUEEZENET,
                  'mobilenet': image_classification.MOBILENET}[args.model]

    with ImageInference(image_classification.model(model_type)) as inference:
        image = Image.open(args.input)

        if args.sparse:
            configs = image_classification.sparse_configs(top_k=args.top_k,
                                                          threshold=args.threshold,
                                                          model_type=model_type)
            result = inference.run(image, sparse_configs=configs)
            classes = image_classification.get_classes_sparse(result)
        else:
            result = inference.run(image)
            classes = image_classification.get_classes(result,
                                                       top_k=args.top_k,
                                                       threshold=args.threshold)

        for i, (label, score) in enumerate(classes):
            print('Result %d: %s (prob=%f)' % (i, label, score))


if __name__ == '__main__':
    main()
