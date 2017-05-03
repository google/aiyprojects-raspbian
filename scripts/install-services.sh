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

cd "$(dirname "${BASH_SOURCE[0]}")/.."

for service in systemd/*.service; do
  cp $service /lib/systemd/system/
done

# voice-recognizer is not enabled by default, as it doesn't work until
# credentials are set up, so we explicitly enable the other services.
sudo systemctl enable alsa-init.service
sudo systemctl enable ntpdate.service
sudo systemctl enable status-led.service
sudo systemctl enable status-led-on.service
sudo systemctl enable status-led-off.service
sudo systemctl enable status-monitor.service
