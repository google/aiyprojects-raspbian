from collections import namedtuple

from aiy.vision.inference import ModelDescriptor, ThresholdingConfig
from aiy.vision.models import utils

PLANTS  = 'inaturalist_plants'
INSECTS = 'inaturalist_insects'
BIRDS   = 'inaturalist_birds'

class ModelType(namedtuple('ModelType', ('labels_file',
                                         'compute_graph_file',
                                         'input_shape',
                                         'input_normalizer',
                                         'output_name'))):
    def labels(self):
        if not hasattr(self, '_labels'):
          setattr(self, '_labels', utils.load_labels(self.labels_file))
        return self._labels

    def compute_graph(self):
        return utils.load_compute_graph(self.compute_graph_file)

_MODELS = {
   PLANTS:  ModelType(labels_file='mobilenet_v2_192res_1.0_inat_plant_labels.txt',
                      compute_graph_file='mobilenet_v2_192res_1.0_inat_plant.binaryproto',
                      input_shape=(1, 192, 192, 3),
                      input_normalizer=(128.0, 128.0),
                      output_name='prediction'),
   INSECTS: ModelType(labels_file='mobilenet_v2_192res_1.0_inat_insect_labels.txt',
                      compute_graph_file='mobilenet_v2_192res_1.0_inat_insect.binaryproto',
                      input_shape=(1, 192, 192, 3),
                      input_normalizer=(128.0, 128.0),
                      output_name='prediction'),
   BIRDS:   ModelType(labels_file='mobilenet_v2_192res_1.0_inat_bird_labels.txt',
                      compute_graph_file='mobilenet_v2_192res_1.0_inat_bird.binaryproto',
                      input_shape=(1, 192, 192, 3),
                      input_normalizer=(128.0, 128.0),
                      output_name='prediction'),
}


def sparse_configs(model_type, top_k=None, threshold=0.0):
    model = _MODELS[model_type]
    num_labels = len(model.labels())
    return {
        model.output_name: ThresholdingConfig(logical_shape=[num_labels],
                                              threshold=threshold,
                                              top_k=num_labels if top_k is None else top_k,
                                              to_ignore=[])
    }


def model(model_type):
    model = _MODELS[model_type]
    return ModelDescriptor(name=model_type,
                           input_shape=model.input_shape,
                           input_normalizer=model.input_normalizer,
                           compute_graph=model.compute_graph())


def get_classes(result, top_k=None, threshold=0.0):
    assert len(result.tensors) == 1

    model = _MODELS[result.model_name]
    labels = model.labels()

    tensor = result.tensors[model.output_name]
    probs, shape = tensor.data, tensor.shape
    assert shape.depth == len(labels)
    pairs = [pair for pair in enumerate(probs) if pair[1] > threshold]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    pairs = pairs[0:top_k]
    return [('/'.join(labels[index]), prob) for index, prob in pairs]


def get_classes_sparse(result):
    assert len(result.tensors) == 1

    model = _MODELS[result.model_name]
    labels = model.labels()

    tensor = result.tensors[model.output_name]
    indices, probs = tuple(tensor.indices), tuple(tensor.data)
    pairs = [(index.values[0], prob) for index, prob in zip(indices, probs)]
    pairs = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    return [('/'.join(labels[index]), prob) for index, prob in pairs]
