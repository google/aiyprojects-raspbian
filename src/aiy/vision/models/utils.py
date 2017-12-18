"""Utility to load compute graphs from diffrent sources."""

import os

def load_compute_graph(name):
  path = os.path.join('/opt/aiy/models', name)
  with open(path, 'rb') as f:
    return f.read()

