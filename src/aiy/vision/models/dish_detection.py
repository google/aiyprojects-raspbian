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

from collections import namedtuple

from aiy.vision.inference import ModelDescriptor
from aiy.vision.models import utils


_COMPUTE_GRAPH_NAME = 'dish_detection.binaryproto'
_CLASSES = utils.load_labels('mobilenet_v1_192res_1.0_seefood_labels.txt')

# sorted_scores: sorted list of (label, score) tuples.
# bounding_box: (x, y, width, height) tuple.
Dish = namedtuple('Dish', ('sorted_scores', 'bounding_box'))


def model():
    return ModelDescriptor(
        name='DishDetection',
        input_shape=(1, 0, 0, 3),
        input_normalizer=(0, 0),
        compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))


def _get_sorted_scores(scores, top_k, threshold):
    pairs = [('/'.join(_CLASSES[i]), prob) for i, prob in enumerate(scores) if prob > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    return pairs[0:top_k]


def get_dishes(result, top_k=3, threshold=0.1):
    """Returns list of Dish objects decoded from the inference result."""
    assert len(result.tensors) == 2
    bboxes = utils.reshape(result.tensors['bounding_boxes'].data, 4)
    dish_scores = utils.reshape(result.tensors['dish_scores'].data, len(_CLASSES))
    assert len(bboxes) == len(dish_scores)

    return [Dish(_get_sorted_scores(scores, top_k, threshold), tuple(bbox))
        for scores, bbox in zip(dish_scores, bboxes)]
