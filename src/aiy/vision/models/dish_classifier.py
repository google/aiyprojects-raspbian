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
"""API for Dish Classifier."""

from aiy.vision.inference import ModelDescriptor
from aiy.vision.models import utils
from aiy.vision.models.dish_classifier_classes import CLASSES

_COMPUTE_GRAPH_NAME = 'mobilenet_v1_192res_1.0_seefood.binaryproto'


def model():
    return ModelDescriptor(
        name='dish_classifier',
        input_shape=(1, 192, 192, 3),
        input_normalizer=(128.0, 128.0),
        compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))


def get_classes(result, max_num_objects=None, object_prob_threshold=0.0):
    """Converts dish classifier model output to list of detected objects.

    Args:
      result: output tensor from dish classifier model.
      max_num_objects: int; max number of objects to return.
      object_prob_threshold: float; min probability of each returned object.

    Returns:
      A list of (class_name: string, probability: float) pairs ordered by
      probability from highest to lowest. The number of pairs is not greater than
      max_num_objects. Each probability is greater than object_prob_threshold. For
      example:

      [('Ramen', 0.981934)
       ('Yaka mein, 0.005497)]
    """
    assert len(result.tensors) == 1
    tensor = result.tensors['MobilenetV1/Predictions/Softmax']
    probs, shape = tensor.data, tensor.shape
    assert (shape.batch, shape.height, shape.width, shape.depth) == (1, 1, 1,
                                                                     2024)

    pairs = [pair for pair in enumerate(probs) if pair[1] > object_prob_threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    pairs = pairs[0:max_num_objects]
    return [('/'.join(CLASSES[index]), prob) for index, prob in pairs]
