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
from aiy.vision.models import image_classification
from .test_util import TestImage


class ImageClassificationTest(unittest.TestCase):

    def testDogMobilenet(self):
        with TestImage('dog.jpg') as image:
            with ImageInference(
                image_classification.model(image_classification.MOBILENET)) as inference:
                classes = image_classification.get_classes(inference.run(image))
                label, score = classes[0]
                self.assertEqual('boxer', label)
                self.assertAlmostEqual(score, 0.684, delta=0.001)

                label, score = classes[1]
                self.assertEqual('bull mastiff', label)
                self.assertAlmostEqual(score, 0.222, delta=0.001)

    def testDogSqueezenet(self):
        with TestImage('dog.jpg') as image:
            with ImageInference(
                image_classification.model(image_classification.SQUEEZENET)) as inference:
                classes = image_classification.get_classes(inference.run(image))

                label, score = classes[0]
                self.assertEqual('pug/pug-dog', label)
                self.assertAlmostEqual(score, 0.271, delta=0.001)

                label, score = classes[1]
                self.assertEqual('bull mastiff', label)
                self.assertAlmostEqual(score, 0.141, delta=0.001)

if __name__ == '__main__':
    unittest.main()
