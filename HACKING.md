# Setting up the image

## Overview

We recommend using [the latest image][github-releases] we provide. Those images
are based on [Raspbian][raspbian], with a few customizations and are tested on
the different Raspberry Pi models. If you prefer to setup Raspbian yourself,
there are some manual steps you need to take.

## AIY Package Repo

Add AIY package repo:
```
echo "deb https://dl.google.com/aiyprojects/deb stable main" | sudo tee -a /etc/apt/sources.list.d/aiyprojects.list
```

Add Google package keys from https://www.google.com/linuxrepositories/:
```
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
```

Update and install the latest system updates (including kernel):
```
sudo apt-get update
sudo apt-get upgrade
```

Reboot after update:
```
sudo reboot
```

## AIY Packages

Package `aiy-dkms` contains MCU and Myriad drivers:

* `aiy-io-i2c`
* `pwm-aiy-io`
* `gpio-aiy-io`
* `aiy-adc`
* `aiy-vision`

Package `aiy-vision-firmware` contains Myriad firmware for Vision Bonnet.

Package `aiy-io-mcu-firmware` contains MCU firmware update service.

Package `leds-ktd202x-dkms` contains LED driver:

* `leds-ktd202x`

Package `pwm-soft-dkms` contains Software PWM driver:

* `pwm-soft`

Package `aiy-voicebonnet-soundcard-dkms` contains sound drivers:

* `rl6231`
* `rt5645`
* `snd_aiy_voicebonnet`

Package `aiy-voicebonnet-routes` contains ALSA UCM files for Voice Bonnet.

Package `aiy-models` contains [models][aiy-models] for Vision Bonnet.

### Vision Bonnet Minimal Setup

```
sudo apt-get install aiy-dkms
sudo reboot
```

Run `dmesg` and check it contains `Myriad ready` message.

In additional you can install package with [models][aiy-models]:

```
sudo apt-get install aiy-models
```

### Voice Bonnet Minimal Setup

```
sudo apt-get install pulseaudio
mkdir -p ~/.config/pulse/
echo "default-sample-rate = 48000" > ~/.config/pulse/daemon.conf
```

```
sudo apt-get install aiy-dkms aiy-voicebonnet-soundcard-dkms aiy-voicebonnet-routes
sudo reboot
```

You should be able to record
```
arecord -f cd test.wav
```
and play
```
aplay test.wav
```
sound right now.

### Vision/Voice Bonnet Additional Setup

Install LED driver to control button RGB LED:
```
sudo apt-get install leds-ktd202x-dkms
```

Install Software PWM driver to control buzzer:
```
sudo apt-get install pwm-soft-dkms
echo "pwm-soft" | sudo tee -a /etc/modules
sudo modprobe pwm-soft
```

## Python Library

### Installation

Install `git` first:
```
sudo apt-get install git
```

Then clone `aiyprojects-raspbian` repo from GitHub:
```
git clone https://github.com/google/aiyprojects-raspbian.git AIY-projects-python
```

And install library in editable mode:
```
sudo pip3 install -e AIY-projects-python/src
```

### Cloud access for Voice HAT or Voice Bonnet

To access the cloud services you need to register a project and generate
credentials for cloud APIs. This is documented in the
[setup instructions](https://aiyprojects.withgoogle.com/voice#google-assistant--get-credentials) on the
webpage.

[raspbian]: https://www.raspberrypi.org/downloads/raspbian/
[aiy-models]: https://aiyprojects.withgoogle.com/models/
[github-releases]: https://github.com/google/aiyprojects-raspbian/releases