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

## Configuring the Voice HAT driver

To use the Voice HAT, your kernel needs to be 4.9 or later. This is available
on Raspbian 2017-07-05 and later. You'll also need to configure ALSA:

``` shell
sudo scripts/configure-driver.sh
sudo scripts/install-alsa-config.sh
sudo reboot
```

## Get cloud credentials

To access the cloud services you need to register a project and generate
credentials for cloud APIs. This is documented in the
[setup instructions](https://aiyprojects.withgoogle.com/voice#users-guide-1-1--connect-to-google-cloud-platform) on the
webpage.

## Making code changes

If you edit the code on a different computer, you can deploy it to your
Raspberry Pi by running:

``` shell
make deploy
```

## Running automatically

You can find sample scripts in the `src` directory showing how to use the
Assistant SDK.

To execute any of these scripts on the Raspberry Pi, login to it and run
(replacing the filename with the script you want to run):

``` shell
cd ~/voice-recognizer-raspi
source env/bin/activate
python3 src/assistant_library_demo.py
```

If you want the voice recognizer service to run automatically when the Pi
boots, you need to have a file in the `src` directory named `main.py`. You can
make a copy of one of the sample scripts and rename it. Then run this command:

``` shell
sudo systemctl enable voice-recognizer.service
```
