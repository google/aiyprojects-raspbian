import configparser
import feedparser
import logging
import threading
import time

import aiy.audio

class ReadRssFeed(object):

    """Reads out headline and summary from items in an RSS feed."""

    #######################################################################################
    # constructor
    # configPath - the config file containing the feed details
    #######################################################################################

    def __init__(self, configPath):
        self._cancelAction = False
        self.configPath = configPath
        self.feedCount = 10
        self.properties = ['title', 'description']
        self.count = 0

    def run(self, voice_command):
        self.resetVariables()

        config = configparser.ConfigParser()
        config.read(self.configPath)
        sources = config['headlines']

        if voice_command == 'list':
            logging.info('Enumerating news sources')
            aiy.audio.say('Available sources are')
            for key in sources:
                aiy.audio.say(key)
            return

        elif voice_command not in sources:
            logging.info('RSS feed source not found: ' + voice_command)
            aiy.audio.say('source ' + voice_command + ' not found')
            return

        res = self.getNewsFeed(sources[voice_command])

        # If res is empty then let user know
        if res == '':
            if aiy.audio.say is not None:
                aiy.audio.say('Cannot get the feed')
            logging.info('Cannot get the feed')
            return

        button = aiy.voicehat.get_button()
        button.on_press(self._buttonPressCancel)

        # This thread handles the speech
        threadSpeech = threading.Thread(target=self.processSpeech, args=[res])
        threadSpeech.daemon = True
        threadSpeech.start()

        # Keep alive until the user cancels speech with button press or all records are read out
        while not self._cancelAction:
            time.sleep(0.1)

        button.on_press(None)

    def getNewsFeed(self, url):
        # parse the feed and get the result in res
        res = feedparser.parse(url)

        # get the total number of entries returned
        resCount = len(res.entries)

        # exit out if empty
        if resCount == 0:
            return ''

        # if the resCount is less than the feedCount specified cap the feedCount to the resCount
        if resCount < self.feedCount:
            self.feedCount = resCount

        # create empty array
        resultList = []

        # loop from 0 to feedCount so we append the right number of entries to the return list
        for x in range(0, self.feedCount):
            resultList.append(res.entries[x])

        return resultList

    def resetVariables(self):
        self._cancelAction = False
        self.feedCount = 10
        self.count = 0

    def processSpeech(self, res):
        # check in various places of speech thread to see if we should terminate out of speech
        if not self._cancelAction:
            for item in res:
                speakMessage = ''

                if self._cancelAction:
                    logging.info('Cancel Speech detected')
                    break

                for property in self.properties:
                    if property in item:
                        if not speakMessage:
                            speakMessage = self.stripSpecialCharacters(item[property])
                        else:
                            speakMessage = speakMessage + ', ' + self.stripSpecialCharacters(item[property])

                if self._cancelAction:
                    logging.info('Cancel Speech detected')
                    break

                if speakMessage != '':
                    # get item number that is being read so you can put it at the front of the message
                    logging.info('Msg: ' + speakMessage)
                    # mock the time it takes to speak the text (only needed when not using pi to actually speak)
                    # time.sleep(2)

                if aiy.audio.say is not None:
                    aiy.audio.say(speakMessage)

                if self._cancelAction:
                    logging.info('Cancel Speech detected')
                    break

            # all records read, so allow exit
            self._cancelAction = True

        else:
            logging.info('Cancel Speech detected')

    def stripSpecialCharacters(self, inputValue):
        return inputValue.replace('<br/>', '\n').replace('<br>', '\n').replace('<br />', '\n')

    def _buttonPressCancel(self):
        self._cancelAction = True

    def resetVariables(self):
        self._cancelAction = False
