import configparser
import logging

from kodijson import Kodi, PLAYER_VIDEO

from aiy.voice import tts

# KodiRemote: Send command to Kodi
# ================================
#

class KodiRemote(object):

    """Sends a command to a kodi client machine"""

    def __init__(self, configPath):
        self.configPath = configPath
        self.kodi = None
        self.action = None
        self.request = None

    def run(self, voice_command):
        config = configparser.ConfigParser()
        config.read(self.configPath)
        settings = config['kodi']

        number_mapping = [ ('9 ', 'nine ') ]

        if self.kodi is None:
            logging.info('No current connection to a Kodi client')

        for key in settings:
            if key not in ['username','password']:
                if voice_command.startswith(key):
                    voice_command = voice_command[(len(key)+1):]
                    self.kodi = Kodi('http://' + settings[key] + '/jsonrpc', kodiUsername, kodiPassword)
                elif self.kodi is None:
                    self.kodi = Kodi('http://' + settings[key] + '/jsonrpc', kodiUsername, kodiPassword)

        try:
            self.kodi.JSONRPC.Ping()
        except:
            tts.say('Unable to connect to client')
            return

        if voice_command.startswith('tv '):
            result = self.kodi.PVR.GetChannels(channelgroupid='alltv')
            channels = result['result']['channels']
            if len(channels) == 0:
                tts.say('No channels found')

            elif voice_command == 'tv channels':
                tts.say('Available channels are')
                for channel in channels:
                    tts.say(channel['label'])

            else:
                for k, v in number_mapping:
                    voice_command = voice_command.replace(k, v)

                channel = [item for item in channels if (str(item['label']).lower() == voice_command[3:])]
                if len(channel) == 1:
                    self.kodi.Player.Open(item={'channelid':int(channel[0]['channelid'])})

                else:
                    logging.info('No channel match found for ' + voice_command[3:] + '(' + str(len(channel)) + ')')
                    tts.say('No channel match found for ' + voice_command[3:])
                    tts.say('Say Kodi t v channels for a list of available channels')

        elif voice_command.startswith('play unwatched ') or voice_command.startswith('play tv series '):
            voice_command = voice_command[15:]
            result = self.kodi.VideoLibrary.GetTVShows(sort={'method':'dateadded','order':'descending'},filter={'field':'title','operator': 'contains', 'value': voice_command}, properties=['playcount','sorttitle','dateadded','episode','watchedepisodes'])
            if 'tvshows' in result['result']:
                if len(result['result']['tvshows']) > 0:
                    result = self.kodi.VideoLibrary.GetEpisodes(tvshowid=result['result']['tvshows'][0]['tvshowid'], sort={'method':'episode','order':'ascending'},filter={'field':'playcount','operator': 'lessthan', 'value': '1'},properties=['episode','playcount'],limits={'end': 1})
                    if 'episodes' in result['result']:
                        if len(result['result']['episodes']) > 0:
                            self.kodi.Player.Open(item={'episodeid':result['result']['episodes'][0]['episodeid']})

                        else:
                            tts.say('No new episodes of ' + voice_command + ' available')
                            logging.info('No new episodes of ' + voice_command + ' available')

                    else:
                        tts.say('No new episodes of ' + voice_command + ' available')
                        logging.info('No new episodes of ' + voice_command + ' available')

            else:
                tts.say('No tv show found titled ' + voice_command)
                logging.info('No tv show found')

        elif voice_command.startswith('play recording '):
            voice_command = voice_command[15:]
            result = self.kodi.PVR.GetRecordings(properties=["starttime"])
            if 'recordings' in result['result']:
                if len(result['result']['recordings']) > 0:
                    recordings = sorted([recording for recording in result["result"]["recordings"] if recording["label"].lower() == voice_command], key = lambda x : x["starttime"], reverse=True)
                    if len(recordings) > 0:
                        self.kodi.Player.Open(item={'recordingid':int(recordings[0]["recordingid"])})
                else:
                    tts.say('No recording titled ' + voice_command)
                    logging.info('No recording found')
            else:
                tts.say('No recordings found')
                logging.info('No PVR recordings found')

        elif voice_command == 'stop':
            result = self.kodi.Player.Stop(playerid=1)
            logging.info('Kodi response: ' + str(result))

        elif voice_command == 'play' or voice_command == 'pause' or voice_command == 'paws' or voice_command == 'resume':
            result = self.kodi.Player.PlayPause(playerid=1)
            logging.info('Kodi response: ' + str(result))

        elif voice_command == 'update tv shows':
            self.kodi.VideoLibrary.Scan()

        elif voice_command == 'shutdown' or voice_command == 'shut down':
            self.kodi.System.Shutdown()

        else:
            tts.say('Unrecognised Kodi command')
            logging.warning('Unrecognised Kodi request: ' + voice_command)
            return
