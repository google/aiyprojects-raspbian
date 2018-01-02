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
"""VisionBonnet InferenceEngine API.

Python API to communicate with the VisionBonnet from the Raspberry Pi side.

It can be used to load a model, analyze local image or image from camera
shot. It automatically unload the model once the associated object is
deleted. See image_classification.py and object_recognition.py as examples on
how to use this API.
"""

import logging
from aiy._drivers._transport import make_transport
from aiy.vision.proto import protocol_pb2


def _tobytes(img):
  try:
    return img.tobytes()
  except AttributeError:
    return img.tostring()


class CameraInference(object):
  """Helper class to run camera inference."""

  def __init__(self, descriptor, params=None):
    self._engine = InferenceEngine()
    self._key = self._engine.load_model(descriptor)
    self._engine.start_camera_inference(self._key, params)

  def camera_state(self):
    return self._engine.get_camera_state()

  def run(self):
    while True:
      yield self._engine.camera_inference()

  def close(self):
    self._engine.stop_camera_inference()
    self._engine.unload_model(self._key)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, exc_tb):
    self.close()


class ImageInference(object):
  """Helper class to run image inference."""

  def __init__(self, descriptor):
    self._engine = InferenceEngine()
    self._key = self._engine.load_model(descriptor)

  def run(self, image, params=None):
    return self._engine.image_inference(self._key, image, params)

  def close(self):
    self._engine.unload_model(self._key)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, exc_tb):
    self.close()


class ModelDescriptor(object):
  """Info used by VisionBonnet to load model."""

  def __init__(self, name, input_shape, input_normalizer, compute_graph):
    """Initialzes ModelDescriptor.

    Args:
      name: string, a name used to refer the model, should not conflict
        with existing model names.
      input_shape: (batch, height, width, depth). For now, only batch=1 and
        depth=3 are supported.
      input_normalizer: (mean, stddev) to convert input image (for analysis) to
        the same range model is
        trained. For example, if the model is trained with [-1, 1] input. To
        analyze an RGB image (input range [0, 255]), one needs to specify the
        input normalizer as (128.0, 128.0).
      compute_graph: string, converted model proto
    """
    self.name = name
    self.input_shape = input_shape
    self.input_normalizer = input_normalizer
    self.compute_graph = compute_graph


class InferenceException(Exception):

  def __init__(self, *args, **kwargs):
    Exception.__init__(self, *args, **kwargs)


class InferenceEngine(object):
  """Class to access InferenceEngine on VisionBonnet board.

  Inference result has the following format:

  message InferenceResult {
    string model_name;  // Name of the model to run inference on.
    int32 width;        // Input image/frame width.
    int32 height;       // Input image/frame height.
    Rectangle window;   // Window inside width x height image/frame.
    int32 duration_ms;  // Inference duration.
    map<string, FloatTensor> tensors;  // Output tensors.

    message Frame {
      int32 index;        // Frame number.
      int64 timestamp_us; // Frame timestamp.
    }

    Frame frame;          // Frame-specific inference data.
  }
  """

  def __init__(self):
    self._transport = make_transport()
    logging.info('InferenceEngine transport: %s',
                 self._transport.__class__.__name__)

  def close(self):
    self._transport.close()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, exc_tb):
    self.close()

  def _communicate(self, request, debug=False):
    """Gets response and logs messages if need to.

    Args:
      request: protocol_pb2.Request
      debug: boolean, if True and response contains inference result, print up
        to the first 10 elements of each returned vector.

    Returns:
      protocol_pb2.Response
    """
    response = protocol_pb2.Response()
    response.ParseFromString(self._transport.send(request.SerializeToString()))
    if response.status.code != protocol_pb2.Response.Status.OK:
      raise InferenceException(response.status.message)

    if debug:
      # Print up to the first 10 elements of each returned vector.
      for name, tensor in response.result.tensors.items():
        data = tensor.data[0:10]
        logging.info('First %d elements of output tensor:', len(data))
        for index, value in enumerate(data):
          logging.info('  %s[%d] = %f', name, index, value)

    return response

  def load_model(self, descriptor):
    """Loads model on VisionBonnet.

    Args:
      descriptor: ModelDescriptor, meta info that defines model name,
        where to get the model and etc.
    Returns:
      Model identifier.
    """
    logging.info('Loading model "%s"...', descriptor.name)

    batch, height, width, depth = descriptor.input_shape
    assert batch == 1, 'Only batch == 1 is currently supported'
    assert depth == 3, 'Only depth == 3 is currently supported'
    mean, stddev = descriptor.input_normalizer

    request = protocol_pb2.Request()
    request.load_model.model_name = descriptor.name
    request.load_model.input_shape.batch = batch
    request.load_model.input_shape.height = height
    request.load_model.input_shape.width = width
    request.load_model.input_shape.depth = depth
    request.load_model.input_normalizer.mean = mean
    request.load_model.input_normalizer.stddev = stddev
    if descriptor.compute_graph:
      request.load_model.compute_graph = descriptor.compute_graph

    try:
      self._communicate(request)
    except InferenceException as e:
      logging.warning(str(e))

    return descriptor.name

  def unload_model(self, model_name):
    """Deletes model on VisionBonnet.

    Args:
      model_name: string, unique identifier used to refer a model.
    """
    logging.info('Unloading model "%s"...', model_name)

    request = protocol_pb2.Request()
    request.unload_model.model_name = model_name
    self._communicate(request)

  def start_camera_inference(self, model_name, params=None):
    """Starts inference running on VisionBonnet."""
    request = protocol_pb2.Request()
    request.start_camera_inference.model_name = model_name

    for key, value in (params or {}).items():
      request.start_camera_inference.params[key] = str(value)

    self._communicate(request)

  def camera_inference(self):
    """Returns the latest inference result from VisionBonnet."""
    request = protocol_pb2.Request()
    request.camera_inference.SetInParent()
    return self._communicate(request).inference_result

  def stop_camera_inference(self):
    """Stops inference running on VisionBonnet."""
    request = protocol_pb2.Request()
    request.stop_camera_inference.SetInParent()
    self._communicate(request)

  def get_camera_state(self):
    request = protocol_pb2.Request()
    request.get_camera_state.SetInParent()
    return self._communicate(request).camera_state

  def image_inference(self, model_name, image, params=None):
    """Runs inference on image using model (identified by model_name).

    Args:
      model_name: string, unique identifier used to refer a model.
      image: PIL.Image,
      params: dict, additional parameters to run inference

    Returns:
      protocol_pb2.Response
    """

    assert model_name, 'model_name must not be empty'

    logging.info('Image inference with model "%s"...', model_name)

    width, height = image.size

    request = protocol_pb2.Request()
    request.image_inference.model_name = model_name
    request.image_inference.tensor.shape.height = height
    request.image_inference.tensor.shape.width = width

    if image.mode == 'RGB':
      r, g, b = image.split()
      request.image_inference.tensor.shape.depth = 3
      request.image_inference.tensor.data = _tobytes(r) + _tobytes(
          g) + _tobytes(b)
    elif image.mode == 'L':
      request.image_inference.tensor.shape.depth = 1
      request.image_inference.tensor.data = _tobytes(image)
    else:
      assert False, 'Only RGB and L modes are supported.'

    for key, value in (params or {}).items():
      request.image_inference.params[key] = str(value)

    return self._communicate(request).inference_result
