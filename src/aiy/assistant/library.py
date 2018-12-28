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
Facilitates access to the `Google Assistant Library`_, which provides APIs to initiate
conversations with the Google Assistant and create custom device commands commands.

This includes a wrapper for the ``Assistant`` class only. You must import all other Google
Assistant classes directly from the |code| :assistant:`google.assistant.library<>`\ |endcode| module
to handle each of the response events.

.. note::

    Hotword detection (such as "Okay Google") is not supported with the Raspberry Pi Zero
    (only with Raspberry Pi 2/3). If you're using a Pi Zero, you must instead use the button or
    another type of trigger to initiate a conversation with the Google Assistant.

.. py:class:: Assistant(credentials)

    Bases: |code| :assistant:`google.assistant.library.Assistant`\ |endcode|

    A wrapper for the |code| :assistant:`Assistant`\ |endcode| class that handles
    model and device registration based on the project name in your OAuth credentials
    (``assistant.json``) file.

    All the ``Assistant`` APIs are available through this class, such as
    |code| :assistant:`start()<google.assistant.library.Assistant.start>`\ |endcode| to start the
    Assistant, and |code| :assistant:`start_conversation()
    <google.assistant.library.Assistant.start_conversation>`\ |endcode| to start
    a conversation, but they are not documented here. Instead refer to the
    `Google Assistant Library for Python documentation
    <https://developers.google.com/assistant/sdk/reference/library/python/>`_.

    To get started, you must call :meth:`~aiy.assistant.auth_helpers.get_assistant_credentials`
    and pass the result to the ``Assistant`` constructor. For example::

        from google.assistant.library.event import EventType
        from aiy.assistant import auth_helpers
        from aiy.assistant.library import Assistant

        credentials = auth_helpers.get_assistant_credentials()
        with Assistant(credentials) as assistant:
            for event in assistant.start():
                process_event(event)

    For more example code, see :github:`src/examples/voice/assistant_library_demo.py`.

    :param credentials: The Google OAuth2 credentials for the device. Get this from
        :meth:`~aiy.assistant.auth_helpers.get_assistant_credentials`.
"""

import google.assistant.library

from aiy.assistant import device_helpers

class Assistant(google.assistant.library.Assistant):
    """Client for the Google Assistant Library.

    Similar to google.assistant.library.Assistant, but handles device
    registration.
    """

    def __init__(self, credentials):
        self._credentials = credentials
        self._model_id = device_helpers.register_model_id(credentials)

        super().__init__(credentials, self._model_id)

    def start(self):
        events = super().start()

        device_helpers.register_device_id(
            self._credentials, self._model_id, self.device_id, "SDK_LIBRARY")

        return events
