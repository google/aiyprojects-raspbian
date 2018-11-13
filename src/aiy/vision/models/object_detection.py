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
"""API for Object Detection tasks."""
import math
import sys

from collections import defaultdict

from aiy.vision.inference import ModelDescriptor, ThresholdingConfig, FromSparseTensorConfig
from aiy.vision.models import utils

_COMPUTE_GRAPH_NAME = 'mobilenet_ssd_256res_0.125_person_cat_dog.binaryproto'
_MACHINE_EPS = sys.float_info.epsilon
_SCORE_TENSOR_NAME = 'concat_1'
_ANCHOR_TENSOR_NAME = 'concat'
_DEFAULT_THRESHOLD = 0.3
_ANCHORS = utils.load_ssd_anchors('mobilenet_ssd_256res_0.125_person_cat_dog_anchors.txt')
_NUM_ANCHORS = len(_ANCHORS)

def _logit(x):
    return math.log(x / (1.0 - x))

def _logistic(x):
    return 1.0 / (1.0 + math.exp(-x))

def sparse_configs(threshold=_DEFAULT_THRESHOLD):
    if threshold < 0 or threshold > 1.0:
        raise ValueError('Threshold must be in [0.0, 1.0]')

    return {
        _SCORE_TENSOR_NAME: ThresholdingConfig(logical_shape=[_NUM_ANCHORS, 4],
                                               threshold=_logit(max(threshold, _MACHINE_EPS)),
                                               top_k=_NUM_ANCHORS,
                                               to_ignore=[(1, 0)]),
        _ANCHOR_TENSOR_NAME: FromSparseTensorConfig(logical_shape=[_NUM_ANCHORS],
                                                    tensor_name=_SCORE_TENSOR_NAME,
                                                    squeeze_dims=[1])
    }

class Object:
    """Object detection result."""
    BACKGROUND = 0
    PERSON = 1
    CAT = 2
    DOG = 3

    _LABELS = {
        BACKGROUND: 'BACKGROUND',
        PERSON: 'PERSON',
        CAT: 'CAT',
        DOG: 'DOG',
    }

    def __init__(self, bounding_box, kind, score):
        """Initialization.

        Args:
          bounding_box: a tuple of 4 ints, (x, y, width, height) order.
          kind: int, tells what object is in the bounding box.
          score: float, confidence score.
        """
        self.bounding_box = bounding_box
        self.kind = kind
        self.score = score

    def __str__(self):
        return 'kind=%s(%d), score=%f, bbox=%s' % (self._LABELS[self.kind],
                                                   self.kind, self.score,
                                                   str(self.bounding_box))

def _decode_detection_result(logit_scores, box_encodings, threshold,
                             image_size, image_offset):
    assert len(logit_scores) == 4 * _NUM_ANCHORS
    assert len(box_encodings) == 4 * _NUM_ANCHORS

    logit_threshold = _logit(max(threshold, _MACHINE_EPS))
    objs = []

    for i in range(_NUM_ANCHORS):
        logits = logit_scores[4 * i: 4 * (i + 1)]
        max_logit = max(logits)
        max_logit_index = logits.index(max_logit)
        if max_logit_index == 0 or max_logit <= logit_threshold:
            continue  # Skip 'background' and below threshold.

        bbox = _decode_bbox(box_encodings[4 * i: 4 * (i + 1)], _ANCHORS[i],
                            image_size, image_offset)
        objs.append(Object(bbox, max_logit_index, _logistic(max_logit)))

    return objs


def _decode_sparse_detection_result(logit_scores_indices, logit_scores,
                                    box_encodings_indices, box_encodings,
                                    image_size, image_offset):
    assert len(logit_scores_indices) == len(logit_scores)
    assert 4 * len(box_encodings_indices) == len(box_encodings)

    logits_dict = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    objs = []

    for index, logit_score in zip(logit_scores_indices, logit_scores):
        i, logit_index = index.values
        logits_dict[i][logit_index] = logit_score

    for j, index in enumerate(box_encodings_indices):
        i, = index.values

        logits = logits_dict[i]
        max_logit = max(logits)
        max_logit_index = logits.index(max_logit)

        bbox = _decode_bbox(box_encodings[4 * j: 4 * (j + 1)], _ANCHORS[i],
                            image_size, image_offset)
        objs.append(Object(bbox, max_logit_index, _logistic(max_logit)))

    return objs

def _clamp(value):
    """Clamps value to range [0.0, 1.0]."""
    return min(max(0.0, value), 1.0)

def _decode_bbox(box_encoding, anchor, image_size, image_offset):
    x0, y0 = image_offset
    width, height = image_size
    xmin, ymin, xmax, ymax = _decode_box_encoding(box_encoding, anchor)
    x = int(x0 + xmin * width)
    y = int(y0 + ymin * height)
    w = int((xmax - xmin) * width)
    h = int((ymax - ymin) * height)
    return x, y, w, h

def _decode_box_encoding(box_encoding, anchor):
    """Decodes bounding box encoding.

    Args:
      box_encoding: a tuple of 4 floats.
      anchor: a tuple of 4 floats.
    Returns:
      A tuple of 4 floats (xmin, ymin, xmax, ymax), each has range [0.0, 1.0].
    """
    assert len(box_encoding) == 4
    assert len(anchor) == 4
    y_scale = 10.0
    x_scale = 10.0
    height_scale = 5.0
    width_scale = 5.0

    rel_y_translation = box_encoding[0] / y_scale
    rel_x_translation = box_encoding[1] / x_scale
    rel_height_dilation = box_encoding[2] / height_scale
    rel_width_dilation = box_encoding[3] / width_scale

    anchor_ymin, anchor_xmin, anchor_ymax, anchor_xmax = anchor
    anchor_ycenter = (anchor_ymax + anchor_ymin) / 2
    anchor_xcenter = (anchor_xmax + anchor_xmin) / 2
    anchor_height = anchor_ymax - anchor_ymin
    anchor_width = anchor_xmax - anchor_xmin

    ycenter = anchor_ycenter + anchor_height * rel_y_translation
    xcenter = anchor_xcenter + anchor_width * rel_x_translation
    height = math.exp(rel_height_dilation) * anchor_height
    width = math.exp(rel_width_dilation) * anchor_width

    # Clamp value to [0.0, 1.0] range, otherwise, part of the bounding box may
    # fall outside of the image.
    xmin = _clamp(xcenter - width / 2)
    ymin = _clamp(ycenter - height / 2)
    xmax = _clamp(xcenter + width / 2)
    ymax = _clamp(ycenter + height / 2)

    return xmin, ymin, xmax, ymax


def _area(box):
    _, _, width, height = box
    area = width * height
    assert area >= 0
    return area


def _intersection_area(box1, box2):
    x1, y1, width1, height1 = box1
    x2, y2, width2, height2 = box2
    x = max(x1, x2)
    y = max(y1, y2)
    width = max(min(x1 + width1, x2 + width2) - x, 0)
    height = max(min(y1 + height1, y2 + height2) - y, 0)
    area = width * height
    assert area >= 0
    return area


def _overlap_ratio(box1, box2):
    """Computes overlap ratio of two bounding boxes.

    Args:
      box1: (x, y, width, height).
      box2: (x, y, width, height).

    Returns:
      float, represents overlap ratio between given boxes.
    """
    intersection_area = _intersection_area(box1, box2)
    union_area = _area(box1) + _area(box2) - intersection_area
    assert union_area >= 0
    if union_area > 0:
        return float(intersection_area) / float(union_area)
    return 1.0


def _non_maximum_suppression(objs, overlap_threshold=0.5):
    """Runs Non Maximum Suppression.

    Removes candidate that overlaps with existing candidate who has higher
    score.

    Args:
      objs: list of ObjectDetection.Object
      overlap_threshold: float
    Returns:
      A list of ObjectDetection.Object
    """
    objs = sorted(objs, key=lambda x: x.score, reverse=True)
    for i in range(len(objs)):
        if objs[i].score < 0.0:
            continue
        # Suppress any nearby bounding boxes having lower score than boxes[i]
        for j in range(i + 1, len(objs)):
            if objs[j].score < 0.0:
                continue
            if _overlap_ratio(objs[i].bounding_box,
                              objs[j].bounding_box) > overlap_threshold:
                objs[j].score = -1.0  # Suppress box

    return [obj for obj in objs if obj.score >= 0.0]  # Exclude suppressed boxes


def model():
    return ModelDescriptor(
        name='object_detection',
        input_shape=(1, 256, 256, 3),
        input_normalizer=(128.0, 128.0),
        compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))

def get_objects(result, threshold=_DEFAULT_THRESHOLD, offset=(0, 0)):
    if threshold < 0 or threshold > 1.0:
        raise ValueError('Threshold must be in [0.0, 1.0]')

    assert len(result.tensors) == 2
    logit_scores = tuple(result.tensors[_SCORE_TENSOR_NAME].data)
    box_encodings = tuple(result.tensors[_ANCHOR_TENSOR_NAME].data)

    size = (result.window.width, result.window.height)
    objs = _decode_detection_result(logit_scores, box_encodings, threshold, size, offset)
    return _non_maximum_suppression(objs)


def get_objects_sparse(result, offset=(0, 0)):
    assert len(result.tensors) == 2

    logit_scores_indices = tuple(result.tensors[_SCORE_TENSOR_NAME].indices)
    logit_scores = tuple(result.tensors[_SCORE_TENSOR_NAME].data)
    box_encodings_indices = tuple(result.tensors[_ANCHOR_TENSOR_NAME].indices)
    box_encodings = tuple(result.tensors[_ANCHOR_TENSOR_NAME].data)

    size = (result.window.width, result.window.height)
    objs = _decode_sparse_detection_result(logit_scores_indices, logit_scores,
                                           box_encodings_indices, box_encodings,
                                           size, offset)
    return _non_maximum_suppression(objs)