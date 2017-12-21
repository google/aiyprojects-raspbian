"""Utility to load compute graphs from diffrent sources."""

import os


def load_compute_graph(name):
  path = os.environ.get('VISION_BONNET_MODELS_PATH', '/opt/aiy/models')
  with open(os.path.join(path, name), 'rb') as f:
    return f.read()
