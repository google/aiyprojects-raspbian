import configparser
import logging
import time

import paho.mqtt.publish as publish

class Mosquitto(object):

    """Publish MQTT"""

    def __init__(self, configpath):
        self.configPath = configpath
        config = configparser.ConfigParser()
        config.read(self.configPath)

        self.mqtt_host = config['mqtt'].get('host')
        self.mqtt_port = config['mqtt'].getint('port', 1883)
        self.mqtt_username = config['mqtt'].get('username')
        self.mqtt_password = config['mqtt'].get('password')

    def command(self, topic=None, message=None):
        config = configparser.ConfigParser()
        config.read(self.configPath)

        try: 
            publish.single(topic, payload=message,
                           hostname=self.mqtt_host,
                           port=self.mqtt_port,
                           auth={'username':self.mqtt_username,
                           'password':self.mqtt_password})
        except:
            logging.error("Error sending MQTT message")
            pass

    def resetVariables(self):
        self._cancelAction = False
