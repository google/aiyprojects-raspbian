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
from aiy.vision.models import dish_detection
from .test_util import TestImage


class DishDetectionTest(unittest.TestCase):

    def testHotdog(self):
        with TestImage('hotdog.jpg') as image:
            with ImageInference(dish_detection.model()) as inference:
                dishes = dish_detection.get_dishes(inference.run(image), top_k=3, threshold=0.1)
                self.assertEqual(1, len(dishes))
                dish = dishes[0]

                self.assertEqual((417.0, 51.0, 2438.0, 2388.0), dish.bounding_box)
                self.assertEqual(2, len(dish.sorted_scores))

                label, score = dish.sorted_scores[0]
                self.assertEqual('Hot dog', label)
                self.assertAlmostEqual(0.223, score, delta=0.001)

                label, score = dish.sorted_scores[1]
                self.assertEqual('Bento', label)
                self.assertAlmostEqual(0.152, score, delta=0.001)

if __name__ == '__main__':
    unittest.main()
