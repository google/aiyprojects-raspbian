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
"""API for Dish Detection."""

from __future__ import division

from aiy.vision.inference import ModelDescriptor
from aiy.vision.models.dish_classifier_classes import CLASSES
from aiy.vision.models import utils

_COMPUTE_GRAPH_NAME = 'dish_detection.binaryproto'


def _reshape(array, width):
    assert len(array) % width == 0
    height = len(array) // width
    return [array[i * width:(i + 1) * width] for i in range(height)]


def _get_sorted_score_map(score_vector, top_k, threshold):
    pairs = [pair for pair in enumerate(score_vector) if pair[1] > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    return pairs[0:top_k]


class Dish(object):
    """Dish detection result."""

    def __init__(self, bbox, sorted_score_map):
        self.bbox = bbox
        self.sorted_score_map = sorted_score_map

    def __str__(self):
        dish = '\t'.join(['%s (%.2f)' % ('/'.join(CLASSES[i]), prob) for
                          (i, prob) in self.sorted_score_map])
        return 'Bounding Box: %s\n Possible dish: %s' % (str(self.bbox), dish)


def model():
    # Dish detection model has special implementation in VisionBonnet firmware.
    # input_shape, input_normalizer, and compute_graph params have on effect.
    return ModelDescriptor(
        name='DishDetection',
        input_shape=(1, 0, 0, 3),
        input_normalizer=(0, 0),
        compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))


def get_dishes(result, top_k=3, threshold=0.1):
    """Returns list of Dish objects decoded from the inference result."""
    assert len(result.tensors) == 2
    bboxes = _reshape(result.tensors['bounding_boxes'].data, 4)
    dish_scores = _reshape(result.tensors['dish_scores'].data, len(CLASSES))
    assert len(bboxes) == len(dish_scores)
    sorted_dish_scores = [_get_sorted_score_map(score_vector, top_k, threshold)
                          for score_vector in dish_scores]
    return [
        Dish(tuple(bbox), sorted_score_map)
        for bbox, sorted_score_map in zip(bboxes, sorted_dish_scores)
    ]
