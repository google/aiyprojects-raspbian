import configparser
import os
import logging
import time
import feedparser
import threading
import sqlite3

from mpd import MPDClient, MPDError, CommandError, ConnectionError

from aiy.voice import tts
from aiy.voice import tts
# from gpiozero import Button
# from aiy.pins import BUTTON_GPIO_PIN
from aiy.board import Board

class PodCatcher(threading.Thread):
    def __init__(self, configpath):
        """ Define variables used by object
        """
        threading.Thread.__init__(self)
        self.configPath = configpath
        self.dbpath = '/run/user/%d/podcasts.sqlite' % os.getuid()

    def _connectDB(self):
        try:
            conn = sqlite3.connect(self.dbpath)
            conn.cursor().execute('''
                CREATE TABLE IF NOT EXISTS podcasts (
                    podcast TEXT NOT NULL,
                    title TEXT NOT NULL,
                    ep_title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    timestamp INT NOT NULL);''')
            conn.row_factory = sqlite3.Row
            return conn

        except Error as e:
            print(e)

        return None

    def syncPodcasts(self, filter=None):
        config = configparser.ConfigParser()
        config.read(self.configPath)
        podcasts = config['podcasts']

        conn = self._connectDB()
        cursor = conn.cursor()

        logging.info('Start updating podcast data')
        for podcastID,url in podcasts.items():
            if filter is not None and not podcastID == filter:
                continue

            logging.info('loading ' + podcastID + ' podcast feed')

            rss = feedparser.parse(url)

            # get the total number of entries returned
            resCount = len(rss.entries)
            logging.info('feed contains ' + str(resCount) + ' items')

            # exit out if empty
            if not resCount > 0:
                logging.warning(podcastID + ' podcast feed is empty')
                continue

            for rssItem in rss.entries:
                result = {
                    'podcast':podcastID,
                    'url':None,
                    'title':None,
                    'ep_title':None,
                    'timestamp':0
                }

                if 'title' in rss.feed:
                    result['title'] = rss.feed.title

                # Abstract information about requested item

                if 'title' in rssItem:
                    result['ep_title'] = rssItem.title

                if 'published_parsed' in rssItem:
                    result['timestamp'] = time.mktime(rssItem['published_parsed'])

                if 'enclosures' in rssItem and len(rssItem.enclosures) > 0:
                    result['url'] = rssItem.enclosures[0]['href']

                elif 'media_content' in rssItem and len(rssItem.media_content) > 0:
                    result['url'] = rssItem.media_content[0]['url']

                else:
                    logging.warning('The feed for "' + podcastID + '" is in an unknown format')
                    continue

                cursor.execute('''REPLACE INTO podcasts(podcast, title, ep_title, url, timestamp)
                    VALUES(?, ?, ?, ?, ?)''', (result['podcast'], result['title'], result['ep_title'], result['url'], result['timestamp']))

                """ Detect existance of episode and skip remaining content
                """
                if cursor.rowcount == 0:
                    break

        conn.commit()
        logging.info('Finished updating podcast data')

    def getPodcastInfo(self, podcastID=None, offset=0):
        if podcastID is None:
            return None

        logging.info('Searching for information about "' + str(podcastID) + '" podcast')

        cursor = self._connectDB().cursor()
        if podcastID in ['today', 'today\'s']:
            logging.info("SELECT podcast, url, title, ep_title, (strftime('%s','now') - strftime('%s', datetime(timestamp, 'unixepoch', 'localtime')))/3600 as age FROM podcasts WHERE age < 25 ORDER BY timestamp DESC")
            cursor.execute("SELECT podcast, url, title, ep_title, (strftime('%s','now') - strftime('%s', datetime(timestamp, 'unixepoch', 'localtime')))/3600 as age FROM podcasts WHERE age < 25 ORDER BY timestamp DESC")
        elif podcastID == 'yesterday':
            logging.info("SELECT podcast, url, title, ep_title, (strftime('%s','now') - strftime('%s', datetime(timestamp, 'unixepoch', 'localtime')))/3600 as age FROM podcasts WHERE age < 49 AND age > 24 ORDER BY timestamp DESC")
            cursor.execute("SELECT podcast, url, title, ep_title, (strftime('%s','now') - strftime('%s', datetime(timestamp, 'unixepoch', 'localtime')))/3600 as age FROM podcasts WHERE age < 49 AND age > 24 ORDER BY timestamp DESC")
        else:
            logging.info("SELECT url, title, ep_title, (strftime('%s','now') - strftime('%s', datetime(timestamp, 'unixepoch', 'localtime')))/3600 as age FROM podcasts WHERE podcast LIKE ? ORDER BY timestamp DESC LIMIT ?,1")
            cursor.execute("SELECT url, title, ep_title, (strftime('%s','now') - strftime('%s', datetime(timestamp, 'unixepoch', 'localtime')))/3600 as age FROM podcasts WHERE podcast LIKE ? ORDER BY timestamp DESC LIMIT ?,1", (podcastID,offset,))
        result = cursor.fetchall()

        logging.info('Found "' + str(len(result)) + '" podcasts')

        return result

    def run(self):
        while True:
            self.syncPodcasts()
            time.sleep(1680)

class Music(object):

    """Interacts with MPD"""

    def __init__(self, configpath):
        self.configPath = configpath
        self._confirmPlayback = False
        self._podcastURL = None
        self.mpd = MPDClient(use_unicode=True)

    def command(self, module, voice_command, podcatcher=None):
        self.mpd.connect("localhost", 6600)

        if module == 'music':
            if voice_command == 'stop':
                self.mpd.stop()
                self.mpd.clear()

            elif voice_command == 'resume' or voice_command == 'play':
                self.mpd.pause(0)

            elif voice_command == 'pause':
                self.mpd.pause(1)

        elif module == 'radio':
            self.playRadio(voice_command)

        elif module == 'podcast':
            self.playPodcast(voice_command, podcatcher)

        logging.info('checking MPD status')

        time.sleep(1)

        logging.info('checking MPD status')

        if self.mpd.status()['state'] != "stop":
            logging.info('Initialising thread to monitor for button press')
            cancel = threading.Event()
            logging.info('Attaching Button object to GPIO')
            self._board = Board()
            logging.info('Attaching thread to Button object')
            self._board.button.when_pressed = cancel.set

            # Keep alive until the user cancels music with button press
            while self.mpd.status()['state'] != "stop":
                if cancel.is_set():
                    logging.info('stopping Music by button press')
                    self.mpd.stop()
                    self._podcastURL = None
                    break

                time.sleep(0.1)
            self._board.button.when_pressed = None
            logging.info('Music stopped playing')
            self.mpd.clear()

        try:
            self.mpd.close()
            self.mpd.disconnect()
        except ConnectionError:
            logging.warning('MPD connection timed out')
            pass

    def playRadio(self, station):
        config = configparser.ConfigParser()
        config.read(self.configPath)

        stations = config['radio']

        if station == 'list':
            logging.info('Enumerating radio stations')
            tts.say('Available stations are')
            for key in stations:
                tts.say(key)
            return

        elif station not in stations:
            logging.info('Station not found: ' + station)
            tts.say('radio station ' + station + ' not found')
            return

        logging.info('streaming ' + station)
        tts.say('tuning the radio to ' + station)

        self._cancelAction = False

        self.mpd.clear()
        self.mpd.add(stations[station])
        self.mpd.play()

    def playPodcast(self, podcastID, podcatcher=None):
        config = configparser.ConfigParser()
        config.read(self.configPath)
        podcasts = config['podcasts']
        logging.info('playPodcast "' + podcastID + "'")

        offset = 0
        if podcatcher is None:
            logging.warning('playPodcast missing podcatcher object')
            return

        if self._confirmPlayback == True:
            self._confirmPlayback = False

        else:
            if podcastID == 'list':
                logging.info('Enumerating Podcasts')
                tts.say('Available podcasts are')
                for key in podcasts:
                    tts.say('' + key)
                return

            elif podcastID in ['recent','today','today\'s','yesterday']:
                podcasts = podcatcher.getPodcastInfo(podcastID, offset)

                if len(podcasts) == 0:
                    tts.say('No podcasts available')
                    return 

                tts.say('Available podcasts are')
                logging.info('Initialising thread to monitor for button press')
                cancel = threading.Event()
                logging.info('Attaching Button object to GPIO')
                self._board = Board()
                logging.info('Attaching thread to Button object')
                self._board.button.when_pressed = cancel.set

                for podcast in podcatcher.getPodcastInfo(podcastID, offset):
                    if cancel.is_set():
                        break
                    elif podcast['age'] < 49:
                        tts.say('' + podcast['podcast'] + ' uploaded an episode ' + str(int(podcast['age'])) + ' hours ago')
                    else:
                        tts.say('' + podcast['podcast'] + ' uploaded an episode ' + str(int(podcast['age']/24)) + ' days ago')

                self._board.button.when_pressed = None
                return

            elif podcastID.startswith('previous '):
                offset = 1
                podcastID = podcastID[9:]

            if podcastID not in podcasts:
                logging.info('Podcast not found: ' + podcastID)
                tts.say('Podcast ' + podcastID + ' not found')
                return

            podcastInfo = podcatcher.getPodcastInfo(podcastID, offset)
            if len(podcastInfo) == 0:
                return

            if podcastInfo == None:
                logging.warning('Podcast data for "' + podcast + '" failed to load')
                return
            logging.info('Podcast Title: ' + podcastInfo[0]['title'])
            logging.info('Episode Title: ' + podcastInfo[0]['ep_title'])
            logging.info('Episode URL: ' + podcastInfo[0]['url'])
            logging.info('Episode Age: ' + str(podcastInfo[0]['age']) + ' hours')

            tts.say('Playing episode of ' + podcastInfo[0]['title'] + ' titled ' + podcastInfo[0]['ep_title'])
            if (podcastInfo[0]['age'] > 336):
                tts.say('This episode is ' + str(int(podcastInfo[0]['age']/24)) + ' days old. Do you still want to play it?')
                self._confirmPlayback = True
                return None

            self._podcastURL = podcastInfo[0]['url']

        if self._podcastURL is None:
            return None

        try:
            self.mpd.clear()
            self.mpd.add(self._podcastURL)
            self.mpd.play()
        except ConnectionError as e:
            tts.say('Error connecting to MPD service')

        self._podcastURL = None

    def getConfirmPlayback(self):
        return self._confirmPlayback

    def setConfirmPlayback(self, confirmPlayback):
        self._confirmPlayback = confirmPlayback == True

    def getPodcastURL(self):
        return self._podcastURL

    def setPodcastURL(self, podcastURL):
        self._podcastURL = podcastURL
