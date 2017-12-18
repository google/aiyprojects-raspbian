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
"""Trigger PiCamera when face is detected."""

from aiy.vision.inference import CameraInference
from aiy.vision.models import face_detection
from picamera import PiCamera


def main():
  with PiCamera() as camera:
    # Configure camera
    camera.resolution = (1640, 922)  # Full Frame, 16:9 (Camera v2)
    camera.start_preview()

    # Do inference on VisionBonnet
    with CameraInference(face_detection.model()) as inference:
      for result in inference.run():
        if len(face_detection.get_faces(result)) >= 1:
          camera.capture('faces.jpg')
          break

    # Stop preview
    camera.stop_preview()


if __name__ == '__main__':
  main()

