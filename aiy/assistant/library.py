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

"""This is a wrapper for ``google.assistant.library`` that handles model and device
registration based on the project name in your `assistant.json` file.

All APIs from ``google.assistant.library`` are available through this module, such as
``Assistant.start()`` to start the assistant, and ``Assistant.start_conversation()`` to start
a conversation, but they are not documented here. Instead refer to the
`Google Assistant Library for Python documentation
<https://developers.google.com/assistant/sdk/reference/library/python/>`_.

For example code, see :github:`src/examples/voice/assistant_library_demo.py`.
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
