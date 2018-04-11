import configparser
import logging
import urllib.request

import aiy.audio

from rpi_rf import RFDevice

# PowerSwitch: Send HTTP command to RF switch website
# ================================
#

class PowerSwitch(object):

    """ Control power sockets"""

    def __init__(self, configPath):
        self.configPath = configPath

    def run(self, voice_command):
        self.config = configparser.ConfigParser()
        self.config.read(self.configPath)
        self.devices = self.config.sections()

        devices = None
        action = None

        if 'GPIO' not in self.config:
            aiy.audio.say('No G P I O settings found')
            logging.info('No GPIO settings found')
            return

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

        if (action is not None):
            for device in devices:
               logging.info('Processing switch request for ' + device)
               self.processCommand(device, action)

    def processCommand(self, device, action):
        if device in self.devices:

            code = int(self.config[device].get('code'))

            if (int(self.config['GPIO'].get('output', -1)) > 0):
                if (self.config[device].get('toggle', False)):
                    logging.info('Power switch is a toggle')

                elif action == 'off':
                   code = code - 8;

                logging.info('Code to send: ' + str(code))

                rfdevice = RFDevice(int(self.config['GPIO'].get('output', -1)))
                rfdevice.enable_tx()
                rfdevice.tx_code(code, 1, 380)
                rfdevice.cleanup()

            elif (self.config['GPIO'].get('url', False)):
                url = self.config['GPIO'].get('url', False)
                logging.info('URL to send request: ' + str(url) + '?code=' + str(code) + '&action=' + action)
                logging.info('Code to send via URL: ' + str(code))
                with urllib.request.urlopen(str(url) + '?code=' + str(code) + '&action=' + action) as response:
                    html = response.read()

            else:
                aiy.audio.say('G P I O settings invalid')
                logging.info('No valid GPIO settings found')

        else:
            aiy.audio.say('Unrecognised switch')
            logging.info('Unrecognised device: ' + device)
