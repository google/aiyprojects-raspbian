"""Set of reusable utilities to work with AIY models."""

import os


def _path(filename):
    path = os.environ.get('VISION_BONNET_MODELS_PATH', '/opt/aiy/models')
    return os.path.join(path, filename)


def load_compute_graph(filename):
    with open(_path(filename), 'rb') as f:
        return f.read()

def load_labels(filename):
    def split(line):
        return tuple(word.strip() for word in line.split(','))

    with open(_path(filename), encoding='utf-8') as f:
        return tuple(split(line) for line in f)

def load_ssd_anchors(filename):
    def split(line):
        return tuple(float(word.strip()) for word in line.split(' '))

    with open(_path(filename), encoding='utf-8') as f:
        return tuple(split(line) for line in f)


def shape_tuple(shape):
    return (shape.batch, shape.height, shape.width, shape.depth)

def reshape(array, width):
    assert len(array) % width == 0
    height = len(array) // width
    return [array[i * width:(i + 1) * width] for i in range(height)]
