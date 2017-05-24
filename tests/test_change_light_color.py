
"""Test the change light color action."""

import mock
import unittest

import phue
import action

action._ = lambda s: s


class TestChangeLightColor(unittest.TestCase):

    def _say(self, text):
        self._say_text = text

    def setUp(self):
        self._say_text = None

    @mock.patch("action.phue")
    def test_change_light_color_no_bridge(self, mockedPhue):
        mockedPhue.PhueRegistrationException = phue.PhueRegistrationException
        bridge = mock.MagicMock()
        bridge.connect.side_effect = mockedPhue.PhueRegistrationException(0, "error")
        mockedPhue.Bridge.return_value = bridge

        action.ChangeLightColor(self._say, "philips-hue", "Lounge Lamp", "0077be").run()

        self.assertEqual(self._say_text,
                         "No bridge registered, press button on bridge and try again")

    @mock.patch("action.phue")
    @mock.patch("action.Converter")
    def test_change_light_color(self, Converter, mockedPhue):

        xyValue = [0.1, 0.2]

        converter = mock.MagicMock()
        Converter.return_value = converter
        converter.hex_to_xy.return_value = xyValue

        light = mock.MagicMock()
        lights = {
            "Lounge Lamp": light
        }
        bridge = mock.MagicMock()
        bridge.get_light_objects.return_value = lights
        mockedPhue.Bridge.return_value = bridge

        action.ChangeLightColor(self._say, "philips-hue", "Lounge Lamp", "0077be").run()

        mockedPhue.Bridge.assert_called_with("philips-hue")
        bridge.connect.assert_called()
        bridge.get_light_objects.assert_called_with("name")
        self.assertEqual(light.on, True)
        converter.hex_to_xy.assert_called_with("0077be")
        self.assertEqual(light.xy, xyValue)
        self.assertEqual(self._say_text, "Ok")


if __name__ == "__main__":
    unittest.main()
