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
"""API for Image Classification tasks."""

from aiy.vision.inference import ModelDescriptor
from aiy.vision.models import utils
from aiy.vision.models.image_classification_classes import CLASSES


_COMPUTE_GRAPH_NAME = 'mobilenet_v1_160res_0.5_imagenet.binaryproto'


def model():
  return ModelDescriptor(
      name='image_classification',
      input_shape=(1, 160, 160, 3),
      input_normalizer=(128.0, 128.0),
      compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))


def get_classes(result, top_k=3):
  """Analyzes and reports what objects are in the given image.

  Args:
    result: dict of tensors, inference result
    top_k: int, returns top_k objects in the image.

  Returns:
    A list of (string, float) tuple, represents object, prob(object) reversely
      ordered by prob(object).
  """
  assert len(result.tensors) == 1
  tensor = result.tensors['MobilenetV1/Predictions/Softmax']
  probs, shape = tensor.data, tensor.shape
  assert (shape.batch, shape.height, shape.width, shape.depth) == (1, 1, 1,
                                                                   1001)
  pairs = sorted(enumerate(probs), key=lambda pair: pair[1], reverse=True)
  return [('/'.join(CLASSES[index]), prob) for index, prob in pairs[0:top_k]]
