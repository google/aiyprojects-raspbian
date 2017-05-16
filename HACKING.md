# Setting up the image

We recommend using [the images](https://aiyprojects.withgoogle.com/voice) we
provide. Those images are based on [Raspbian](https://www.raspberrypi.org/downloads/raspbian/),
with a few customizations and are tested on the Raspberry Pi 3. If you prefer
to setup Raspbian yourself, there are some manual steps you need to take.

## Installing the dependencies

First, make sure you have `git` installed and clone this repository in
`~/voice-recognizer-raspi`:

```shell
sudo apt-get install git
cd
git clone https://github.com/google/aiyprojects-raspbian.git voice-recognizer-raspi
```

Then, install the project dependencies and setup the services:

``` shell
cd ~/voice-recognizer-raspi
scripts/install-deps.sh
sudo scripts/install-services.sh
```

## Installing the Voice HAT driver and config

To use the Voice HAT, you'll need to upgrade your kernel to 4.9, then adjust the
kernel and ALSA configuration:

``` shell
sudo apt-get update
sudo apt-get install raspberrypi-kernel
sudo scripts/configure-driver.sh
sudo scripts/install-alsa-config.sh
sudo reboot
```

## Get cloud credentials

To access the cloud services you need to register a project and generate
credentials for cloud APIs. This is documented in the
[setup instructions](https://aiyprojects.withgoogle.com/voice#users-guide-1-1--connect-to-google-cloud-platform) on the
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

Strings wrapped with `_()` are marked for translation:

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
