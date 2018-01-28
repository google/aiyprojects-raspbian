#!/usr/bin/env python3
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
"""Joy detection demo."""
import argparse
import collections
import math
import os
import queue
import signal
import sys
import threading
import time

from aiy._drivers._hat import get_aiy_device_name
from aiy.toneplayer import TonePlayer
from aiy.vision.inference import CameraInference
from aiy.vision.leds import Leds
from aiy.vision.leds import PrivacyLed
from aiy.vision.models import face_detection

from gpiozero import Button
from picamera import PiCamera

JOY_COLOR = (255, 70, 0)
SAD_COLOR = (0, 0, 64)

JOY_SCORE_PEAK = 0.85
JOY_SCORE_MIN = 0.1

JOY_SOUND = ['C5q', 'E5q', 'C6q']
SAD_SOUND = ['C6q', 'E5q', 'C5q']
MODEL_LOAD_SOUND = ['C6w', 'c6w', 'C6w']

WINDOW_SIZE = 10


def blend(color_a, color_b, alpha):
    return tuple([math.ceil(alpha * color_a[i] + (1.0 - alpha) * color_b[i]) for i in range(3)])


def average_joy_score(faces):
    if faces:
        return sum([face.joy_score for face in faces]) / len(faces)
    return 0.0


class AtomicValue(object):
    def __init__(self, value):
        self._lock = threading.Lock()
        self._value = value

    @property
    def value(self):
        with self._lock:
            return self._value

    @value.setter
    def value(self, value):
        with self._lock:
            self._value = value

class MovingAverage(object):

    def __init__(self, size):
        self._window = collections.deque(maxlen=size)

    def add(self, value):
        self._window.append(value)

    @property
    def value(self):
        return sum(self._window) / len(self._window)


class JoyDetector(object):

    def __init__(self, num_frames, preview_alpha):
        self._leds = Leds()
        self._num_frames = num_frames
        self._preview_alpha = preview_alpha
        self._toneplayer = TonePlayer(22, bpm=10)
        self._detector = threading.Thread(target=self._run_detector)
        self._animator = threading.Thread(target=self._run_animator)
        self._photographer = threading.Thread(target=self._run_photographer)
        self._requests = queue.Queue()
        self._joy_score = AtomicValue(0.0)
        self._run_event = threading.Event()
        signal.signal(signal.SIGINT, lambda signal, frame: self.stop())
        signal.signal(signal.SIGTERM, lambda signal, frame: self.stop())

    def start(self):
        print('Starting JoyDetector...')
        self._run_event.set()
        self._animator.start()
        self._detector.start()
        self._photographer.start()

    def join(self):
        self._detector.join()
        self._animator.join()
        self._photographer.join()

    def stop(self):
        print('Stopping JoyDetector...')
        self._run_event.clear()
        self._requests.put(None)

    def _play_sound(self, sound):
        threading.Thread(target=self._toneplayer.play, args=(*sound,)).start()


    def _run_animator(self):
        prev_joy_score = -1.0
        while self._run_event.is_set():
            joy_score = self._joy_score.value

            if joy_score > JOY_SCORE_PEAK > prev_joy_score:
                self._play_sound(JOY_SOUND)
            elif joy_score < JOY_SCORE_MIN < prev_joy_score:
                self._play_sound(SAD_SOUND)

            if joy_score > 0:
                self._leds.update(Leds.rgb_on(blend(JOY_COLOR, SAD_COLOR, joy_score)))
            else:
                self._leds.update(Leds.rgb_off())

            prev_joy_score = joy_score

    def _run_photographer(self):
        while True:
            request = self._requests.get()
            if request is None:
                break

            camera, faces = request
            filename = os.path.expanduser(
                '~/Pictures/photo_%s.jpg' % time.strftime('%Y-%m-%d@%H.%M.%S'))
            print(filename)
            camera.capture(filename, use_video_port=True)
            # TODO(dkovalev): Generate and save overlay image with faces.
            self._requests.task_done()


    def _run_detector(self):
        with PiCamera() as camera, PrivacyLed(self._leds):
            detected_faces = AtomicValue([])

            def take_photo():
                self._requests.put((camera, detected_faces.value))

            # Forced sensor mode, 1640x1232, full FoV. See:
            # https://picamera.readthedocs.io/en/release-1.13/fov.html#sensor-modes
            # This is the resolution inference run on.
            camera.sensor_mode = 4
            camera.resolution = (1640, 1232)
            camera.framerate = 15
            # Blend the preview layer with the alpha value from the flags.
            camera.start_preview(alpha=self._preview_alpha)

            button = Button(23)
            button.when_pressed = take_photo

            joy_score_moving_average = MovingAverage(WINDOW_SIZE)
            with CameraInference(face_detection.model()) as inference:
                self._play_sound(MODEL_LOAD_SOUND)
                for i, result in enumerate(inference.run()):
                    faces = face_detection.get_faces(result)
                    detected_faces.value = faces
                    joy_score_moving_average.add(average_joy_score(faces))
                    self._joy_score.value = joy_score_moving_average.value
                    if self._num_frames == i or not self._run_event.is_set():
                        break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--num_frames',
        '-n',
        type=int,
        dest='num_frames',
        default=-1,
        help='Sets the number of frames to run for. '
        'Setting this parameter to -1 will '
        'cause the demo to not automatically terminate.')
    parser.add_argument(
        '--preview_alpha',
        '-pa',
        type=int,
        dest='preview_alpha',
        default=0,
        help='Sets the transparency value of the preview overlay (0-255).')
    args = parser.parse_args()

    device = get_aiy_device_name()
    if not device or not 'Vision' in device:
        print('Do you have an AIY Vision bonnet installed? Exiting.')
        sys.exit(0)

    detector = JoyDetector(args.num_frames, args.preview_alpha)
    detector.start()
    detector.join()


if __name__ == '__main__':
    main()
