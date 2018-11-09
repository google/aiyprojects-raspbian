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
from aiy.vision.models import inaturalist_classification as m
from .test_util import define_test_case, TestImage

LILY_CLASSES = (
    ('Lilium canadense (Canada lily)',                 0.60107),
    ("Lilium superbum (Turk's-Cap lily)",              0.07489),
    ('Lilium parvum (Sierra Tiger Lily)',              0.05954),
    ('Lilium philadelphicum (Wood Lily)',              0.01994),
    ('Calochortus venustus (Butterfly Mariposa Lily)', 0.01755)
)

BEE_CLASSES = (
    ('Apis mellifera (Honey Bee)',                 0.65234),
    ('Ancistrocerus gazella (European Tube Wasp)', 0.00761),
    ('Vespula vulgaris (Common Yellowjacket)',     0.00698),
    ('Vespula germanica (German Wasp)',            0.00618),
    ('Eristalis tenax (Drone Fly)',                0.00440)
)

SPARROW_CLASSES = (
    ('Passer domesticus (House Sparrow)',          0.91943),
    ('Passer italiae (Italian Sparrow)',           0.01279),
    ('Passer montanus (Eurasian Tree Sparrow)',    0.00241),
    ('Sylvia communis (Greater Whitethroat)',      0.00198),
    ('Spiza americana (Dickcissel)',               0.00166),
)

class InaturalistClassificationTest:
    TOP_K = 5
    THRESHOLD = 0.0

    def __init__(self, model_type, sparse):
        self.model_type = model_type
        self.sparse = sparse

        self.image_file = {m.PLANTS:  'lily.jpg',
                           m.INSECTS: 'bee.jpg',
                           m.BIRDS:   'sparrow.jpg'}[model_type]

        self.classes = {m.PLANTS:  LILY_CLASSES,
                        m.INSECTS: BEE_CLASSES,
                        m.BIRDS:   SPARROW_CLASSES}[model_type]

    def check(self, classes):
        self.assertEqual(len(classes), len(self.classes))
        for (label1, prob1), (label2, prob2) in zip(classes, self.classes):
            self.assertEqual(label1, label2)
            self.assertAlmostEqual(prob1, prob2, delta=0.0001)

    def test_classification(self):
        with TestImage(self.image_file) as image:
            with ImageInference(m.model(self.model_type)) as inference:
                if self.sparse:
                    configs = m.sparse_configs(top_k=self.TOP_K,
                                               threshold=self.THRESHOLD,
                                               model_type=self.model_type)
                    result = inference.run(image, sparse_configs=configs)
                    classes = m.get_classes_sparse(result)
                else:
                    result = inference.run(image)
                    classes = m.get_classes(result, top_k=self.TOP_K, threshold=self.THRESHOLD)

                self.check(classes)


define_test_case(globals(), InaturalistClassificationTest, m.PLANTS, False)
define_test_case(globals(), InaturalistClassificationTest, m.PLANTS, True)
define_test_case(globals(), InaturalistClassificationTest, m.INSECTS, False)
define_test_case(globals(), InaturalistClassificationTest, m.INSECTS, True)
define_test_case(globals(), InaturalistClassificationTest, m.BIRDS, False)
define_test_case(globals(), InaturalistClassificationTest, m.BIRDS, True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
