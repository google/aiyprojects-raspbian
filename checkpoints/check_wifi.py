#!/usr/bin/env python3
#
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

"""Check that Wi-Fi is working."""

import socket
import subprocess
import traceback

WPA_CONF_PATH = '/etc/wpa_supplicant/wpa_supplicant.conf'
GOOGLE_SERVER_ADDRESS = ('speech.googleapis.com', 443)

ERROR_NOT_CONFIGURED='''
Please click the Wi-Fi icon at the top right to set up a Wi-Fi network.
'''

ERROR_NOT_CONNECTED='''
Please click the Wi-Fi icon at the top right to check your Wi-Fi settings.
'''

ERROR_GOOGLE_SERVER='''
Failed to reach Google servers. Please check that your Wi-Fi network is
connected to the Internet.
'''


def error(message):
    print(message.strip())


def check_wifi_is_configured():
    """Check wpa_supplicant.conf has at least one network configured."""
    output = subprocess.check_output(['sudo', 'cat', WPA_CONF_PATH]).decode('utf-8')
    if 'network=' not in output:
        error(ERROR_NOT_CONFIGURED)
        return False
    return True


def check_wifi_is_connected():
    """Check wlan0 has an IP address."""
    output = subprocess.check_output(['ifconfig', 'wlan0']).decode('utf-8')
    if 'inet ' not in output:
        error(ERROR_NOT_CONNECTED)
        return False
    return True


def check_can_reach_google_server():
    """Check the API server is reachable on port 443."""
    try:
        with socket.create_connection(GOOGLE_SERVER_ADDRESS, timeout=10):
            pass
        return True
    except:
        error(ERROR_GOOGLE_SERVER)
        return False


def main():
    print('Checking the Wi-Fi connection...')

    if not check_wifi_is_configured():
        return

    if not check_wifi_is_connected():
        return

    if not check_can_reach_google_server():
        return

    print('Wi-Fi seems to be working!')


if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
    finally:
        input('Press Enter to close...')
