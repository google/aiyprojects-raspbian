import configparser
import logging

import aiy.audio
import requests
import json

from modules.mqtt import Mosquitto

# PowerSwitch: Send MQTT command to control remote devices
# ================================
#

class PowerSwitch(object):

    """ Control power sockets"""

    def __init__(self, configPath, remotePath):
        self.configPath = configPath
        self.remotePath = remotePath
        self.mqtt = Mosquitto(configPath)

    def run(self, voice_command):

        try:
            if self.remotePath.startswith("http"):
                logging.warning('Loading remote device list')
                response = requests.get(self.remotePath)
                self.config = json.loads(response.text.lower())

            else:
                logging.warning('Loading local device list')
                self.config = json.loads(open(self.remotePath).read())

        except:
            logging.warning('Failed to load remote device list')
            return

        self.devices = self.config["remotes"]

        devices = None
        action = None

        if voice_command == 'list':
            logging.info('Enumerating switchable devices')
            aiy.audio.say('Available switches are')
            for device in self.devices:
                aiy.audio.say(device["names"][0])
            return

        elif voice_command.startswith('on '):
            action = 'on'
            devices = voice_command[3:].split(' and ')

        elif voice_command.startswith('off '):
            action = 'off'
            devices = voice_command[4:].split(' and ')

        elif voice_command.startswith('up '):
            action = 'up'
            devices = voice_command[3:].split(' and ')

        elif voice_command.startswith('down '):
            action = 'down'
            devices = voice_command[5:].split(' and ')

        else:
            aiy.audio.say('Unrecognised command')
            logging.warning('Unrecognised command: ' + device)
            return

        if action is not None:
            for device in devices:
               logging.info('Processing switch request for ' + device)
               self.processCommand(device, action)

    def processCommand(self, device, action):

        config = configparser.ConfigParser()
        config.read(self.configPath)

        if device.startswith('the '):
            device = device[4:]

        for deviceobj in self.devices:

            if device in deviceobj["names"]:

                logging.info('Device found: ' + device)

                if action in deviceobj["codes"]:
                    logging.info('Code found for "' + action + '" action')
                    self.mqtt.command(config["mqtt"].get("power_topic","power/code"), deviceobj["codes"][action])
                else:
                    aiy.audio.say(device + ' does not support command ' + action)
                    logging.warning('Device "' + device + '" does not support command: ' + action)

                return

            logging.info('Device not matched')

        aiy.audio.say('Unrecognised switch')
        logging.warning('Unrecognised device: ' + device)

