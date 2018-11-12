import unittest

from picamera import PiCamera

from aiy.vision.inference import InferenceEngine, InferenceException, \
                                 ImageInference, CameraInference
from aiy.vision.models import face_detection as fd

from .test_util import TestImage, TestImageFile

class InferenceEngineTest(unittest.TestCase):
    def setUp(self):
        with InferenceEngine() as engine:
            engine.reset()

    def test_firmware_info(self):
        with InferenceEngine() as engine:
            for _ in range(50):
                info = engine.get_firmware_info()
                self.assertTrue(hasattr(info, 'major'))
                self.assertTrue(hasattr(info, 'minor'))

    def test_system_info(self):
        with InferenceEngine() as engine:
            for _ in range(50):
                info = engine.get_system_info()
                self.assertTrue(hasattr(info, 'uptime_seconds'))
                self.assertTrue(hasattr(info, 'temperature_celsius'))

    def test_load_unload(self):
        with InferenceEngine() as engine:
            state = engine.get_inference_state()
            self.assertFalse(state.loaded_models)
            self.assertFalse(state.processing_models)

            model_name = engine.load_model(fd.model())
            state = engine.get_inference_state()
            self.assertEqual(set(state.loaded_models), {model_name})
            self.assertFalse(state.processing_models)

            with self.assertRaises(InferenceException):
                engine.unload_model('invalid_model_name')

            engine.unload_model(model_name)
            state = engine.get_inference_state()
            self.assertFalse(state.loaded_models)
            self.assertFalse(state.processing_models)

    def test_inference_state(self):
        with InferenceEngine() as engine:
            state = engine.get_inference_state()
            self.assertFalse(state.loaded_models)
            self.assertFalse(state.processing_models)

            model_name = engine.load_model(fd.model())
            state = engine.get_inference_state()
            self.assertEqual(set(state.loaded_models), {model_name})
            self.assertFalse(state.processing_models)

            engine.reset()
            state = engine.get_inference_state()
            self.assertFalse(state.loaded_models)
            self.assertFalse(state.processing_models)

            model_name = engine.load_model(fd.model())

            with PiCamera(sensor_mode=4):
                engine.start_camera_inference(model_name)
                state = engine.get_inference_state()
                self.assertEqual(set(state.loaded_models), {model_name})
                self.assertEqual(set(state.processing_models), {model_name})

                engine.reset()
                state = engine.get_inference_state()
                self.assertFalse(state.loaded_models)
                self.assertFalse(state.processing_models)

    def test_camera_state(self):
        MODES = {1: (1920, 1080),
                 2: (3280, 2464),
                 3: (3280, 2464),
                 4: (1640, 1232),
                 5: (1640, 922),
                 6: (1280, 720),
                 7: (640, 480)}
        with InferenceEngine() as engine:
            for mode, (width, height) in MODES.items():
                state = engine.get_camera_state()
                self.assertFalse(state.running)

                with PiCamera(sensor_mode=mode):
                    state = engine.get_camera_state()
                    self.assertTrue(state.running)
                    self.assertEqual(state.width, width)
                    self.assertEqual(state.height, height)
                    info = engine.get_system_info()

            state = engine.get_camera_state()
            self.assertFalse(state.running)

    def test_image_inference_raw(self):
        with ImageInference(fd.model()) as inference, TestImage('faces.jpg') as image:
            fd.get_faces(inference.run(image))

    def test_image_inference_jpeg(self):
        with ImageInference(fd.model()) as inference, TestImageFile('faces.jpg') as f:
            fd.get_faces(inference.run(f.read()))

    def test_camera_inference(self):
        with PiCamera(sensor_mode=4):
            with CameraInference(fd.model()) as inference:
                state = inference.engine.get_inference_state()
                self.assertEqual(len(state.loaded_models), 1)
                self.assertEqual(len(state.processing_models), 1)

                results = [fd.get_faces(result) for result in inference.run(10)]
                self.assertEqual(len(results), 10)

if __name__ == '__main__':
    unittest.main()
