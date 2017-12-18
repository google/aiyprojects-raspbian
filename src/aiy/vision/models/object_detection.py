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

from aiy.vision.inference import ModelDescriptor
from aiy.vision.models import utils
from aiy.vision.models.object_detection_anchors import ANCHORS

_COMPUTE_GRAPH_NAME = 'mobilenet_ssd_256res_0.125_person_cat_dog.binaryproto'


class Object(object):
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


def _reshape(array, height, width):
  assert len(array) == height * width
  return [array[i * width:(i + 1) * width] for i in range(height)]


def _decode_and_nms_detection_result(logit_scores, box_encodings, anchors,
                                     score_threshold, image_size, offset):
  """Decodes result as bounding boxes and runs Non-Maximum Suppression.

  Args:
    logit_scores: list of scores
    box_encodings: list of bounding boxes
    anchors: list of anchors
    score_threshold: float, bounding box candidates below this threshold will
      be rejected.
    image_size: (width, height)
    offset: (x, y)
  Returns:
    A list of ObjectDetection.Result.
  """

  assert len(box_encodings) == len(anchors)
  assert len(logit_scores) == len(anchors)

  x0, y0 = offset
  results = []
  for logit_score, box_encoding, anchor in zip(logit_scores, box_encodings,
                                               anchors):
    scores = _logit_score_to_score(logit_score)
    max_score_index, max_score = max(enumerate(scores), key=lambda x: x[1])
    # Skip if max score is below threshold or max score is 'background'.
    if max_score <= score_threshold or max_score_index == 0:
      continue

    x, y, w, h = _decode_box_encoding(box_encoding, anchor, image_size)
    results.append(Object((x0 + x, y0 + y, w, h), max_score_index, max_score))

  return _non_maximum_suppression(results)


def _logit_score_to_score(logit_score):
  return [1.0 / (1.0 + math.exp(-val)) for val in logit_score]


def _decode_box_encoding(box_encoding, anchor, image_size):
  """Decodes bounding box encoding.

  Args:
    box_encoding: a tuple of 4 floats.
    anchor: a tuple of 4 floats.
    image_size: a tuple of 2 ints, (width, height)
  Returns:
    A tuple of 4 integer, in the order of (left, upper, right, lower).
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

  image_width, image_height = image_size
  x0 = int(max(0.0, xcenter - width / 2) * image_width)
  y0 = int(max(0.0, ycenter - height / 2) * image_height)
  x1 = int(min(1.0, xcenter + width / 2) * image_width)
  y1 = int(min(1.0, ycenter + height / 2) * image_height)
  return (x0, y0, x1 - x0, y1 - y0)


def _overlap_ratio(box1, box2):
  """Computes overlap ratio of two bounding boxes.

  Args:
    box1: (x, y, width, height).
    box2: (x, y, width, height).

  Returns:
    float, represents overlap ratio between given boxes.
  """

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

  intersection_area = _intersection_area(box1, box2)
  union_area = _area(box1) + _area(box2) - intersection_area
  assert union_area >= 0
  if union_area > 0:
    return float(intersection_area) / float(union_area)
  return 1.0


def _non_maximum_suppression(boxes, overlap_threshold=0.5):
  """Runs Non Maximum Suppression.

  Removes box candidate that overlaps with existing candidate who has higher
  score.

  Args:
    boxes: list of Object
    overlap_threshold: float
  Returns:
    A list of Object
  """
  boxes = sorted(boxes, key=lambda x: x.score, reverse=True)
  for i in range(len(boxes)):
    if boxes[i].score < 0.0:
      continue
    # Suppress any nearby bounding boxes having lower score than boxes[i]
    for j in range(i + 1, len(boxes)):
      if boxes[j].score < 0.0:
        continue
      if _overlap_ratio(boxes[i].bounding_box,
                        boxes[j].bounding_box) > overlap_threshold:
        boxes[j].score = -1.0  # Suppress box

  return [box for box in boxes if box.score >= 0.0]  # Exclude suppressed boxes


def model():
  return ModelDescriptor(
      name='object_detection',
      input_shape=(1, 256, 256, 3),
      input_normalizer=(128.0, 128.0),
      compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))


# TODO: check all tensor shapes
def get_objects(result, score_threshold=0.3, offset=(0, 0)):
  assert len(result.tensors) == 2
  logit_scores = result.tensors['concat_1'].data
  logit_scores = _reshape(logit_scores, len(ANCHORS), 4)
  box_encodings = result.tensors['concat'].data
  box_encodings = _reshape(box_encodings, len(ANCHORS), 4)

  size = (result.window.width, result.window.height)
  return _decode_and_nms_detection_result(logit_scores, box_encodings, ANCHORS,
                                          score_threshold, size, offset)
