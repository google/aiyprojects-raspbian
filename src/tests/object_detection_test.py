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
from aiy.vision.models import object_detection
from .test_util import TestImage

def _crop_center(image):
    width, height = image.size
    size = min(width, height)
    x, y = (width - size) / 2, (height - size) / 2
    return image.crop((x, y, x + size, y + size)), (x, y)

class ObjectDetectionTest(unittest.TestCase):

    def testDog(self):
        with TestImage('dog.jpg') as image:
            image_center, offset = _crop_center(image)
            with ImageInference(object_detection.model()) as inference:
                objects = object_detection.get_objects(inference.run(image_center), 0.3, offset)
                self.assertEqual(1, len(objects))
                self.assertEqual(object_detection.Object.DOG, objects[0].kind)
                self.assertAlmostEqual(0.914, objects[0].score, delta=0.001)
                self.assertEqual((52, 116, 570, 485), objects[0].bounding_box)

    def testCat(self):
        with TestImage('cat.jpg') as image:
            image_center, offset = _crop_center(image)
            with ImageInference(object_detection.model()) as inference:
                objects = object_detection.get_objects(inference.run(image_center), 0.3, offset)
                print(objects[0])
                self.assertEqual(1, len(objects))
                self.assertEqual(object_detection.Object.CAT, objects[0].kind)
                self.assertAlmostEqual(0.672, objects[0].score, delta=0.001)
                self.assertEqual((575, 586, 2187, 1758), objects[0].bounding_box)


if __name__ == '__main__':
    unittest.main()
