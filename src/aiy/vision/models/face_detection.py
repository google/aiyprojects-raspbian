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
"""API for Face Detection."""

from __future__ import division

from aiy.vision.inference import ModelDescriptor
from aiy.vision.models import utils

_COMPUTE_GRAPH_NAME = 'face_detection.binaryproto'


def _reshape(array, width):
  assert len(array) % width == 0
  height = len(array) // width
  return [array[i * width:(i + 1) * width] for i in range(height)]


class Face(object):
  """Face detection result."""

  def __init__(self, bounding_box, face_score, joy_score):
    """Creates a new Face instance.

    Args:
      bounding_box: (x, y, width, height).
      face_score: float, face confidence score.
      joy_score: float, face joy score.
    """
    self.bounding_box = bounding_box
    self.face_score = face_score
    self.joy_score = joy_score

  def __str__(self):
    return 'face_score=%f, joy_score=%f, bbox=%s' % (self.face_score,
                                                     self.joy_score,
                                                     str(self.bounding_box))


def model():
  # Face detection model has special implementation in VisionBonnet firmware.
  # input_shape, input_normalizer, and computate_graph params have on effect.
  return ModelDescriptor(
      name='FaceDetection',
      input_shape=(1, 0, 0, 3),
      input_normalizer=(0, 0),
      compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))


def get_faces(result):
  """Retunrs list of Face objects decoded from the inference result."""
  assert len(result.tensors) == 3
  # TODO(dkovalev): check tensor shapes
  bboxes = _reshape(result.tensors['bounding_boxes'].data, 4)
  face_scores = result.tensors['face_scores'].data
  joy_scores = result.tensors['joy_scores'].data
  assert len(bboxes) == len(joy_scores)
  assert len(bboxes) == len(face_scores)
  return [
      Face(tuple(bbox), face_score, joy_score)
      for bbox, face_score, joy_score in zip(bboxes, face_scores, joy_scores)
  ]
