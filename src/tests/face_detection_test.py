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
import unittest

from aiy.vision.inference import ImageInference
from aiy.vision.models import face_detection
from .test_util import TestImage


class FaceDetectionTest(unittest.TestCase):

    def testFaceDetection(self):
        with TestImage('faces.jpg') as image:
            with ImageInference(face_detection.model()) as inference:
                faces = face_detection.get_faces(inference.run(image))
                self.assertEqual(2, len(faces))

                face0 = faces[0]
                self.assertAlmostEqual(face0.face_score, 1.0, delta=0.001)
                self.assertAlmostEqual(face0.joy_score, 0.969, delta=0.001)
                self.assertEqual((812.0, 44.0, 1000.0, 1000.0), face0.bounding_box)

                face1 = faces[1]
                self.assertAlmostEqual(face1.face_score, 0.884, delta=0.001)
                self.assertAlmostEqual(face1.joy_score, 0.073, delta=0.001)
                self.assertEqual((748.0, 1063.0, 496.0, 496.0), face1.bounding_box)

    def testFaceDetectionWithParams(self):
        with TestImage('faces.jpg') as image:
            with ImageInference(face_detection.model()) as inference:
                params = {'max_face_size': 500}
                faces = face_detection.get_faces(inference.run(image, params))
                self.assertEqual(1, len(faces))

                face0 = faces[0]
                self.assertAlmostEqual(face0.face_score, 0.884, delta=0.001)
                self.assertAlmostEqual(face0.joy_score, 0.073, delta=0.001)
                self.assertEqual((748.0, 1063.0, 496.0, 496.0), face0.bounding_box)

if __name__ == '__main__':
    unittest.main()
