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

RUN_AS="pi"

set -o errexit

if [ "$USER" != "$RUN_AS" ]
then
    echo "This script must run as $RUN_AS, trying to change user..."
    exec sudo -u $RUN_AS $0
fi

sudo apt-get -y install alsa-utils python3-all-dev python3-pip python3-numpy \
  python3-scipy python3-virtualenv rsync sox libttspico-utils ntpdate
sudo apt-get -y install -t stretch python3-httplib2 python3-configargparse
sudo pip3 install --upgrade pip virtualenv

cd ~/voice-recognizer-raspi
virtualenv --system-site-packages -p python3 env
env/bin/pip install google-assistant-sdk[auth_helpers]==0.1.0 \
  grpc-google-cloud-speech-v1beta1==0.14.0 protobuf==3.1.0
