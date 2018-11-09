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

from aiy.vision.inference import ModelDescriptor, ThresholdingConfig
from aiy.vision.models import utils

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

_CLASSES = utils.load_labels('mobilenet_v1_160res_0.5_imagenet_labels.txt')

def sparse_configs(top_k=len(_CLASSES), threshold=0.0, model_type=MOBILENET):
    name = _OUTPUT_TENSOR_NAME_MAP[model_type]
    return {
        name: ThresholdingConfig(logical_shape=[len(_CLASSES)],
                                 threshold=threshold,
                                 top_k=top_k,
                                 to_ignore=[])
    }

def model(model_type=MOBILENET):
    return ModelDescriptor(
        name=model_type,
        input_shape=(1, 160, 160, 3),
        input_normalizer=(128.0, 128.0),
        compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME_MAP[model_type]))


def _get_probs(result):
    assert len(result.tensors) == 1
    tensor = result.tensors[_OUTPUT_TENSOR_NAME_MAP[result.model_name]]
    assert utils.shape_tuple(tensor.shape) == (1, 1, 1, len(_CLASSES))
    return tuple(tensor.data)


def get_classes(result, top_k=None, threshold=0.0):
    """Converts image classification model output to list of detected objects.

    Args:
      result: output tensor from image classification model.
      top_k: int; max number of objects to return.
      threshold: float; min probability of each returned object.

    Returns:
      A list of (class_name: string, probability: float) pairs ordered by
      probability from highest to lowest. The number of pairs is not greater than
      top_k. Each probability is greater than threshold. For
      example:

      [('Egyptian cat', 0.767578)
       ('tiger cat, 0.163574)
       ('lynx/catamount', 0.039795)]
    """
    probs = _get_probs(result)
    pairs = [pair for pair in enumerate(probs) if pair[1] > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    pairs = pairs[0:top_k]
    return [('/'.join(_CLASSES[index]), prob) for index, prob in pairs]


def _get_pairs(result):
    assert len(result.tensors) == 1
    tensor = result.tensors[_OUTPUT_TENSOR_NAME_MAP[result.model_name]]
    indices = tuple(tensor.indices)
    data = tuple(tensor.data)
    return [(index.values[0], prob) for index, prob in zip(indices, data)]


def get_classes_sparse(result):
    """Converts sparse image classification model output to list of detected objects.

    Args:
      result: sparse output tensor from image classification model.

    Returns:
      A list of (class_name: string, probability: float) pairs ordered by
      probability from highest to lowest.
      For example:

      [('Egyptian cat', 0.767578)
       ('tiger cat, 0.163574)
    """
    pairs = _get_pairs(result)
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    return [('/'.join(_CLASSES[index]), prob) for index, prob in pairs]
