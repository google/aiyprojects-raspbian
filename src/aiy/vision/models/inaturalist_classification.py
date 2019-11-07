# Copyright 2018 Google Inc.
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

"""
API for detecting plants, insects, and birds from the iNaturalist dataset.
"""

from collections import namedtuple

from aiy.vision.inference import ModelDescriptor, ThresholdingConfig
from aiy.vision.models import utils

PLANTS  = 'inaturalist_plants'
INSECTS = 'inaturalist_insects'
BIRDS   = 'inaturalist_birds'

class Model(namedtuple('Model', ('labels',
                                 'compute_graph_file',
                                 'input_shape',
                                 'input_normalizer',
                                 'output_name'))):
    def compute_graph(self):
        return utils.load_compute_graph(self.compute_graph_file)

_MODELS = {
   PLANTS:  Model(labels=utils.load_labels('mobilenet_v2_192res_1.0_inat_plant_labels.txt'),
                  compute_graph_file='mobilenet_v2_192res_1.0_inat_plant.binaryproto',
                  input_shape=(1, 192, 192, 3),
                  input_normalizer=(128.0, 128.0),
                  output_name='prediction'),
   INSECTS: Model(labels=utils.load_labels('mobilenet_v2_192res_1.0_inat_insect_labels.txt'),
                  compute_graph_file='mobilenet_v2_192res_1.0_inat_insect.binaryproto',
                  input_shape=(1, 192, 192, 3),
                  input_normalizer=(128.0, 128.0),
                  output_name='prediction'),
   BIRDS:   Model(labels=utils.load_labels('mobilenet_v2_192res_1.0_inat_bird_labels.txt'),
                  compute_graph_file='mobilenet_v2_192res_1.0_inat_bird.binaryproto',
                  input_shape=(1, 192, 192, 3),
                  input_normalizer=(128.0, 128.0),
                  output_name='prediction'),
}


def sparse_configs(model_type, top_k=None, threshold=0.0):
    this_model = _MODELS[model_type]
    num_labels = len(this_model.labels)
    return {
        this_model.output_name: ThresholdingConfig(logical_shape=[num_labels],
                                                   threshold=threshold,
                                                   top_k=num_labels if top_k is None else top_k,
                                                   to_ignore=[])
    }


def model(model_type):
    this_model = _MODELS[model_type]
    return ModelDescriptor(name=model_type,
                           input_shape=this_model.input_shape,
                           input_normalizer=this_model.input_normalizer,
                           compute_graph=this_model.compute_graph())


def get_classes(result, top_k=None, threshold=0.0):
    assert len(result.tensors) == 1

    this_model = _MODELS[result.model_name]
    labels = this_model.labels

    tensor = result.tensors[this_model.output_name]
    probs, shape = tensor.data, tensor.shape
    assert shape.depth == len(labels)
    pairs = [pair for pair in enumerate(probs) if pair[1] > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    pairs = pairs[0:top_k]
    return [('/'.join(labels[index]), prob) for index, prob in pairs]


def get_classes_sparse(result):
    assert len(result.tensors) == 1

    this_model = _MODELS[result.model_name]
    labels = this_model.labels

    tensor = result.tensors[this_model.output_name]
    indices, probs = tuple(tensor.indices), tuple(tensor.data)
    pairs = [(index.values[0], prob) for index, prob in zip(indices, probs)]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    return [('/'.join(labels[index]), prob) for index, prob in pairs]
