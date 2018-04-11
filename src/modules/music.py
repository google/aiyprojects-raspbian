import configparser
import logging
import time
import feedparser
import threading

from mpd import MPDClient, MPDError, CommandError

import aiy.audio
import aiy.voicehat

class Music(object):

    """Interacts with MPD"""

    def __init__(self, configpath):
        self._cancelAction = False
        self.configPath = configpath
        self._confirmPlayback = False
        self._podcastURL = None
        self._podcasts = {}
        self._mpd = MPDClient(use_unicode=True)

    def run(self, module, voice_command):
        self.resetVariables()
        self._mpd.connect("localhost", 6600)

        if module == 'music':
            if voice_command == 'stop':
                self._mpd.stop()
                self._mpd.clear()

            elif voice_command == 'resume' or voice_command == 'play':
                self._mpd.pause(0)

            elif voice_command == 'pause':
                self._mpd.pause(1)

        elif module == 'radio':
            self.playRadio(voice_command)

        elif module == 'podcast':
            self.playPodcast(voice_command)

        if self._cancelAction == False:
            time.sleep(1)
            button = aiy.voicehat.get_button()
            button.on_press(self._buttonPressCancel)

            # Keep alive until the user cancels music with button press
            while self._mpd.status()['state'] != "stop":
                if self._cancelAction == True:
                    logging.info('stopping Music by button press')
                    self._mpd.stop()
                    self._podcastURL = None
                    break

                time.sleep(0.1)
            button.on_press(None)
            logging.info('Music stopped playing')
            self._mpd.clear()

        self._mpd.close()
        self._mpd.disconnect()

    def playRadio(self, station):
        config = configparser.ConfigParser()
        config.read(self.configPath)

        stations = config['radio']

        if station == 'list':
            logging.info('Enumerating radio stations')
            aiy.audio.say('Available stations are')
            for key in stations:
                aiy.audio.say(key)
            return

        elif station not in stations:
            logging.info('Station not found: ' + station)
            aiy.audio.say('radio station ' + station + ' not found')
            return

        logging.info('streaming ' + station)
        aiy.audio.say('tuning the radio to ' + station)

        self._cancelAction = False

        self._mpd.clear()
        self._mpd.add(stations[station])
        self._mpd.play()

    def playPodcast(self, podcast):

        config = configparser.ConfigParser()
        config.read(self.configPath)
        podcasts = config['podcasts']

        offset = 0

        if self._confirmPlayback == True:
            self._confirmPlayback = False

        else:
            if podcast == 'list':
                logging.info('Enumerating Podcasts')
                aiy.audio.say('Available podcasts are')
                for key in podcasts:
                    aiy.audio.say(key)
                return

            elif podcast == 'recent':
                aiy.audio.say('Recent podcasts are')
                for title,url in podcasts.items():
                    podcastInfo = self.getPodcastItem(podcast, url, offset)
                    aiy.audio.say(title + ' uploaded an episode ' + str(int(podcastInfo['age']/24)) + ' days ago')
                return

            elif podcast == 'today':
                aiy.audio.say('Today\'s podcasts are')
                for title,url in podcasts.items():
                    podcastInfo = self.getPodcastItem(podcast, url, offset)
                    if podcastInfo['age'] < 36:
                        aiy.audio.say(title + ' uploaded an episode ' + str(int(podcastInfo['age'])) + ' hours ago')
                return

            elif podcast.startswith('previous '):
                offset = 1
                podcast = podcast[9:]

            if podcast not in podcasts:
                logging.info('Podcast not found: ' + podcast)
                aiy.audio.say('Podcast ' + podcast + ' not found')
                return

            podcastInfo = self.getPodcastItem(podcast, podcasts[podcast], offset)
            if podcastInfo == None:
                logging.info('Podcast failed to load')
                return
            logging.info('Podcast Title: ' + podcastInfo['title'])
            logging.info('Episode Title: ' + podcastInfo['ep_title'])
            logging.info('Episode URL: ' + podcastInfo['url'])
            logging.info('Episode Date: ' + podcastInfo['published'])
            logging.info('Podcast Age: ' + str(podcastInfo['age']) + ' hours')

            aiy.audio.say('Playing episode of ' + podcastInfo['title'] + ' titled ' + podcastInfo['ep_title'])

            self._podcastURL = podcastInfo['url']

            if (podcastInfo['age'] > 336):
                aiy.audio.say('This episode is ' + str(int(podcastInfo['age']/24)) + ' days old. Do you still want to play it?')
                self._confirmPlayback = True
                return None

        self._cancelAction = False

        self._mpd.clear()
        self._mpd.add(self._podcastURL)
        self._mpd.play()

        self._podcastURL = None

    def getPodcastItem(self, podcast, src, offset):
        result = {
            'url':None,
            'title':None,
            'ep_title':None,
            'age':0,
            'published':None
        }

        logging.info('loading ' + src + ' podcast feed')
        rss = feedparser.parse(src)

        # get the total number of entries returned
        resCount = len(rss.entries)
        logging.info('feed contains ' + str(resCount) + ' items')

        # exit out if empty
        if resCount < offset:
            logging.info(podcast + ' podcast feed is empty')
            aiy.audio.say('There are no episodes available of ' + podcast)
            return None

        if 'title' in rss.feed:
            result['title'] = rss.feed.title

        rssItem = rss.entries[offset]

        # Extract infromation about requested item

        if 'title' in rssItem:
            result['ep_title'] = rssItem.title

        if 'published_parsed' in rssItem:
            result['age'] = int((time.time() - time.mktime(rssItem['published_parsed'])) / 3600)

        if 'published' in rssItem:
            result['published'] = rssItem.published

        if 'enclosures' in rssItem:
            result['url'] = rssItem.enclosures[0]['href']

        elif 'media_content' in rssItem:
            result['url'] = rssItem.media_content[0]['url']

        else:
            logging.info(podcast + ' feed format is unknown')
            aiy.audio.say('The feed for ' + podcast + ' is unknown format')
            return None

        return result

    def _buttonPressCancel(self):
        self._cancelAction = True

    def getConfirmPlayback(self):
        return self._confirmPlayback

    def setConfirmPlayback(self, confirmPlayback):
        self._confirmPlayback = confirmPlayback == True

    def getPodcastURL(self):
        return self._podcastURL

    def setPodcastURL(self, podcastURL):
        self._podcastURL = podcastURL

    def resetVariables(self):
        self._cancelAction = False

    def _syncPodcasts(self):
        logging.info('Starting Podcast sync')
        config = configparser.ConfigParser()
        config.read(self.configPath)
        podcasts = config['podcasts']

		for title,url in podcasts.items():
            self._podcasts[podcast] = self.getPodcastItem(podcast, url, 0)
