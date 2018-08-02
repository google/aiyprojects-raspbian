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

from collections import namedtuple

from aiy.vision.inference import ModelDescriptor
from aiy.vision.models import utils


_COMPUTE_GRAPH_NAME = 'face_detection.binaryproto'

# face_score: float, face confidence score from 0.0 to 1.0.
# joy_score: float, face joy score from 0.0 to 1.0.
# bounding_box: (x, y, width, height) tuple.
Face = namedtuple('Face', ('face_score', 'joy_score', 'bounding_box'))


def model():
    # Face detection model has special implementation in VisionBonnet firmware.
    # input_shape, input_normalizer, and compute_graph params have no effect.
    return ModelDescriptor(
        name='FaceDetection',
        input_shape=(1, 0, 0, 3),
        input_normalizer=(0, 0),
        compute_graph=utils.load_compute_graph(_COMPUTE_GRAPH_NAME))


def get_faces(result):
    """Returns list of Face objects decoded from the inference result."""
    assert len(result.tensors) == 3
    # TODO(dkovalev): check tensor shapes
    bboxes = utils.reshape(result.tensors['bounding_boxes'].data, 4)
    face_scores = tuple(result.tensors['face_scores'].data)
    joy_scores = tuple(result.tensors['joy_scores'].data)
    assert len(bboxes) == len(joy_scores)
    assert len(bboxes) == len(face_scores)
    return [
        Face(face_score, joy_score, tuple(bbox))
        for face_score, joy_score, bbox in zip(face_scores, joy_scores, bboxes)
    ]
