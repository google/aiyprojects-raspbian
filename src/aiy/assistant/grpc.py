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

"""An API to access the Google Assistant Service."""

import array
import logging
import math
import os
import sys

os.environ['GRPC_POLL_STRATEGY'] = 'epoll1'
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials

from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2_grpc

from aiy.assistant import auth_helpers, device_helpers
from aiy.board import Led
from aiy.voice.audio import AudioFormat, Recorder, BytesPlayer

logger = logging.getLogger(__name__)

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
END_OF_UTTERANCE = embedded_assistant_pb2.AssistResponse.END_OF_UTTERANCE
DIALOG_FOLLOW_ON = embedded_assistant_pb2.DialogStateOut.DIALOG_FOLLOW_ON
CLOSE_MICROPHONE = embedded_assistant_pb2.DialogStateOut.CLOSE_MICROPHONE
PLAYING = embedded_assistant_pb2.ScreenOutConfig.PLAYING
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5
AUDIO_SAMPLE_RATE_HZ = 16000
AUDIO_FORMAT=AudioFormat(sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
                         num_channels=1,
                         bytes_per_sample=2)

def _normalize_audio_buffer(buf, volume_percentage, sample_width=2):
    assert sample_width == 2
    scale = math.pow(2, 1.0 * volume_percentage / 100) - 1
    arr = array.array('h', buf)
    for i in range(0, len(arr)):
        arr[i] = int(arr[i] * scale)
    return arr.tobytes()

# https://developers.google.com/assistant/sdk/reference/rpc/
class AssistantServiceClient:
    def __init__(self, language_code='en-US', volume_percentage=100):
        self._volume_percentage = volume_percentage  # Mutable state.
        self._conversation_state = None              # Mutable state.
        self._language_code = language_code

        ##
        credentials = auth_helpers.get_assistant_credentials()
        device_model_id, device_id = device_helpers.get_ids_for_service(credentials)

        logger.info('device_model_id: %s', device_model_id)
        logger.info('device_id: %s', device_id)

        http_request = google.auth.transport.requests.Request()
        try:
            credentials.refresh(http_request)
        except Exception as e:
            raise RuntimeError('Error loading credentials: %s', e)

        api_endpoint = ASSISTANT_API_ENDPOINT
        grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
            credentials, http_request, api_endpoint)
        logger.info('Connecting to %s', api_endpoint)
        ##

        self._assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(grpc_channel)
        self._device_config = embedded_assistant_pb2.DeviceConfig(
            device_model_id=device_model_id,
            device_id=device_id)

    @property
    def volume_percentage(self):
        return self._volume_percentage

    def _recording_started(self):
        logger.info('Recording started.')

    def _recording_stopped(self):
        logger.info('Recording stopped.')

    def _playing_started(self):
        logger.info('Playing started.')

    def _playing_stopped(self):
        logger.info('Playing stopped.')

    def _requests(self, recorder):
        audio_in_config = embedded_assistant_pb2.AudioInConfig(
            encoding='LINEAR16',
            sample_rate_hertz=AUDIO_SAMPLE_RATE_HZ)

        audio_out_config = embedded_assistant_pb2.AudioOutConfig(
            encoding='LINEAR16',
            sample_rate_hertz=AUDIO_SAMPLE_RATE_HZ,
            volume_percentage=self._volume_percentage)

        dialog_state_in = embedded_assistant_pb2.DialogStateIn(
            conversation_state=self._conversation_state,
            language_code=self._language_code)

        config = embedded_assistant_pb2.AssistConfig(
            audio_in_config=audio_in_config,
            audio_out_config=audio_out_config,
            device_config=self._device_config,
            dialog_state_in=dialog_state_in)

        yield embedded_assistant_pb2.AssistRequest(config=config)

        for chunk in recorder.record(AUDIO_FORMAT,
                                     chunk_duration_sec=0.1,
                                     on_start=self._recording_started,
                                     on_stop=self._recording_stopped):
            yield embedded_assistant_pb2.AssistRequest(audio_in=chunk)


    def _assist(self, recorder, play, deadline):
        continue_conversation = False

        for response in self._assistant.Assist(self._requests(recorder), deadline):
            if response.event_type == END_OF_UTTERANCE:
                logger.info('End of audio request detected.')
                recorder.done()

            # Process 'speech_results'.
            if response.speech_results:
                logger.info('You said: "%s".',
                            ' '.join(r.transcript for r in response.speech_results))
            # Process 'audio_out'.
            if response.audio_out.audio_data:
                recorder.done()  # Just in case.
                play(_normalize_audio_buffer(response.audio_out.audio_data,
                                             self._volume_percentage))

            # Process 'dialog_state_out'.
            if response.dialog_state_out.conversation_state:
                conversation_state = response.dialog_state_out.conversation_state
                logger.debug('Updating conversation state.')
                self._conversation_state = conversation_state  # Mutable state change.

            volume_percentage = response.dialog_state_out.volume_percentage
            if volume_percentage:
                logger.info('Setting volume to %s%%', volume_percentage)
                self._volume_percentage = volume_percentage  # Mutable state change.

            supplemental_display_text = response.dialog_state_out.supplemental_display_text
            if supplemental_display_text:
                logger.info('Assistant said: "%s"', supplemental_display_text)

            microphone_mode = response.dialog_state_out.microphone_mode
            if microphone_mode == DIALOG_FOLLOW_ON:
                continue_conversation = True
                logger.info('Expecting follow-on query from user.')
            elif microphone_mode == CLOSE_MICROPHONE:
                continue_conversation = False
                logger.info('Not expecting follow-on query from user.')

        return continue_conversation

    def conversation(self, deadline=DEFAULT_GRPC_DEADLINE):
        keep_talking = True
        while keep_talking:
            playing = False
            with Recorder() as recorder, BytesPlayer() as player:
                play = player.play(AUDIO_FORMAT)

                def wrapped_play(data):
                    nonlocal playing
                    if not playing:
                        self._playing_started()
                        playing = True
                    play(data)

                try:
                    keep_talking = self._assist(recorder, wrapped_play, deadline)
                finally:
                    play(None)       # Signal end of sound stream.
                    recorder.done()  # Signal stop recording.

            if playing:
                self._playing_stopped()


class AssistantServiceClientWithLed(AssistantServiceClient):
    def _update_led(self, state, brightness):
        self._board.led.state = state
        self._board.led.brightness = brightness

    def __init__(self, board, language_code='en-US', volume_percentage=100):
        super().__init__(language_code, volume_percentage)

        self._board = board
        self._update_led(Led.ON, 0.1)

    def _recording_started(self):
        super()._recording_started()
        self._update_led(Led.ON, 1.0)

    def _recording_stopped(self):
        self._update_led(Led.ON, 0.1)
        super()._recording_stopped()

    def _playing_started(self):
        super()._playing_started()
        self._update_led(Led.PULSE_SLOW, 1.0)

    def _playing_stopped(self):
        self._update_led(Led.ON, 0.1)
        super()._playing_stopped()

