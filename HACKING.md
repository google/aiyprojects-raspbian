# Setting up the image

We recommend using [the images](https://aiyprojects.withgoogle.com/voice) we
provide. Those images are based on [Raspbian](https://www.raspberrypi.org/downloads/raspbian/),
with a few customizations and are tested on the Raspberry Pi 3.

If you prefer to set up Raspbian yourself, add a source for `stretch`, the
testing version of Raspbian:
``` shell
echo "deb http://archive.raspbian.org/raspbian/ stretch main" | sudo tee /etc/apt/sources.list.d/stretch.list >/dev/null
echo 'APT::Default-Release "jessie";' | sudo tee /etc/apt/apt.conf.d/default-release >/dev/null
sudo apt-get update
sudo apt-get upgrade
sudo rpi-update
sudo reboot
```

Next install the project dependencies and setup services and the ALSA
configuration for the VoiceHAT hardware:
``` shell
cd ~/voice-recognizer-raspi
scripts/install-deps.sh
scripts/install-services.sh
scripts/install-alsa-config.sh
```

## Get service credentials

To access the cloud services you need to register a project and generate
credentials for cloud APIs. This is documented in the
[setup instructions](https://aiyprojects.withgoogle.com/voice) on the
webpage.

# Making code changes

If you edit the code on a different computer, you can deploy it to your
Raspberry Pi by running:

``` shell
make deploy
```
To execute the script on the Raspberry Pi run, login to it and run:
``` shell
cd ~/voice-recognizer-raspi
source env/bin/activate
python3 src/main.py
```

# I18N

Strings wrapped with `_()` are marked for translation.

``` shell
# update catalog after string changed
pygettext3 -d voice-recognizer -p po src/main.py src/action.py

# add new language
msgmerge po/de.po po/voice-recognizer.pot
# now edit po/de.po

# update language
msgmerge -U po/de.po po/voice-recognizer.pot
# now edit po/de.po

# create language bundle
mkdir po/de/LC_MESSAGES/
msgfmt po/de.po -o po/de/LC_MESSAGES/voice-recognizer.mo
```
