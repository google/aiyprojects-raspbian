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

"""Auth helpers for Google Assistant API."""

import json
import os.path

import google_auth_oauthlib.flow
import google.auth.transport
import google.oauth2.credentials


ASSISTANT_OAUTH_SCOPE = (
    'https://www.googleapis.com/auth/assistant-sdk-prototype'
)


def load_credentials(credentials_path):
    migrate = False
    with open(credentials_path, 'r') as f:
        credentials_data = json.load(f)
        if 'access_token' in credentials_data:
            migrate = True
            del credentials_data['access_token']
            credentials_data['scopes'] = [ASSISTANT_OAUTH_SCOPE]
    if migrate:
        with open(credentials_path, 'w') as f:
            json.dump(credentials_data, f)
    credentials = google.oauth2.credentials.Credentials(token=None,
                                                        **credentials_data)
    http_request = google.auth.transport.requests.Request()
    credentials.refresh(http_request)
    return credentials


def credentials_flow_interactive(client_secrets_path):
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_path,
        scopes=[ASSISTANT_OAUTH_SCOPE])
    if 'DISPLAY' in os.environ:
        credentials = flow.run_local_server()
    else:
        credentials = flow.run_console()
    return credentials


def save_credentials(credentials_path, credentials):
    config_path = os.path.dirname(credentials_path)
    if not os.path.isdir(config_path):
        os.makedirs(config_path)
    with open(credentials_path, 'w') as f:
        json.dump({
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }, f)
