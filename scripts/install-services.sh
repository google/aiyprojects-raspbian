#!/bin/bash
#
# Install systemd service files for running on startup.
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

set -o errexit

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 1>&2
   exit 1
fi

cd "$(dirname "${BASH_SOURCE[0]}")/.."
repo_path="$PWD"

# We want the uid of the user that runs sudo
userid=$(id -u $SUDO_USER)

# Use systemd-tmpfiles and create the PID directory on boot if it doesn't exist
sed -e "s:userid:${userid}:;s:username:$SUDO_USER:g" systemd/tmpfiles.d/create-run-dir.conf \
  > /etc/tmpfiles.d/create-run-dir.conf

for service in systemd/*.service; do
  sed "s:/home/pi/voice-recognizer-raspi:${repo_path}:g" "$service" \
    > "/lib/systemd/system/$(basename "$service")"
done

# voice-recognizer is not enabled by default, as it doesn't work until
# credentials are set up, so we explicitly enable the other services.
systemctl enable alsa-init.service
systemctl enable ntpdate.service
systemctl enable status-led.service
systemctl enable status-led-on.service
systemctl enable status-led-off.service
systemctl enable status-monitor.service
