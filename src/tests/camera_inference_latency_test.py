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
"""Tests to make sure end-to-end camera inference latency is reasonable."""

import time
import unittest

from picamera import PiCamera

from aiy.vision.inference import CameraInference
from aiy.vision.models import dish_classification
from aiy.vision.models import face_detection
from aiy.vision.models import image_classification
from aiy.vision.models import object_detection


class LatencyTest(unittest.TestCase):

    def benchmarkModel(self, model, interpret, num_frames=30):
        """Benchmarks model and reports end-to-end + on bonnet latency.

        Args:
          model: ModelDescriptor.
          interpret: function object on how to interpret inference result.
          num_frames: number of frames to run inference on.

        Returns:
          (avg_end_to_end, avg_bonnet) latency tuple in ms.
        """
        with PiCamera(sensor_mode=4, framerate=30), CameraInference(model) as inference:
            sum_bonnet_ms = 0
            start = time.monotonic()
            for result in inference.run(num_frames):
                interpret(result)
                sum_bonnet_ms += result.duration_ms
            sum_overall_ms = (time.monotonic() - start) * 1000
            return (sum_overall_ms / num_frames, sum_bonnet_ms / num_frames)

    def assertLatency(self, measured, expected, variation=0.2):
        lower = (1 - variation) * expected
        upper = (1 + variation) * expected
        if measured > upper or measured < lower:
            raise AssertionError(
                'Measured %f latency is outside of [%f, %f] interval' % (measured, lower, upper))

    def testFaceDetectionLatency(self):
        avg_end_to_end, avg_bonnet = self.benchmarkModel(
            face_detection.model(), face_detection.get_faces)
        # Latency depends on number of faces in the scene, which is
        # unpredictable when the test runs. Setting a larger variation value
        # here to accommodate this.
        self.assertLatency(avg_bonnet, 76.0, variation=0.6)
        self.assertLatency(avg_end_to_end, 91.0, variation=0.6)

    def testObjectDetectionLatency(self):
        avg_end_to_end, avg_bonnet = self.benchmarkModel(
            object_detection.model(), object_detection.get_objects)
        self.assertLatency(avg_bonnet, 36.0)
        self.assertLatency(avg_end_to_end, 153.0)

    def testImageClassificationMobilenetLatency(self):
        avg_end_to_end, avg_bonnet = self.benchmarkModel(
            image_classification.model(image_classification.MOBILENET),
            image_classification.get_classes)
        self.assertLatency(avg_bonnet, 42.0)
        self.assertLatency(avg_end_to_end, 80.0, 0.3)

    def testImageClassificationSqueezenetLatency(self):
        avg_end_to_end, avg_bonnet = self.benchmarkModel(
            image_classification.model(image_classification.SQUEEZENET),
            image_classification.get_classes)
        self.assertLatency(avg_bonnet, 183.0)
        self.assertLatency(avg_end_to_end, 202.0)

    def testDishClassificationLatency(self):
        avg_end_to_end, avg_bonnet = self.benchmarkModel(
            dish_classification.model(), dish_classification.get_classes)
        self.assertLatency(avg_bonnet, 304.0)
        self.assertLatency(avg_end_to_end, 328.0)


if __name__ == '__main__':
    unittest.main()
