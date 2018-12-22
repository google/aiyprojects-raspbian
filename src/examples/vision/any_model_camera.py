#!/usr/bin/env python3
#
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
"""Script to load and run model on Vision Bonnet.

The primary purpose of this script is to make sure a compiled model can run on
Vision Bonnet. It does not try to interpret the output tensor.

Example:
~/AIY-projects-python/src/examples/vision/any_model_camera.py \
  --model_path ~/models/mobilenet_ssd_256res_0.125_person_cat_dog.binaryproto \
  --input_height 256 \
  --input_width 256
"""
import argparse

from picamera import PiCamera

from aiy.vision.inference import CameraInference, ModelDescriptor
from aiy.vision.models import utils

def tensors_info(tensors):
    return ', '.join('%s [%d elements]' % (name, len(tensor.data))
        for name, tensor in tensors.items())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_name', default='test_model', help='Model identifier.')
    parser.add_argument('--model_path', required=True, help='Path to model file.')
    parser.add_argument('--input_height', type=int, required=True, help='Input height.')
    parser.add_argument('--input_width', type=int, required=True, help='Input width.')
    parser.add_argument('--input_depth', type=int, default=3, help='Input depth.')
    parser.add_argument('--input_mean', type=float, default=128.0, help='Input mean.')
    parser.add_argument('--input_std', type=float, default=128.0, help='Input std.')
    args = parser.parse_args()

    model = ModelDescriptor(
        name=args.model_name,
        input_shape=(1, args.input_height, args.input_width, args.input_depth),
        input_normalizer=(args.input_mean, args.input_std),
        compute_graph=utils.load_compute_graph(args.model_path))

    with PiCamera(sensor_mode=4, framerate=30):
        with CameraInference(model) as inference:
            for result in inference.run():
                print('#%05d (%5.2f fps): %s' %
                    (inference.count, inference.rate, tensors_info(result.tensors)))


if __name__ == '__main__':
    main()
