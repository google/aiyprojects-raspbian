#!/usr/bin/env python
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
"""Camera inference face detection demo code.

Runs continuous face detection on the VisionBonnet and prints the number of
detected faces.

Example:
face_detection_camera.py --num_frames 10
"""
import argparse

from aiy.vision.inference import CameraInference
from aiy.vision.models import face_detection
from examples.vision.annotator import Annotator
from picamera import PiCamera


def main():
  """Face detection camera inference example."""
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--num_frames',
      '-n',
      type=int,
      dest='num_frames',
      default=-1,
      help='Sets the number of frames to run for, otherwise runs forever.')
  args = parser.parse_args()

  with PiCamera() as camera:
    # Forced sensor mode, 1640x1232, full FoV. See:
    # https://picamera.readthedocs.io/en/release-1.13/fov.html#sensor-modes
    # This is the resolution inference run on.
    camera.sensor_mode = 4

    # Scaled and cropped resolution. If different from sensor mode implied
    # resolution, inference results must be adjusted accordingly. This is
    # true in particular when camera.start_recording is used to record an
    # encoded h264 video stream as the Pi encoder can't encode all native
    # sensor resolutions, or a standard one like 1080p may be desired.
    camera.resolution = (1640, 1232)

    # Start the camera stream.
    camera.framerate = 30
    camera.start_preview()

    # Annotator renders in software so use a smaller size and scale results
    # for increased performace.
    annotator = Annotator(camera, dimensions=(320, 240))
    scale_x = 320 / 1640
    scale_y = 240 / 1232

    # Incoming boxes are of the form (x, y, width, height). Scale and
    # transform to the form (x1, y1, x2, y2).
    def transform(bounding_box):
      x, y, width, height = bounding_box
      return (scale_x * x, scale_y * y, scale_x * (x + width),
              scale_y * (y + height))

    with CameraInference(face_detection.model()) as inference:
      for i, result in enumerate(inference.run()):
        if i == args.num_frames:
          break
        faces = face_detection.get_faces(result)
        annotator.clear()
        for face in faces:
          annotator.bounding_box(transform(face.bounding_box), fill=0)
        annotator.update()
        print('Iteration #%d: num_faces=%d' % (i, len(faces)))

    camera.stop_preview()


if __name__ == '__main__':
  main()
