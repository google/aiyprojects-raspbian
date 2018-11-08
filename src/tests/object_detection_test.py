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
from aiy.vision.models import object_detection as od
from .test_util import define_test_case, TestImage

def crop_center(image):
    width, height = image.size
    size = min(width, height)
    x, y = (width - size) / 2, (height - size) / 2
    return image.crop((x, y, x + size, y + size)), (x, y)


class ObjectDetectionTest:
    THRESHOLD = 0.3

    def __init__(self, image_file, sparse):
        self.image_file = image_file
        self.sparse = sparse
        self.check = {'dog.jpg': self.check_dog, 'cat.jpg': self.check_cat}[image_file]

    def check_dog(self, objects):
        self.assertEqual(1, len(objects))
        self.assertEqual(od.Object.DOG, objects[0].kind)
        self.assertAlmostEqual(0.914, objects[0].score, delta=0.001)
        self.assertEqual((52, 116, 570, 485), objects[0].bounding_box)


    def check_cat(self, objects):
        self.assertEqual(1, len(objects))
        self.assertEqual(od.Object.CAT, objects[0].kind)
        self.assertAlmostEqual(0.672, objects[0].score, delta=0.001)
        self.assertEqual((575, 586, 2187, 1758), objects[0].bounding_box)

    def test_detection(self):
        with TestImage(self.image_file) as image:
            image_center, offset = crop_center(image)
            with ImageInference(od.model()) as inference:
                if self.sparse:
                    sparse_configs = od.sparse_configs(threshold=self.THRESHOLD)
                    result = inference.run(image_center, sparse_configs=sparse_configs)
                    objects = od.get_objects_sparse(result, offset)
                else:
                    result = inference.run(image_center)
                    objects = od.get_objects(result, self.THRESHOLD, offset)
                self.check(objects)

define_test_case(globals(), ObjectDetectionTest, 'dog.jpg', False)
define_test_case(globals(), ObjectDetectionTest, 'dog.jpg', True)
define_test_case(globals(), ObjectDetectionTest, 'cat.jpg', False)
define_test_case(globals(), ObjectDetectionTest, 'cat.jpg', True)

if __name__ == '__main__':
    unittest.main(verbosity=2)
