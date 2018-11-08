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
from aiy.vision.models import image_classification as ic
from .test_util import define_test_case, TestImage

class ImageClassificationTest:
    TOP_K = 20
    THRESHOLD = 0.0

    def __init__(self, model_type, sparse):
        self.image_file = 'dog.jpg'
        self.model_type = model_type
        self.sparse = sparse
        self.check = {ic.MOBILENET: self.check_dog_mobilenet,
                      ic.SQUEEZENET: self.check_dog_squeezenet}[model_type]

    def check_dog_mobilenet(self, classes):
        label, score = classes[0]
        self.assertEqual('boxer', label)
        self.assertAlmostEqual(score, 0.684, delta=0.001)

        label, score = classes[1]
        self.assertEqual('bull mastiff', label)
        self.assertAlmostEqual(score, 0.222, delta=0.001)

    def check_dog_squeezenet(self, classes):
        label, score = classes[0]
        self.assertEqual('pug/pug-dog', label)
        self.assertAlmostEqual(score, 0.271, delta=0.001)

        label, score = classes[1]
        self.assertEqual('bull mastiff', label)
        self.assertAlmostEqual(score, 0.141, delta=0.001)

    def test_classification(self):
        with TestImage(self.image_file) as image:
            with ImageInference(ic.model(self.model_type)) as inference:
                if self.sparse:
                    sparse_configs = ic.sparse_configs(top_k=self.TOP_K,
                                                       threshold=self.THRESHOLD,
                                                       model_type=self.model_type)
                    result = inference.run(image, sparse_configs=sparse_configs)
                    classes = ic.get_classes_sparse(result)
                else:
                    result = inference.run(image)
                    classes = ic.get_classes(result, top_k=self.TOP_K, threshold=self.THRESHOLD)

                self.check(classes)

define_test_case(globals(), ImageClassificationTest, ic.MOBILENET, False)
define_test_case(globals(), ImageClassificationTest, ic.MOBILENET, True)
define_test_case(globals(), ImageClassificationTest, ic.SQUEEZENET, False)
define_test_case(globals(), ImageClassificationTest, ic.SQUEEZENET, True)

if __name__ == '__main__':
    unittest.main(verbosity=2)
