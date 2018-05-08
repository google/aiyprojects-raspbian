# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Python Library for connecting to Google Cloud IoT Core via MQTT, using JWT.
This library connects to Google Cloud IoT Core via MQTT, using a JWT for device
authentication. After connection, publish_message can be used to provide an
arbitrary message to a cloud project. Configuration must be done using a
configuration file.
"""

import argparse
import configparser
import datetime
import os
import logging
import time
import jwt
import paho.mqtt.client as mqtt

from aiy._drivers._ecc608 import *

logger = logging.getLogger(__name__)


class CloudIot(object):
    def __init__(self, config_file, config_section='DEFAULT'):
        self._config = configparser.ConfigParser()
        self._config.read(config_file)

        if not self._config.getboolean(config_section, 'Enabled'):
            logger.warn('Cloud IoT is disabled per configuration.')
            self._enabled = False
            return

        config = self._config[config_section]
        self._project_id = config['ProjectID']
        self._cloud_region = config['CloudRegion']
        self._registry_id = config['RegistryID']
        self._device_id = config['DeviceID']
        self._ca_certs = config['CACerts']
        self._message_type = config['MessageType']
        self._mqtt_bridge_hostname = config['MQTTBridgeHostName']
        self._mqtt_bridge_port = config.getint('MQTTBridgePort')

        # TODO(michaelbrooks): Implement SW fallback.
        if not ecc608_is_valid():
            logging.warn('SW-based Cloud IoT is not yet enabled.')
            self._enabled = False
            return
        # For the HW Crypto chip, use ES256.
        self._algorithm = 'ES256'

        # Create our MQTT client. The client_id is a unique string that identifies
        # this device. For Google Cloud IoT Core, it must be in the format below.
        self._client = mqtt.Client(
            client_id='projects/%s/locations/%s/registries/%s/devices/%s' %
                       (self._project_id,
                        self._cloud_region,
                        self._registry_id,
                        self._device_id))

        # With Google Cloud IoT Core, the username field is ignored, and the
        # password field is used to transmit a JWT to authorize the device.
        self._client.username_pw_set(
            username='unused',
            password=self._create_jwt(
                self._project_id, self._algorithm))

        # Enable SSL/TLS support.
        self._client.tls_set(ca_certs=self._ca_certs)

        # Connect to the Google MQTT bridge.
        self._client.connect(self._mqtt_bridge_hostname, self._mqtt_bridge_port)

        logger.info('Successfully connected to Cloud IoT')
        self._enabled = True

    def enabled(self):
        return self._enabled

    def publish_message(self, message):
        if not self._enabled:
            return

        # Start the network loop.
        self._client.loop_start()

        # Publish to the events or state topic based on the flag.
        sub_topic = 'events' if self._message_type == 'event' else 'state'

        mqtt_topic = '/devices/%s/%s' % (self._device_id, sub_topic)

        # Publish payload using JSON dumps to create bytes representation.
        payload = '%s/%s-payload-%s' % (
            self._registry_id, self._device_id, json.dumps(message))

        # Publish payload to the MQTT topic. qos=1 means at least once
        # delivery. Cloud IoT Core also supports qos=0 for at most once
        # delivery.
        self._client.publish(mqtt_topic, payload, qos=1)

        # End the network loop and finish.
        self._client.loop_stop()

    def register_message_callbacks(self, callbacks):
        if 'on_connect' in callbacks:
            self._client.on_connect = callbacks['on_connect']
        if 'on_disconnect' in callbacks:
            self._client.on_disconnect = callbacks['on_disconnect']
        if 'on_publish' in callbacks:
            self._client.on_publish = callbacks['on_publish']
        if 'on_message' in callbacks:
            self._client.on_message = callbacks['on_message']
        if 'on_unsubscribe' in callbacks:
            self._client.on_unsubscribe = callbacks['on_unsubscribe']
        if 'on_log' in callbacks:
            self._client.on_log = callbacks['on_log']

    def _create_jwt(self, project_id, algorithm):
        """Creates a JWT (https://jwt.io) to establish an MQTT connection.
            Args:
                Project_id: The cloud project ID this device belongs to
                 algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
            Returns:
                An MQTT generated from the given project_id and private key, which
                expires in 20 minutes. After 20 minutes, your client will be
                disconnected, and a new JWT will have to be generated.
            Raises:
                ValueError: If the private_key_file does not contain a known key.
        """

        token = {
            # The time that the token was issued at
            'iat': datetime.datetime.utcnow(),
            # The time the token expires.
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            # The audience field should always be set to the GCP project id.
            'aud': project_id
        }

        # Use HW Crypto Chip (ATECC608) to obtain private key.
        jwt_inst = ecc608_jwt_with_hw_alg()
        return jwt_inst.encode(token, None, algorithm=algorithm)
