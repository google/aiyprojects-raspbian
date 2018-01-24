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

"""Device registration helpers for the Google Assistant API."""

import json
import os
import uuid

import google.auth.transport.requests

import aiy.assistant.auth_helpers


_DEVICE_MODEL = "voice-kit"
_DEVICE_MANUFACTURER = "AIY Projects"
_DEVICE_NAME = "Voice Kit"
_DEVICE_TYPE = "action.devices.types.LIGHT"

_DEVICE_ID_FILE = os.path.join(
        aiy.assistant.auth_helpers._VR_CACHE_DIR, 'device_id.json')


def _get_project_id():
    with open(aiy.assistant.auth_helpers._ASSISTANT_CREDENTIALS_FILE) as f:
        client_secrets_data = json.load(f)
        return client_secrets_data["installed"]["project_id"]


def _get_api_url(*args):
    return "/".join(
            ("https://embeddedassistant.googleapis.com/v1alpha2/projects",) + args)

def _load_ids(id_path):
    with open(id_path, 'r') as f:
        id_data = json.load(f)
    return id_data["model_id"], id_data["device_id"]


def _save_ids(id_path, model_id, device_id):
    if not os.path.exists(os.path.dirname(id_path)):
        os.makedirs(os.path.dirname(id_path))

    id_data = {
            "model_id": model_id,
            "device_id": device_id,
    }
    with open(id_path, 'w') as f:
        json.dump(id_data, f)


def _get_model_id(credentials, session, project_id):
    model_id = "%s-%s" % (project_id, _DEVICE_MODEL)
    payload = {
            "device_model_id": model_id,
            "project_id": project_id,
            "device_type": _DEVICE_TYPE,
            "manifest": {
                    "manufacturer": _DEVICE_MANUFACTURER,
                    "product_name": _DEVICE_NAME,
            },
    }
    r = session.post(_get_api_url(project_id, "deviceModels"),
                     data=json.dumps(payload))
    # Ignore 409, which means we've already created the model ID.
    if r.status_code != 409:
        r.raise_for_status()
    return model_id


def get_ids(credentials, model_id=None):
    """get_ids gets a Device ID for use with the Google Assistant SDK.

    It optionally also gets a Device Model ID if one is not given. The IDs are
    cached on disk so that a device keeps a consistent ID.

    Returns:
        a tuple: (model_id, device_id)
    """

    if os.path.exists(_DEVICE_ID_FILE):
        return _load_ids(_DEVICE_ID_FILE)

    session = google.auth.transport.requests.AuthorizedSession(credentials)
    project_id = _get_project_id()
    model_id = model_id or _get_model_id(credentials, session, project_id)

    device_id = "%s-%s" % (model_id, uuid.uuid4())
    # We can hardcode client_type as SDK_SERVICE, because the Assistant Library
    # creates its own device_id.
    payload = {
            "id": device_id,
            "model_id": model_id,
            "client_type": "SDK_SERVICE",
    }
    r = session.post(_get_api_url(project_id, "devices"),
                     data=json.dumps(payload))
    r.raise_for_status()

    _save_ids(_DEVICE_ID_FILE, model_id, device_id)
    return model_id, device_id


if __name__ == "__main__":
    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
    print("ids:", get_ids(credentials))
