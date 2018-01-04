#!/bin/bash
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

scripts_dir="$(dirname "${BASH_SOURCE[0]}")"

# make sure we're running as the owner of the checkout directory
RUN_AS="$(ls -ld "$scripts_dir" | awk 'NR==1 {print $3}')"
if [ "$USER" != "$RUN_AS" ]
then
    echo "This script must run as $RUN_AS, trying to change user..."
    exec sudo -u $RUN_AS $0
fi

sudo apt-get -y install alsa-utils python3-all-dev python3-pip python3-numpy \
  python3-rpi.gpio python3-pysocks virtualenv rsync libttspico-utils ntpdate
sudo pip3 install --upgrade pip virtualenv

cd "${scripts_dir}/.."
virtualenv --system-site-packages -p python3 env
env/bin/pip install -r requirements.txt

# The google-assistant-library is only available on some platforms.
if [[ "$(uname -m)" == "armv7l" || "$(uname -m)" == "x86_64" ]] ; then
  env/bin/pip install google-assistant-library==0.1.0
fi
