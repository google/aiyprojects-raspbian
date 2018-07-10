import os
import signal
import subprocess
import sys
import time
import unittest

from .test_util import test_image_path

ENV = {
    'PYTHONUNBUFFERED': '1',
    'PYTHONPATH': os.path.join(os.path.dirname(__file__), '..'),
    'VISION_BONNET_SPICOMM': 'sync_mmap'
}

def example_path(name):
    p = os.path.join(os.path.dirname(__file__), '..', 'examples', 'vision', name)
    return os.path.abspath(p)

def wait_terminated(process, timeout):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        code = process.poll()
        if code is not None:
            return code
    return None

class VisionExamplesTest(unittest.TestCase):

    def execute(self, cmdline, timeout):
        file, *rest = cmdline.split()
        cmd = [sys.executable, example_path(file)] + rest
        print(cmd)
        process = subprocess.Popen(cmd, shell=False, env=ENV)
        code = wait_terminated(process, timeout)
        if code is not None:
            self.assertEqual(0, code)
            return

        print('Interrupting process (Control-C)')
        os.kill(process.pid, signal.SIGINT)
        if wait_terminated(process, timeout=5.0) is None:
            print('Terminating process')
            os.kill(process.pid, signal.SIGTERM)
            if wait_terminated(process, timeout=5.0) is None:
                print('Killing process')
                os.kill(process.pid, signal.SIGKILL)

        process.wait()
        self.fail('Process did not finish in time: %s' % timeout)

    def test_face_detection_camera(self):
       self.execute('face_detection_camera.py --num_frames 100', timeout=45.0)

    def test_face_detection_raspivid(self):
        self.execute('face_detection_raspivid.py --num_frames 100', timeout=45.0)

    def test_image_classification_camera(self):
        self.execute('image_classification_camera.py --num_frames 100', timeout=45.0)

    def test_face_detection(self):
        image = test_image_path('faces.jpg')
        self.execute('face_detection.py --input %s' % image, timeout=45.0)

    def test_object_detection(self):
        image = test_image_path('cat.jpg')
        self.execute('object_detection.py --input %s' % image, timeout=45.0)

    def test_image_classification_mobilenet(self):
        image = test_image_path('dog.jpg')
        self.execute('image_classification.py --input %s' % image, timeout=45.0)

    def test_image_classification_mobilenet_squeezenet(self):
        image = test_image_path('dog.jpg')
        self.execute('image_classification.py --use_squeezenet --input %s' % image, timeout=45.0)


if __name__ == '__main__':
    unittest.main()
