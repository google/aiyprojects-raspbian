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

"""A demo of the Piezo Buzzer."""

import sys

from aiy.toneplayer import Note
from aiy.trackplayer import NoteOff, Arpeggio, StopPlaying, TrackPlayer, TrackLoader


def main():
    if len(sys.argv) == 1:
        print("Usage: buzzer_tracker_demo.py <path-to-track-file>")
        return

    loader = TrackLoader(22, sys.argv[1], debug=True)
    player = loader.load()
    player.play()


if __name__ == '__main__':
    main()
