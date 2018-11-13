#!/usr/bin/env python3
# Copyright 2018 Google Inc.
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
"""Object detection with servo output demo."""
import argparse
import time
import picamera

from aiy.pins import PIN_A
from aiy.pins import BUTTON_GPIO_PIN
from aiy.vision.inference import CameraInference
from aiy.vision.models import image_classification
from aiy.vision.annotator import Annotator
from gpiozero import Button
from gpiozero import AngularServo
from wordnet_grouping import category_mapper


class AutoButton:
    """Button utility that handles the io and state tracking."""

    def __init__(self, start_enabled=False, use_hardware=True):
        self._use_hardware = use_hardware
        if use_hardware:
            self._button = Button(BUTTON_GPIO_PIN)
            self._enabled = start_enabled
            if not start_enabled:
                self._button.when_pressed = self._enable

    def _enable(self):
        self._enabled = True

    def on(self):
        if not self._use_hardware or not self._enabled:
            return True
        # Button is currently pressed
        return self._button.is_pressed


class OverlayManager:
    """Overlay utility for managing state and drawing of overlay."""
    LINE_HEIGHT = 12
    ROW_HEIGHT = 50

    def __init__(self, camera):
        self._clear_needed = False
        self._annotator = Annotator(camera, default_color=(0xFF, 0xFF, 0xFF, 0xFF),
                                    dimensions=(320, 240))

    def _draw_annotation(self, result, category, index):
        self._annotator.text((5,
                              index * self.ROW_HEIGHT + 5 + 0 * self.LINE_HEIGHT),
                             '{:.2%}'.format(result[1]))
        self._annotator.text((5,
                              index * self.ROW_HEIGHT + 5 + 1 * self.LINE_HEIGHT),
                             '{:25.25}'.format(result[0]))
        self._annotator.text((5,
                              index * self.ROW_HEIGHT + 5 + 2 * self.LINE_HEIGHT),
                             'category: {:20.20}'.format(category))

    def clear(self):
        if self._clear_needed:
            self._annotator.stop()
            self._clear_needed = False

    def update(self, classes, categories):
        self._annotator.clear()
        self._clear_needed = True
        for i, result in enumerate(classes):
            self._draw_annotation(result, categories[i], i)
        self._annotator.update()


class DummyOverlayManager:
    """Dummy implementation of overlay manager used when overlay is disabled."""

    def clear(self):
        pass

    def update(self, classes, categories):
        del classes, categories  # Unused


def main():
    parser = argparse.ArgumentParser(
        description='Example application for displaying a dial indicator for '
        'what object is seen')
    parser.add_argument(
        '--output_overlay',
        default=True,
        type=bool,
        help='Should the visual overlay be generated')
    parser.add_argument(
        '--button_enabled',
        default=True,
        type=bool,
        help='Should the button be monitored')
    parser.add_argument(
        '--button_active',
        default=False,
        type=bool,
        help='Should the button start out active (true) or only be active once '
        'pressed (false)')
    flags = parser.parse_args()
    load_model = time.time()
    category_count = len(category_mapper.get_categories())
    button = AutoButton(flags.button_active, flags.button_enabled)

    for category in category_mapper.get_categories():
        print('Category[%d]: %s' % (category_mapper.get_category_index(category),
                                    category))
    with picamera.PiCamera() as camera:
        camera.resolution = (1640, 1232)
        camera.start_preview()
        overlay = OverlayManager(
            camera) if flags.output_overlay else DummyOverlayManager()
        servo = AngularServo(PIN_A, min_pulse_width=.0005, max_pulse_width=.0019)
        with CameraInference(image_classification.model()) as classifier:
            print('Load Model %f' % (time.time() - load_model))
            for result in classifier.run():
                if not button.on():
                    overlay.clear()
                    servo.angle = -90
                    continue

                classes = image_classification.get_classes(result)

                probs = [0] * (category_count + 1)
                result_categories = []
                for label, score in classes:
                    category = category_mapper.get_category(label) or 'Other'
                    probs[category_mapper.get_category_index(category) + 1] += score
                    result_categories.append(category)
                overlay.update(classes, result_categories)
                max_prob = max(probs)
                best_category = probs.index(max_prob)
                if best_category == 0 and max_prob > .5:
                    servo.angle = -90
                elif best_category != 0:
                    servo.angle = -90 + (180 * best_category) / category_count
                    print('category: %d - %s' %
                          (best_category,
                           category_mapper.get_categories()[best_category - 1]))


if __name__ == '__main__':
    main()
