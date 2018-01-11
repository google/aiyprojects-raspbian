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

# There are two models in our repository that can do image classification. One
# based on MobileNet model structure, the other based on SqueezeNet model
# structure.
#
# MobileNet based model has 59.9% top-1 accuracy on ImageNet.
# SqueezeNet based model has 45.3% top-1 accuracy on ImageNet.
MOBILENET = 'image_classification_mobilenet'
SQUEEZENET = 'image_classification_squeezenet'
_COMPUTE_GRAPH_NAME_MAP = {
    MOBILENET: 'mobilenet_v1_160res_0.5_imagenet.binaryproto',
    SQUEEZENET: 'squeezenet_160res_5x5_0.75.binaryproto',
}
_OUTPUT_TENSOR_NAME_MAP = {
    MOBILENET: 'MobilenetV1/Predictions/Softmax',
    SQUEEZENET: 'Prediction',
}


def model(model_type=MOBILENET):
    return ModelDescriptor(
        name=model_type,
        input_shape=(1, 160, 160, 3),
        input_normalizer=(128.0, 128.0),
        compute_graph=utils.load_compute_graph(
            _COMPUTE_GRAPH_NAME_MAP[model_type]))


def get_classes(result, max_num_objects=None, object_prob_threshold=0.0):
    """Converts image classification model output to list of detected objects.

    Args:
      result: output tensor from image classification model.
      max_num_objects: int; max number of objects to return.
      object_prob_threshold: float; min probability of each returned object.

    Returns:
      A list of (class_name: string, probability: float) pairs ordered by
      probability from highest to lowest. The number of pairs is not greater than
      max_num_objects. Each probability is greater than object_prob_threshold. For
      example:

      [('Egyptian cat', 0.767578)
       ('tiger cat, 0.163574)
       ('lynx/catamount', 0.039795)]
    """
    assert len(result.tensors) == 1
    tensor_name = _OUTPUT_TENSOR_NAME_MAP[result.model_name]
    tensor = result.tensors[tensor_name]
    probs, shape = tensor.data, tensor.shape
    assert (shape.batch, shape.height, shape.width, shape.depth) == (1, 1, 1,
                                                                     1001)

    pairs = [pair for pair in enumerate(probs) if pair[1] > object_prob_threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    pairs = pairs[0:max_num_objects]
    return [('/'.join(CLASSES[index]), prob) for index, prob in pairs]
