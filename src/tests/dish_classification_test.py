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
from aiy.vision.models import dish_classification
from .test_util import TestImage


class DishClassificationTest(unittest.TestCase):

    def testHotdog(self):
        with TestImage('hotdog.jpg') as image:
            with ImageInference(dish_classification.model()) as inference:
                classes = dish_classification.get_classes(inference.run(image))
                label, score = classes[0]
                self.assertEqual('Hot dog', label)
                self.assertAlmostEqual(score, 0.744, delta=0.001)

                label, score = classes[1]
                self.assertEqual('Lobster roll', label)
                self.assertAlmostEqual(score, 0.119, delta=0.001)


if __name__ == '__main__':
    unittest.main()
