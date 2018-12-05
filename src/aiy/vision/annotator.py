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

"""
An annotation library that draws overlays on the Raspberry Pi's camera preview.

Annotations include bounding boxes, text overlays, and points.
Annotations support partial opacity, however only with respect to the content in
the preview. A transparent fill value will cover up previously drawn overlay
under it, but not the camera content under it. A color of None can be given,
which will then not cover up overlay content drawn under the region.

Note: Overlays do not persist through to the storage layer so images saved from
the camera, will not contain overlays.
"""

import time

from PIL import Image, ImageDraw

import picamera

def _round_to_bit(value, power):
    """Rounds the given value to the next multiple of 2^power.

    Args:
      value: int to be rounded.
      power: power of two which the value should be rounded up to.
    Returns:
      the result of value rounded to the next multiple 2^power.
    """
    return (((value - 1) >> power) + 1) << power


def _round_buffer_dims(dims):
    """Appropriately rounds the given dimensions for image overlaying.

    The overlay buffer must be rounded the next multiple of 32 for the hight, and
    the next multiple of 16 for the width."""
    return (_round_to_bit(dims[0], 5), _round_to_bit(dims[1], 4))


# TODO(namiller): Add an annotator for images.
class Annotator:
    """Utility for managing annotations on the camera preview.

    Args:
      camera: picamera.PiCamera camera object to overlay on top of.
      bg_color: PIL.ImageColor (with alpha) for the background of the overlays.
      default_color: PIL.ImageColor (with alpha) default for the drawn content.
    """

    def __init__(self, camera, bg_color=None, default_color=None,
                 dimensions=None):
        self._dims = dimensions if dimensions else camera.resolution
        self._buffer_dims = _round_buffer_dims(self._dims)
        self._buffer = Image.new('RGBA', self._buffer_dims)
        self._overlay = camera.add_overlay(
            self._buffer.tobytes(), format='rgba', layer=3, size=self._buffer_dims)
        self._draw = ImageDraw.Draw(self._buffer)
        self._bg_color = bg_color if bg_color else (0, 0, 0, 0xA0)
        self._default_color = default_color if default_color else (0xFF, 0, 0, 0xFF)

        # MMALPort has a bug in enable.wrapper, where it always calls
        # self._pool.send_buffer(block=False) regardless of the port direction.
        # This is in contrast to setup time when it only calls
        # self._pool.send_all_buffers(block=False)
        # if self._port[0].type == mmal.MMAL_PORT_TYPE_OUTPUT.
        # Because of this bug updating an overlay once will log a MMAL_EAGAIN
        # error every update. This is safe to ignore as we the user is driving
        # the renderer input port with calls to update() that dequeue buffers
        # and sends them to the input port (so queue is empty on when
        # send_all_buffers(block=False) is called from wrapper).
        # As a workaround, monkey patch MMALPortPool.send_buffer and
        # silence the "error" if thrown by our overlay instance.
        original_send_buffer = picamera.mmalobj.MMALPortPool.send_buffer

        def silent_send_buffer(zelf, **kwargs):
            try:
                original_send_buffer(zelf, **kwargs)
            except picamera.exc.PiCameraMMALError as error:
                # Only silence MMAL_EAGAIN for our target instance.
                our_target = self._overlay.renderer.inputs[0].pool == zelf
                if not our_target or error.status != 14:
                    raise error

        picamera.mmalobj.MMALPortPool.send_buffer = silent_send_buffer

    def update(self):
        """Updates the contents of the overlay."""
        self._overlay.update(self._buffer.tobytes())

    def stop(self):
        """Removes the overlay from the screen."""
        self._draw.rectangle((0, 0) + self._dims, fill=0)
        self.update()

    def clear(self):
        """Clears the contents of the overlay - leaving only the plain background.
        """
        self._draw.rectangle((0, 0) + self._dims, fill=self._bg_color)

    def bounding_box(self, rect, outline=None, fill=None):
        """Draws a bounding box around the specified rectangle.

        Args:
          rect: (x1, y1, x2, y2) rectangle to be drawn - where (x1,y1) and (x2, y2)
            are opposite corners of the desired rectangle.
          outline: PIL.ImageColor with which to draw the outline (defaults to the
            configured default_color).
          fill: PIL.ImageColor with which to fill the rectangel (defaults to None
          which will not cover up drawings under the region.
        """
        outline = self._default_color if outline is None else outline
        self._draw.rectangle(rect, fill=fill, outline=outline)

    # TODO(namiller): Add a font size parameter and load a truetype font.
    def text(self, location, text, color=None):
        """Draws the given text at the given location.

        Args:
          location: (x,y) point at which to draw the text (upper left corner).
          text: string to be drawn.
          color: PIL.ImageColor to draw the string in (defaults to default_color).
        """
        color = self._default_color if color is None else color
        self._draw.text(location, text, fill=color)

    def point(self, location, radius=1, color=None):
        """Draws a point of the given size at the given location.

        Args:
          location: (x,y) center of the point to be drawn.
          radius: the radius of the point to be drawn.
          color: The color to draw the point in (defaults to default_color).
        """
        color = self._default_color if color is None else color
        self._draw.ellipse(
            (location[0] - radius, location[1] - radius, location[0] + radius,
             location[1] + radius),
            fill=color)


def _main():
    """Example usage of the annotator utility.

    Demonstrates setting up a camera preview, drawing slowly moving/intersecting
    animations over it, and clearing the overlays."""
    with picamera.PiCamera() as camera:
        # Resolution can be arbitrary.
        camera.resolution = (351, 561)
        camera.start_preview()
        annotator = Annotator(camera)
        for i in range(10):
            annotator.clear()
            annotator.bounding_box(
                (20, 20, 70, 70), outline=(0, 0xFF, 0, 0xFF), fill=0)
            annotator.bounding_box((10 * i, 10, 10 * i + 50, 60))
            annotator.bounding_box(
                (80, 0, 130, 50), outline=(0, 0, 0xFF, 0xFF), fill=0)
            annotator.text((100, 100), 'Hello World')
            annotator.point((10, 100), radius=5)
            annotator.update()
            time.sleep(1)
        annotator.stop()
        time.sleep(10)


if __name__ == '__main__':
    _main()
