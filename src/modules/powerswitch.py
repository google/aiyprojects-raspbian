import configparser
import logging

import aiy.audio

from modules.mqtt import Mosquitto

# PowerSwitch: Send HTTP command to RF switch website
# ================================
#

class PowerSwitch(object):

    """ Control power sockets"""

    def __init__(self, configPath, remotePath):
        self.remotePath = remotePath
        self.mqtt = Mosquitto(configPath)

    def run(self, voice_command):
        self.config = configparser.ConfigParser()
        self.config.read(self.remotePath)
        self.devices = self.config.sections()

        devices = None
        action = None

        if voice_command == 'list':
            logging.info('Enumerating switchable devices')
            aiy.audio.say('Available switches are')
            for device in self.devices:
                if device != 'GPIO':
                    aiy.audio.say(str(device))
            return

        elif voice_command.startswith('on '):
            action = 'on'
            devices = voice_command[3:].split(' and ')

        elif voice_command.startswith('off '):
            action = 'off'
            devices = voice_command[4:].split(' and ')

        else:
            aiy.audio.say('Unrecognised command')
            logging.info('Unrecognised command: ' + device)
            return

        if action is not None:
            for device in devices:
               logging.info('Processing switch request for ' + device)
               self.processCommand(device, action)

    def processCommand(self, device, action):
        if device.startswith('the '):

            device = device[4:]

        if device in self.devices:

            code = int(self.config[device].get('code'))

            if action == 'off':
               code = code - 8;

            logging.info('Code to send: ' + str(code))

            self.mqtt.command('/rf-power/code', code)

        else:
            aiy.audio.say('Unrecognised switch')
            logging.info('Unrecognised device: ' + device)

