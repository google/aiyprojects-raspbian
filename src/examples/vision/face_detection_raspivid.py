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
"""Camera inference face detection demo code.

Runs continuous face detection on the VisionBonnet and prints the number of
detected faces.

Example:
face_detection_raspivid.py --num_frames 10
"""
import argparse
import subprocess

from aiy.vision.inference import CameraInference
from aiy.vision.models import face_detection

def avg_joy_score(faces):
    if faces:
        return sum(face.joy_score for face in faces) / len(faces)
    return 0.0

def raspivid_cmd(sensor_mode):
    return ('raspivid', '--mode', str(sensor_mode), '--timeout', '0', '--nopreview')

def main():
    """Face detection camera inference example."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--num_frames', '-n', type=int, dest='num_frames', default=-1,
        help='Sets the number of frames to run for, otherwise runs forever.')
    args = parser.parse_args()

    raspivid = subprocess.Popen(raspivid_cmd(sensor_mode=4))
    try:
        with CameraInference(face_detection.model()) as inference:
            for i, result in enumerate(inference.run()):
                if i == args.num_frames:
                    break
                faces = face_detection.get_faces(result)

                print('Iteration #%05d (%5.2f fps): num_faces=%d, avg_joy_score=%.2f, dur=%d ms' %
                    (i, inference.rate, len(faces), avg_joy_score(faces), result.duration_ms))
    finally:
        raspivid.terminate()
        raspivid.wait()

if __name__ == '__main__':
    main()
