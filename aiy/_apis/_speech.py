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

"""Classes for speech interaction."""

from abc import abstractmethod
import collections
import logging
import os
import sys
import tempfile
import wave

import google.auth
import google.auth.exceptions
import google.auth.transport.grpc
import google.auth.transport.requests
try:
    from google.cloud import speech
    from google.cloud.speech import enums
    from google.cloud.speech import types
except ImportError:
    print("Failed to import google.cloud.speech. Try:")
    print("    env/bin/pip install -r requirements.txt")
    sys.exit(1)

from google.rpc import code_pb2 as error_code
from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc,
)
import grpc
from six.moves import queue

import aiy.i18n

logger = logging.getLogger('speech')

AUDIO_SAMPLE_SIZE = 2  # bytes per sample
AUDIO_SAMPLE_RATE_HZ = 16000

# Expected location of the service credentials file:
SERVICE_CREDENTIALS = os.path.expanduser('~/cloud_speech.json')


_Result = collections.namedtuple('_Result', ['transcript', 'response_audio'])


class Error(Exception):
    pass


class _ChannelFactory(object):

    """Creates gRPC channels with a given configuration."""

    def __init__(self, api_host, credentials):
        self._api_host = api_host
        self._credentials = credentials

        self._checked = False

    def make_channel(self):
        """Creates a secure channel."""

        request = google.auth.transport.requests.Request()
        target = self._api_host + ':443'

        if not self._checked:
            # Refresh now, to catch any errors early. Otherwise, they'll be
            # raised and swallowed somewhere inside gRPC.
            self._credentials.refresh(request)
            self._checked = True

        return google.auth.transport.grpc.secure_authorized_channel(
            self._credentials, request, target)


class GenericSpeechRequest(object):

    """Common base class for Cloud Speech and Assistant APIs."""

    # TODO(rodrigoq): Refactor audio logging.
    # pylint: disable=attribute-defined-outside-init,too-many-instance-attributes

    DEADLINE_SECS = 185

    def __init__(self, api_host, credentials):
        self.dialog_follow_on = False
        self._audio_queue = queue.Queue()
        self._phrases = []
        self._channel_factory = _ChannelFactory(api_host, credentials)
        self._endpointer_cb = None
        self._audio_logging_enabled = False
        self._request_log_wav = None

    def add_phrases(self, phrases):
        """Makes the recognition more likely to recognize the given phrase(s).
        phrases: an object with a method get_phrases() that returns a list of
                 phrases.
        """

        self._phrases.extend(phrases.get_phrases())

    def add_phrase(self, phrase):
        """Makes the recognition more likely to recognize the given phrase."""
        self._phrases.append(phrase)

    def set_endpointer_cb(self, cb):
        """Callback to invoke on end of speech."""
        self._endpointer_cb = cb

    def set_audio_logging_enabled(self, audio_logging_enabled=True):
        self._audio_logging_enabled = audio_logging_enabled

        if audio_logging_enabled:
            self._audio_log_dir = tempfile.mkdtemp()
            self._audio_log_ix = 0

    def reset(self):
        while True:
            try:
                self._audio_queue.get(False)
            except queue.Empty:
                return

        self.dialog_follow_on = False

    def add_data(self, data):
        self._audio_queue.put(data)

    def end_audio(self):
        self.add_data(None)

    def _get_speech_context(self):
        """Return a SpeechContext instance to bias recognition towards certain
        phrases.
        """
        return types.SpeechContext(
            phrases=self._phrases,
        )

    @abstractmethod
    def _make_service(self, channel):
        """Create a service stub.
        """
        return

    @abstractmethod
    def _create_config_request(self):
        """Create a config request for the given endpoint.

        This is sent first to the server to configure the speech recognition.
        """
        return

    @abstractmethod
    def _create_audio_request(self, data):
        """Create an audio request for the given endpoint.

        This is sent to the server with audio to be recognized.
        """
        return

    def _request_stream(self):
        """Yields a config request followed by requests constructed from the
        audio queue.
        """
        yield self._create_config_request()

        while True:
            data = self._audio_queue.get()

            if not data:
                return

            if self._request_log_wav:
                self._request_log_wav.writeframes(data)

            yield self._create_audio_request(data)

    @abstractmethod
    def _create_response_stream(self, service, request_stream, deadline):
        """Given a request stream, start the gRPC call to get the response
        stream.
        """
        return

    @abstractmethod
    def _stop_sending_audio(self, resp):
        """Return true if this response says user has stopped speaking.

        This stops the request from sending further audio.
        """
        return

    @abstractmethod
    def _handle_response(self, resp):
        """Handle a response from the remote API.

        Args:
            resp: StreamingRecognizeResponse instance
        """
        return

    def _end_audio_request(self):
        self.end_audio()
        if self._endpointer_cb:
            self._endpointer_cb()

    def _handle_response_stream(self, response_stream):
        for resp in response_stream:
            if self._stop_sending_audio(resp):
                self._end_audio_request()

            self._handle_response(resp)

        # Server has closed the connection
        return self._finish_request() or ''

    def _start_logging_request(self):
        """Open a WAV file to log the request audio."""
        self._audio_log_ix += 1
        request_filename = '%s/request.%03d.wav' % (
            self._audio_log_dir, self._audio_log_ix)
        logger.info('Writing request to %s', request_filename)

        self._request_log_wav = wave.open(request_filename, 'w')

        self._request_log_wav.setnchannels(1)
        self._request_log_wav.setsampwidth(AUDIO_SAMPLE_SIZE)
        self._request_log_wav.setframerate(AUDIO_SAMPLE_RATE_HZ)

    def _finish_request(self):
        """Called after the final response is received."""

        if self._request_log_wav:
            self._request_log_wav.close()

        return _Result(None, None)

    def do_request(self):
        """Establishes a connection and starts sending audio to the cloud
        endpoint. Responses are handled by the subclass until one returns a
        result.

        Returns:
            namedtuple with the following fields:
                transcript: string with transcript of user query
                response_audio: optionally, an audio response from the server

        Raises speech.Error on error.
        """
        try:
            service = self._make_service(self._channel_factory.make_channel())

            response_stream = self._create_response_stream(
                service, self._request_stream(), self.DEADLINE_SECS)

            if self._audio_logging_enabled:
                self._start_logging_request()

            return self._handle_response_stream(response_stream)
        except (
                google.auth.exceptions.GoogleAuthError,
                grpc.RpcError,
        ) as exc:
            raise Error('Exception in speech request') from exc


class CloudSpeechRequest(GenericSpeechRequest):

    """A transcription request to the Cloud Speech API.

    Args:
        credentials_file: path to service account credentials JSON file
    """

    SCOPE = 'https://www.googleapis.com/auth/cloud-platform'

    def __init__(self, credentials_file):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_file
        credentials, _ = google.auth.default(scopes=[self.SCOPE])

        super().__init__('speech.googleapis.com', credentials)

        self._transcript = None

    def reset(self):
        super().reset()
        self._transcript = None

    def _make_service(self, channel):
        return speech.SpeechClient()

    def _create_config_request(self):
        recognition_config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=AUDIO_SAMPLE_RATE_HZ,
            language_code=aiy.i18n.get_language_code(),
            speech_contexts=[self._get_speech_context()],
        )
        streaming_config = types.StreamingRecognitionConfig(
            config=recognition_config,
            single_utterance=True,
        )

        # TODO(rodrigoq): we're actually returning a Config, not a Request, as
        # the v1 API takes the Config and wraps it up in a Request, but we still
        # want to share code with the Assistant API. Can we clean this up?
        return streaming_config

    def _create_audio_request(self, data):
        return types.StreamingRecognizeRequest(audio_content=data)

    def _create_response_stream(self, client, request_stream, deadline):
        config = next(request_stream)
        return client.streaming_recognize(config, request_stream)

    def _stop_sending_audio(self, resp):
        """Check the endpointer type to see if an utterance has ended."""

        if resp.speech_event_type:
            speech_event_type = types.StreamingRecognizeResponse.SpeechEventType.Name(
                resp.speech_event_type)
            logger.info('endpointer_type: %s', speech_event_type)

        END_OF_SINGLE_UTTERANCE = types.StreamingRecognizeResponse.SpeechEventType.Value(
            'END_OF_SINGLE_UTTERANCE')
        return resp.speech_event_type == END_OF_SINGLE_UTTERANCE

    def _handle_response(self, resp):
        """Store the last transcript we received."""
        if resp.results:
            self._transcript = ' '.join(
                result.alternatives[0].transcript for result in resp.results)
            logger.info('transcript: %s', self._transcript)

    def _finish_request(self):
        super()._finish_request()
        return _Result(self._transcript, None)


class AssistantSpeechRequest(GenericSpeechRequest):

    """A request to the Assistant API, which returns audio and text."""

    def __init__(self, credentials, model_id, device_id):

        super().__init__('embeddedassistant.googleapis.com', credentials)

        self.model_id = model_id
        self.device_id = device_id

        self._conversation_state = None
        self._response_audio = b''
        self._transcript = None

    def reset(self):
        super().reset()
        self._response_audio = b''
        self._transcript = None

    def _make_service(self, channel):
        return embedded_assistant_pb2_grpc.EmbeddedAssistantStub(channel)

    def _create_config_request(self):
        audio_in_config = embedded_assistant_pb2.AudioInConfig(
            encoding='LINEAR16',
            sample_rate_hertz=AUDIO_SAMPLE_RATE_HZ,
        )
        audio_out_config = embedded_assistant_pb2.AudioOutConfig(
            encoding='LINEAR16',
            sample_rate_hertz=AUDIO_SAMPLE_RATE_HZ,
            volume_percentage=50,
        )
        device_config = embedded_assistant_pb2.DeviceConfig(
            device_id=self.device_id,
            device_model_id=self.model_id,
        )
        dialog_state_in = embedded_assistant_pb2.DialogStateIn(
            conversation_state=self._conversation_state,
            language_code=aiy.i18n.get_language_code(),
        )
        assist_config = embedded_assistant_pb2.AssistConfig(
            audio_in_config=audio_in_config,
            audio_out_config=audio_out_config,
            device_config=device_config,
            dialog_state_in=dialog_state_in,
        )

        return embedded_assistant_pb2.AssistRequest(config=assist_config)

    def _create_audio_request(self, data):
        return embedded_assistant_pb2.AssistRequest(audio_in=data)

    def _create_response_stream(self, service, request_stream, deadline):
        return service.Assist(request_stream, deadline)

    def _stop_sending_audio(self, resp):
        if resp.event_type:
            logger.info('event_type: %s', resp.event_type)

        return (resp.event_type ==
                embedded_assistant_pb2.AssistResponse.END_OF_UTTERANCE)

    def _handle_response(self, resp):
        """Accumulate audio and text from the remote end. It will be handled
        in _finish_request().
        """

        if resp.speech_results:
            self._transcript = ' '.join(r.transcript for r in resp.speech_results)
            logger.info('transcript: %s', self._transcript)

        self._response_audio += resp.audio_out.audio_data

        if resp.dialog_state_out.conversation_state:
            self._conversation_state = resp.dialog_state_out.conversation_state

        if resp.dialog_state_out.microphone_mode:
            self.dialog_follow_on = (
                resp.dialog_state_out.microphone_mode ==
                embedded_assistant_pb2.DialogStateOut.DIALOG_FOLLOW_ON)

    def _finish_request(self):
        super()._finish_request()

        if self._response_audio and self._audio_logging_enabled:
            self._log_audio_out(self._response_audio)

        return _Result(self._transcript, self._response_audio)

    def _log_audio_out(self, frames):
        response_filename = '%s/response.%03d.wav' % (
            self._audio_log_dir, self._audio_log_ix)
        logger.info('Writing response to %s', response_filename)

        response_wav = wave.open(response_filename, 'w')
        response_wav.setnchannels(1)
        response_wav.setsampwidth(AUDIO_SAMPLE_SIZE)
        response_wav.setframerate(AUDIO_SAMPLE_RATE_HZ)
        response_wav.writeframes(frames)
        response_wav.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # for testing: use audio from a file
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?', default='test_speech.raw')
    args = parser.parse_args()

    req = CloudSpeechRequest(SERVICE_CREDENTIALS)

    with open(args.file, 'rb') as f:
        while True:
            chunk = f.read(64000)
            if not chunk:
                break
            req.add_data(chunk)
    req.end_audio()

    print('down response:', req.do_request())
