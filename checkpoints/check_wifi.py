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

"""Check that the WiFi is working."""

import socket
import subprocess
import traceback

WPA_CONF_PATH = '/etc/wpa_supplicant/wpa_supplicant.conf'
GOOGLE_SERVER_ADDRESS = ('speech.googleapis.com', 443)


def check_wifi_is_configured():
    """Check wpa_supplicant.conf has at least one network configured."""
    output = subprocess.check_output(['sudo', 'cat', WPA_CONF_PATH]).decode('utf-8')

    return 'network=' in output


def check_wifi_is_connected():
    """Check wlan0 has an IP address."""
    output = subprocess.check_output(['ifconfig', 'wlan0']).decode('utf-8')

    return 'inet addr' in output


def check_can_reach_google_server():
    """Check the API server is reachable on port 443."""
    print("Trying to contact Google's servers...")
    try:
        sock = socket.create_connection(GOOGLE_SERVER_ADDRESS, timeout=10)
        sock.close()
        return True
    except Exception:  # pylint: disable=W0703
        return False


def main():
    """Run all checks and print status."""
    print('Checking the WiFi connection...')

    if not check_wifi_is_configured():
        print('Please click the WiFi icon at the top right to set up a WiFi network.')
        return

    if not check_wifi_is_connected():
        print(
            """You are not connected to WiFi. Please click the WiFi icon at the top right
to check your settings.""")
        return

    if not check_can_reach_google_server():
        print(
            """Failed to reach Google servers. Please check that your WiFi network is
connected to the internet.""")
        return

    print('The WiFi connection seems to be working.')


if __name__ == '__main__':
    try:
        main()
        input('Press Enter to close...')
    except:  # pylint: disable=bare-except
        traceback.print_exc()
        input('Press Enter to close...')
