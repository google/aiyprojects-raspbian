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
import contextlib
import io
import logging
import math
import os
import queue
import signal
import sys
import threading
import time

from PIL import Image, ImageDraw, ImageFont
from picamera import PiCamera

from aiy.board import Board
from aiy.leds import Color, Leds, Pattern, PrivacyLed
from aiy.toneplayer import TonePlayer
from aiy.vision.inference import CameraInference
from aiy.vision.models import face_detection
from aiy.vision.streaming.server import StreamingServer
from aiy.vision.streaming import svg

logger = logging.getLogger(__name__)

JOY_COLOR = (255, 70, 0)
SAD_COLOR = (0, 0, 64)

JOY_SCORE_HIGH = 0.85
JOY_SCORE_LOW = 0.10

JOY_SOUND = ('C5q', 'E5q', 'C6q')
SAD_SOUND = ('C6q', 'E5q', 'C5q')
MODEL_LOAD_SOUND = ('C6w', 'c6w', 'C6w')
BEEP_SOUND = ('E6q', 'C6q')

FONT_FILE = '/usr/share/fonts/truetype/freefont/FreeSans.ttf'

BUZZER_GPIO = 22

@contextlib.contextmanager
def stopwatch(message):
    try:
        logger.info('%s...', message)
        begin = time.monotonic()
        yield
    finally:
        end = time.monotonic()
        logger.info('%s done. (%fs)', message, end - begin)


def run_inference(num_frames, on_loaded):
    """Yields (faces, (frame_width, frame_height)) tuples."""
    with CameraInference(face_detection.model()) as inference:
        on_loaded()
        for result in inference.run(num_frames):
            yield face_detection.get_faces(result), (result.width, result.height)


def threshold_detector(low_threshold, high_threshold):
    """Yields 'low', 'high', and None events."""
    assert low_threshold < high_threshold

    event = None
    prev_score = 0.0
    while True:
        score = (yield event)
        if score > high_threshold > prev_score:
            event = 'high'
        elif score < low_threshold < prev_score:
            event = 'low'
        else:
            event = None
        prev_score = score


def moving_average(size):
    window = collections.deque(maxlen=size)
    window.append((yield 0.0))
    while True:
        window.append((yield sum(window) / len(window)))


def average_joy_score(faces):
    if faces:
        return sum(face.joy_score for face in faces) / len(faces)
    return 0.0


def draw_rectangle(draw, x0, y0, x1, y1, border, fill=None, outline=None):
    assert border % 2 == 1
    for i in range(-border // 2, border // 2 + 1):
        draw.rectangle((x0 + i, y0 + i, x1 - i, y1 - i), fill=fill, outline=outline)


def scale_bounding_box(bounding_box, scale_x, scale_y):
    x, y, w, h = bounding_box
    return (x * scale_x, y * scale_y, w * scale_x, h * scale_y)


def svg_overlay(faces, frame_size, joy_score):
    width, height = frame_size
    doc = svg.Svg(width=width, height=height)

    for face in faces:
        x, y, w, h = face.bounding_box
        doc.add(svg.Rect(x=int(x), y=int(y), width=int(w), height=int(h), rx=10, ry=10,
                         fill_opacity=0.3 * face.face_score,
                         style='fill:red;stroke:white;stroke-width:4px'))

        doc.add(svg.Text('Joy: %.2f' % face.joy_score, x=x, y=y - 10,
                         fill='red', font_size=30))

    doc.add(svg.Text('Faces: %d Avg. joy: %.2f' % (len(faces), joy_score),
            x=10, y=50, fill='red', font_size=40))
    return str(doc)


class Service:

    def __init__(self):
        self._requests = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            request = self._requests.get()
            if request is None:
                self.shutdown()
                break
            self.process(request)
            self._requests.task_done()

    def process(self, request):
        pass

    def shutdown(self):
        pass

    def submit(self, request):
        self._requests.put(request)

    def close(self):
        self._requests.put(None)
        self._thread.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


class Player(Service):
    """Controls buzzer."""

    def __init__(self, gpio, bpm):
        super().__init__()
        self._toneplayer = TonePlayer(gpio, bpm)

    def process(self, sound):
        self._toneplayer.play(*sound)

    def play(self, sound):
        self.submit(sound)


class Photographer(Service):
    """Saves photographs to disk."""

    def __init__(self, format, folder):
        super().__init__()
        assert format in ('jpeg', 'bmp', 'png')

        self._font = ImageFont.truetype(FONT_FILE, size=25)
        self._faces = ([], (0, 0))
        self._format = format
        self._folder = folder

    def _make_filename(self, timestamp, annotated):
        path = '%s/%s_annotated.%s' if annotated else '%s/%s.%s'
        return os.path.expanduser(path % (self._folder, timestamp, self._format))

    def _draw_face(self, draw, face, scale_x, scale_y):
        x, y, width, height = scale_bounding_box(face.bounding_box, scale_x, scale_y)
        text = 'Joy: %.2f' % face.joy_score
        _, text_height = self._font.getsize(text)
        margin = 3
        bottom = y + height
        text_bottom = bottom + margin + text_height + margin
        draw_rectangle(draw, x, y, x + width, bottom, 3, outline='white')
        draw_rectangle(draw, x, bottom, x + width, text_bottom, 3, fill='white', outline='white')
        draw.text((x + 1 + margin, y + height + 1 + margin), text, font=self._font, fill='black')

    def process(self, message):
        if isinstance(message, tuple):
            self._faces = message
            return

        camera = message
        timestamp = time.strftime('%Y-%m-%d_%H.%M.%S')

        stream = io.BytesIO()
        with stopwatch('Taking photo'):
            camera.capture(stream, format=self._format, use_video_port=True)

        filename = self._make_filename(timestamp, annotated=False)
        with stopwatch('Saving original %s' % filename):
            stream.seek(0)
            with open(filename, 'wb') as file:
                file.write(stream.read())

        faces, (width, height) = self._faces
        if faces:
            filename = self._make_filename(timestamp, annotated=True)
            with stopwatch('Saving annotated %s' % filename):
                stream.seek(0)
                image = Image.open(stream)
                draw = ImageDraw.Draw(image)
                scale_x, scale_y = image.width / width, image.height / height
                for face in faces:
                    self._draw_face(draw, face, scale_x, scale_y)
                del draw
                image.save(filename)

    def update_faces(self, faces):
        self.submit(faces)

    def shoot(self, camera):
        self.submit(camera)


class Animator(Service):
    """Controls RGB LEDs."""

    def __init__(self, leds):
        super().__init__()
        self._leds = leds

    def process(self, joy_score):
        if joy_score > 0:
            self._leds.update(Leds.rgb_on(Color.blend(JOY_COLOR, SAD_COLOR, joy_score)))
        else:
            self._leds.update(Leds.rgb_off())

    def shutdown(self):
        self._leds.update(Leds.rgb_off())

    def update_joy_score(self, joy_score):
        self.submit(joy_score)


def joy_detector(num_frames, preview_alpha, image_format, image_folder,
                 enable_streaming, streaming_bitrate, mdns_name):
    done = threading.Event()
    def stop():
        logger.info('Stopping...')
        done.set()

    signal.signal(signal.SIGINT, lambda signum, frame: stop())
    signal.signal(signal.SIGTERM, lambda signum, frame: stop())

    logger.info('Starting...')
    with contextlib.ExitStack() as stack:
        leds = stack.enter_context(Leds())
        board = stack.enter_context(Board())
        player = stack.enter_context(Player(gpio=BUZZER_GPIO, bpm=10))
        photographer = stack.enter_context(Photographer(image_format, image_folder))
        animator = stack.enter_context(Animator(leds))
        # Forced sensor mode, 1640x1232, full FoV. See:
        # https://picamera.readthedocs.io/en/release-1.13/fov.html#sensor-modes
        # This is the resolution inference run on.
        # Use half of that for video streaming (820x616).
        camera = stack.enter_context(PiCamera(sensor_mode=4, resolution=(820, 616)))
        stack.enter_context(PrivacyLed(leds))

        server = None
        if enable_streaming:
            server = stack.enter_context(StreamingServer(camera, bitrate=streaming_bitrate,
                                                         mdns_name=mdns_name))

        def model_loaded():
            logger.info('Model loaded.')
            player.play(MODEL_LOAD_SOUND)

        def take_photo():
            logger.info('Button pressed.')
            player.play(BEEP_SOUND)
            photographer.shoot(camera)

        if preview_alpha > 0:
            camera.start_preview(alpha=preview_alpha)

        board.button.when_pressed = take_photo

        joy_moving_average = moving_average(10)
        joy_moving_average.send(None)  # Initialize.
        joy_threshold_detector = threshold_detector(JOY_SCORE_LOW, JOY_SCORE_HIGH)
        joy_threshold_detector.send(None)  # Initialize.
        for faces, frame_size in run_inference(num_frames, model_loaded):
            photographer.update_faces((faces, frame_size))
            joy_score = joy_moving_average.send(average_joy_score(faces))
            animator.update_joy_score(joy_score)
            event = joy_threshold_detector.send(joy_score)
            if event == 'high':
                logger.info('High joy detected.')
                player.play(JOY_SOUND)
            elif event == 'low':
                logger.info('Low joy detected.')
                player.play(SAD_SOUND)

            if server:
                server.send_overlay(svg_overlay(faces, frame_size, joy_score))

            if done.is_set():
                break

def preview_alpha(string):
    value = int(string)
    if value < 0 or value > 255:
        raise argparse.ArgumentTypeError('Must be in [0...255] range.')
    return value


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--num_frames', '-n', type=int, default=None,
                        help='Number of frames to run for')
    parser.add_argument('--preview_alpha', '-pa', type=preview_alpha, default=0,
                        help='Video preview overlay transparency (0-255)')
    parser.add_argument('--image_format', default='jpeg',
                        choices=('jpeg', 'bmp', 'png'),
                        help='Format of captured images')
    parser.add_argument('--image_folder', default='~/Pictures',
                        help='Folder to save captured images')
    parser.add_argument('--blink_on_error', default=False, action='store_true',
                        help='Blink red if error occurred')
    parser.add_argument('--enable_streaming', default=False, action='store_true',
                        help='Enable streaming server')
    parser.add_argument('--streaming_bitrate', type=int, default=1000000,
                        help='Streaming server video bitrate (kbps)')
    parser.add_argument('--mdns_name', default='',
                        help='Streaming server mDNS name')
    args = parser.parse_args()

    try:
        joy_detector(args.num_frames, args.preview_alpha, args.image_format, args.image_folder,
                     args.enable_streaming, args.streaming_bitrate, args.mdns_name)
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception('Exception while running joy demo.')
        if args.blink_on_error:
            with Leds() as leds:
                leds.pattern = Pattern.blink(100)  # 10 Hz
                leds.update(Leds.rgb_pattern(Color.RED))
                time.sleep(1.0)

    return 0

if __name__ == '__main__':
    sys.exit(main())
