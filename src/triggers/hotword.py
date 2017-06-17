"""Detect hotword in the audio stream."""

import os
import time
import logging

from triggers.trigger import Trigger
from triggers import snowboydetect

logger = logging.getLogger('trigger')

TOP_DIR = os.path.dirname(os.path.abspath(__file__))

RESOURCE_FILE = os.path.join(TOP_DIR, "resources/common.res")
MODEL_FILE = os.path.join(TOP_DIR, "resources/snowboy.umdl")

class HotwordTrigger(Trigger):

    """Detect hotword in the audio stream."""

    def __init__(self, recorder):
        super().__init__()

        self.have_hotword = True  # don't start yet

        sensitivity = 1.0
        audio_gain = 2.0
        resource = RESOURCE_FILE
        decoder_model = MODEL_FILE

        tm = type(decoder_model)
        ts = type(sensitivity)
        if tm is not list:
            decoder_model = [decoder_model]
        if ts is not list:
            sensitivity = [sensitivity]
        model_str = ",".join(decoder_model)

        self.detector = snowboydetect.SnowboyDetect(
            resource_filename=resource.encode(), model_str=model_str.encode())
        self.detector.SetAudioGain(audio_gain)
        self.num_hotwords = self.detector.NumHotwords()

        if len(decoder_model) > 1 and len(sensitivity) == 1:
            sensitivity = sensitivity*self.num_hotwords
        if len(sensitivity) != 0:
            assert self.num_hotwords == len(sensitivity), \
                "number of hotwords in decoder_model (%d) and sensitivity " \
                "(%d) does not match" % (self.num_hotwords, len(sensitivity))
        sensitivity_str = ",".join([str(t) for t in sensitivity])
        if len(sensitivity) != 0:
            self.detector.SetSensitivity(sensitivity_str.encode())
        recorder.add_processor(self)

    def start(self):
        self.have_hotword = False

    def add_data(self, data):
        """ audio is mono 16bit signed at 16kHz """
        if not self.have_hotword and data:
            ans = self.detector.RunDetection(data)
            if ans == -1:
                logger.warning("Error initializing streams or reading audio data")
            elif ans > 0:
                message = "Keyword " + str(ans) + " detected at time: "
                message += time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime(time.time()))
                logger.info(message)
                self.have_hotword = True
                self.callback()
