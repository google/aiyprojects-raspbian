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

import contextlib
import itertools
import logging
import time
from collections import namedtuple

import aiy.vision.proto.protocol_pb2 as pb2
from aiy._drivers._transport import make_transport

logger = logging.getLogger(__name__)

# name: string, a unique identifier to refer a model.
# input_shape: (batch, height, width, depth). Only batch=1 and depth=3 are supported now.
# input_normalizer: (mean, stddev) to convert input image  to the same range as model was
#     trained with. For example, if the model is trained with [-1, 1] input. To analyze an RGB image
#     (input range 0-255), one needs to specify the input normalizer as (128.0, 128.0).
# compute_graph: bytes, serialized model protobuf.
ModelDescriptor = namedtuple('ModelDescriptor',
    ('name', 'input_shape', 'input_normalizer', 'compute_graph'))

ThresholdingConfig = namedtuple('ThresholdingConfig',
    ('logical_shape', 'threshold', 'top_k', 'to_ignore'))

FromSparseTensorConfig = namedtuple('FromSparseTensorConfig',
    ('logical_shape', 'tensor_name', 'squeeze_dims'))

# major: int, major firmware version
# minor: int, minor firmware version
FirmwareVersion = namedtuple('FirmwareVersion', ('major', 'minor'))
FirmwareVersion.__str__ = lambda self: '%d.%d' % (self.major, self.minor)


_SUPPORTED_FIRMWARE_VERSION = FirmwareVersion(1, 2)


class FirmwareVersionException(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def _check_firmware_info(version):
    if version[0] > _SUPPORTED_FIRMWARE_VERSION[0]:
        raise FirmwareVersionException(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. You should upgrade AIY library.' %
            (_SUPPORTED_FIRMWARE_VERSION, version))
    if version[0] < _SUPPORTED_FIRMWARE_VERSION[0]:
        raise FirmwareVersionException(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. You should upgrade firmware.' %
            (_SUPPORTED_FIRMWARE_VERSION, version))
    if version[1] > _SUPPORTED_FIRMWARE_VERSION[1]:
        logger.warning(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. Consider upgrading AIY library.',
            _SUPPORTED_FIRMWARE_VERSION, version)
    if version[1] < _SUPPORTED_FIRMWARE_VERSION[1]:
        logger.warning(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. Consider upgrading firmware.',
            _SUPPORTED_FIRMWARE_VERSION, version)

def _close_stack_silently(stack):
    try:
        stack.close()
    except Exception:
        pass

class CameraInference:
    """Helper class to run camera inference."""

    def __init__(self, descriptor, params=None, sparse_configs=None):
        self._rate = 0.0
        self._count = 0
        self._stack = contextlib.ExitStack()
        self._engine = self._stack.enter_context(InferenceEngine())

        try:
            model_name = descriptor.name
            if model_name not in self._engine.get_inference_state().loaded_models:
                self._engine.load_model(descriptor)
                self._stack.callback(lambda: self._engine.unload_model(model_name))

            self._engine.start_camera_inference(model_name, params, sparse_configs)
            self._stack.callback(lambda: self._engine.stop_camera_inference())
        except Exception:
            _close_stack_silently(self._stack)
            raise

    def run(self, count=None):
        before = None
        for _ in (itertools.count() if count is None else range(count)):
            result = self._engine.camera_inference()
            now = time.monotonic()
            self._rate = 1.0 / (now - before) if before else 0.0
            before = now
            self._count += 1
            yield result

    @property
    def engine(self):
        return self._engine

    @property
    def rate(self):
        return self._rate

    @property
    def count(self):
        return self._count

    def close(self):
        self._stack.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


class ImageInference:
    """Helper class to run image inference."""

    def __init__(self, descriptor):
        self._stack = contextlib.ExitStack()
        self._engine = self._stack.enter_context(InferenceEngine())

        try:
            self._model_name = descriptor.name
            if self._model_name not in self._engine.get_inference_state().loaded_models:
                self._model_name = self._engine.load_model(descriptor)
                self._stack.callback(lambda: self._engine.unload_model(self._model_name))
        except Exception:
            _close_stack_silently(self._stack)
            raise

    def run(self, image, params=None, sparse_configs=None):
        return self._engine.image_inference(self._model_name, image, params, sparse_configs)

    @property
    def engine(self):
        return self._engine

    def close(self):
        self._stack.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


class InferenceException(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

def _get_sparse_config(config):
    if isinstance(config, ThresholdingConfig):
        return pb2.SparseConfig(
            logical_shape=pb2.Tuple(values=config.logical_shape),
            thresholding=pb2.SparseConfig.Thresholding(
                threshold=config.threshold,
                top_k=config.top_k,
                to_ignore=[pb2.SparseConfig.Thresholding.ToIgnore(dim=d, label=l) for d, l in config.to_ignore]))

    if isinstance(config, FromSparseTensorConfig):
        return pb2.SparseConfig(
            logical_shape=pb2.Tuple(values=config.logical_shape),
            from_sparse_tensor=pb2.SparseConfig.FromSparseTensor(
                tensor_name=config.tensor_name,
                squeeze_dims=config.squeeze_dims))

    raise ValueError('Invalid sparse config type.')

def _get_sparse_configs(configs):
    if configs:
        return {name: _get_sparse_config(config) for name, config in configs.items()}
    return None


def _image_to_tensor(image):
    if isinstance(image, (bytes, bytearray)):
        # Only JPEG is supported on the bonnet side.
        return pb2.ByteTensor(
            shape=pb2.TensorShape(batch=1, height=0, width=0, depth=0),
            data=image)

    width, height = image.size
    if image.mode == 'RGB':
        r, g, b = image.split()
        return pb2.ByteTensor(
            shape=pb2.TensorShape(batch=1, height=height, width=width, depth=3),
            data=r.tobytes() + g.tobytes() + b.tobytes())

    if image.mode == 'L':
        return pb2.ByteTensor(
            shape=pb2.TensorShape(batch=1, height=height, width=width, depth=1),
            data=image.tobytes())

    raise InferenceException('Unsupported image format: %s. Must be L or RGB.' % image.mode)


def _get_params(params):
    return {key: str(value) for key, value in (params or {}).items()}


def _check_model_name(model_name):
    if not model_name:
        raise ValueError('Model name must not be empty.')


def _request_bytes(*args, **kwargs):
    return pb2.Request(*args, **kwargs).SerializeToString()


_REQ_GET_FIRMWARE_INFO = _request_bytes(get_firmware_info=pb2.Request.GetFirmwareInfo())
_REQ_GET_SYSTEM_INFO = _request_bytes(get_system_info=pb2.Request.GetSystemInfo())
_REQ_CAMERA_INFERENCE = _request_bytes(camera_inference=pb2.Request.CameraInference())
_REQ_STOP_CAMERA_INFERENCE = _request_bytes(stop_camera_inference=pb2.Request.StopCameraInference())
_REQ_GET_INFERENCE_STATE = _request_bytes(get_inference_state=pb2.Request.GetInferenceState())
_REQ_GET_CAMERA_STATE = _request_bytes(get_camera_state=pb2.Request.GetCameraState())
_REQ_RESET = _request_bytes(reset=pb2.Request.Reset())

class InferenceEngine:
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
        logger.info('InferenceEngine transport: %s', self._transport.__class__.__name__)

    def close(self):
        self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _communicate(self, request, timeout=None):
        return self._communicate_bytes(request.SerializeToString(), timeout=timeout)

    def _communicate_bytes(self, request_bytes, timeout=None):
        response = pb2.Response()
        response.ParseFromString(self._transport.send(request_bytes, timeout=timeout))
        if response.status.code != pb2.Response.Status.OK:
            raise InferenceException(response.status.message)
        return response

    def load_model(self, descriptor):
        """Loads model on VisionBonnet.

        Args:
          descriptor: ModelDescriptor, meta info that defines model name,
            where to get the model and etc.
        Returns:
          Model identifier.
        """
        _check_firmware_info(self.get_firmware_info())
        mean, stddev = descriptor.input_normalizer
        batch, height, width, depth = descriptor.input_shape
        if batch != 1:
            raise ValueError('Unsupported batch value: %d. Must be 1.')

        if depth != 3:
            raise ValueError('Unsupported depth value: %d. Must be 3.')

        try:
            logger.info('Load model "%s".', descriptor.name)
            self._communicate(pb2.Request(
                load_model=pb2.Request.LoadModel(
                    model_name=descriptor.name,
                    input_shape=pb2.TensorShape(
                        batch=batch,
                        height=height,
                        width=width,
                        depth=depth),
                    input_normalizer=pb2.TensorNormalizer(
                        mean=mean,
                        stddev=stddev),
                    compute_graph=descriptor.compute_graph)))
        except InferenceException as e:
            logger.warning(str(e))

        return descriptor.name

    def unload_model(self, model_name):
        """Deletes model on VisionBonnet.

        Args:
          model_name: string, unique identifier used to refer a model.
        """
        _check_model_name(model_name)

        logger.info('Unload model "%s".', model_name)
        self._communicate(pb2.Request(
            unload_model=pb2.Request.UnloadModel(model_name=model_name)))

    def start_camera_inference(self, model_name, params=None, sparse_configs=None):
        """Starts inference running on VisionBonnet."""
        _check_model_name(model_name)

        logger.info('Start camera inference on "%s".', model_name)
        self._communicate(pb2.Request(
            start_camera_inference=pb2.Request.StartCameraInference(
                model_name=model_name,
                params=_get_params(params),
                sparse_configs=_get_sparse_configs(sparse_configs))))

    def camera_inference(self):
        """Returns the latest inference result from VisionBonnet."""
        return self._communicate_bytes(_REQ_CAMERA_INFERENCE).inference_result

    def stop_camera_inference(self):
        """Stops inference running on VisionBonnet."""
        logger.info('Stop camera inference.')
        self._communicate_bytes(_REQ_STOP_CAMERA_INFERENCE)

    def get_inference_state(self):
        """Returns inference state."""
        return self._communicate_bytes(_REQ_GET_INFERENCE_STATE).inference_state

    def get_camera_state(self):
        """Returns current camera state."""
        return self._communicate_bytes(_REQ_GET_CAMERA_STATE).camera_state

    def get_firmware_info(self):
        """Returns firmware version as (major, minor) tuple."""
        try:
            info = self._communicate_bytes(_REQ_GET_FIRMWARE_INFO).firmware_info
            return FirmwareVersion(info.major_version, info.minor_version)
        except InferenceException:
            return FirmwareVersion(1, 0)  # Request is not supported by firmware, default to 1.0

    def get_system_info(self):
        """Returns system information: uptime, memory usage, temperature."""
        return self._communicate_bytes(_REQ_GET_SYSTEM_INFO).system_info

    def image_inference(self, model_name, image, params=None, sparse_configs=None):
        """Runs inference on image using model identified by model_name.

        Args:
          model_name: string, unique identifier used to refer a model.
          image: PIL.Image,
          params: dict, additional parameters to run inference

        Returns:
          pb2.Response.InferenceResult
        """
        _check_model_name(model_name)

        logger.info('Image inference on "%s".', model_name)
        return self._communicate(pb2.Request(
            image_inference=pb2.Request.ImageInference(
                model_name=model_name,
                tensor=_image_to_tensor(image),
                params=_get_params(params),
                sparse_configs=_get_sparse_configs(sparse_configs)))).inference_result

    def reset(self):
        self._communicate_bytes(_REQ_RESET)
