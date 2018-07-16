import logging
import time

import aiy.audio
import aiy.voicehat

class PowerCommand(object):

    def __init__(self):
        self._cancelAction = False

    def run(self, voice_command):
        self.resetVariables()

        if voice_command == 'shutdown':
            button = aiy.voicehat.get_button()
            button.on_press(self._buttonPressCancel)
    
            p = subprocess.Popen(['/usr/bin/aplay',os.path.expanduser('~/.config/self-destruct.wav')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    
            while p.poll() == None:
                if self._cancelAction == True:
                    logging.info('shutdown cancelled by button press')
                    p.kill()
                    return
                    break
    
                time.sleep(0.1)
    
            time.sleep(1)
            button.on_press(None)
            logging.info('shutdown would have just happened')
            subprocess.call('sudo shutdown now', shell=True)
    
        elif voice_command == 'reboot':
            aiy.audio.say('Rebooting')
            subprocess.call('sudo shutdown -r now', shell=True)

    def _buttonPressCancel(self):
        self._cancelAction = True

    def resetVariables(self):
        self._cancelAction = False
