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
import aiy.vision.proto.protocol_pb2 as pb2
from aiy._drivers._transport import make_transport

logger = logging.getLogger(__name__)

_SUPPORTED_FIRMWARE_VERSION = (1, 1)  # major, minor


class FirmwareVersionException(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def _check_firmware_info(info):
    firmware_version = '%d.%d' % info
    supported_version = '%d.%d' % _SUPPORTED_FIRMWARE_VERSION
    if info[0] > _SUPPORTED_FIRMWARE_VERSION[0]:
        raise FirmwareVersionException(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. You should upgrade AIY library.' %
            (supported_version, firmware_version))
    if info[0] < _SUPPORTED_FIRMWARE_VERSION[0]:
        raise FirmwareVersionException(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. You should upgrade firmware.' %
            (supported_version, firmware_version))
    if info[1] > _SUPPORTED_FIRMWARE_VERSION[1]:
        logger.warning(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. Consider upgrading AIY library.',
            supported_version, firmware_version)
    if info[1] < _SUPPORTED_FIRMWARE_VERSION[1]:
        logger.warning(
            'AIY library supports firmware version %s, current firmware '
            'version is %s. Consider upgrading firmware.',
            supported_version, firmware_version)


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
        self._engine.close()

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
        self._engine.close()

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


def _image_to_tensor(image):
    width, height = image.size
    if image.mode == 'RGB':
        r, g, b = image.split()
        return pb2.ByteTensor(
            shape=pb2.TensorShape(batch=1, height=height, width=width, depth=3),
            data=r.tobytes() + g.tobytes() + b.tobytes())
    elif image.mode == 'L':
        return pb2.ByteTensor(
            shape=pb2.TensorShape(batch=1, height=height, width=width, depth=1),
            data=image.tobytes())
    else:
        raise InferenceException('Unsupported image format: %s. Must be L or RGB.' % image.mode)


def _get_params(params):
    return {key: str(value) for key, value in (params or {}).items()}


def _check_model_name(model_name):
    if not model_name:
        raise ValueError('Model name must not be empty.')


def _request_bytes(*args, **kwargs):
    return pb2.Request(*args, **kwargs).SerializeToString()


_REQ_GET_FIRMWARE_INFO = _request_bytes(get_firmware_info=pb2.Request.GetFirmwareInfo())
_REQ_CAMERA_INFERENCE = _request_bytes(camera_inference=pb2.Request.CameraInference())
_REQ_STOP_CAMERA_INFERENCE = _request_bytes(stop_camera_inference=pb2.Request.StopCameraInference())
_REQ_GET_CAMERA_STATE = _request_bytes(get_camera_state=pb2.Request.GetCameraState())


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
        logger.info('InferenceEngine transport: %s', self._transport.__class__.__name__)

    def close(self):
        self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _communicate(self, request):
        return self._communicate_bytes(request.SerializeToString())

    def _communicate_bytes(self, request_bytes):
        response = pb2.Response()
        response.ParseFromString(self._transport.send(request_bytes))
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

        logger.info('Loading model "%s"...', descriptor.name)

        mean, stddev = descriptor.input_normalizer
        batch, height, width, depth = descriptor.input_shape
        if batch != 1:
            raise ValueError('Unsupported batch value: %d. Must be 1.')

        if depth != 3:
            raise ValueError('Unsupported depth value: %d. Must be 3.')

        try:
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

        logger.info('Unloading model "%s"...', model_name)
        self._communicate(pb2.Request(
            unload_model=pb2.Request.UnloadModel(model_name=model_name)))

    def start_camera_inference(self, model_name, params=None):
        """Starts inference running on VisionBonnet."""
        _check_model_name(model_name)

        self._communicate(pb2.Request(
            start_camera_inference=pb2.Request.StartCameraInference(
                model_name=model_name,
                params=_get_params(params))))

    def camera_inference(self):
        """Returns the latest inference result from VisionBonnet."""
        return self._communicate_bytes(_REQ_CAMERA_INFERENCE).inference_result

    def stop_camera_inference(self):
        """Stops inference running on VisionBonnet."""
        self._communicate_bytes(_REQ_STOP_CAMERA_INFERENCE)

    def get_camera_state(self):
        """Returns current camera state."""
        return self._communicate_bytes(_REQ_GET_CAMERA_STATE).camera_state

    def get_firmware_info(self):
        """Returns firmware version as (major, minor) tuple."""
        try:
            info = self._communicate_bytes(_REQ_GET_FIRMWARE_INFO).firmware_info
            return (info.major_version, info.minor_version)
        except InferenceException:
            return (1, 0)  # Request is not supported by firmware, default to 1.0

    def image_inference(self, model_name, image, params=None):
        """Runs inference on image using model identified by model_name.

        Args:
          model_name: string, unique identifier used to refer a model.
          image: PIL.Image,
          params: dict, additional parameters to run inference

        Returns:
          pb2.Response.InferenceResult
        """
        _check_model_name(model_name)

        logger.info('Image inference with model "%s"...', model_name)
        return self._communicate(pb2.Request(
            image_inference=pb2.Request.ImageInference(
                model_name=model_name,
                tensor=_image_to_tensor(image),
                params=_get_params(params)))).inference_result
