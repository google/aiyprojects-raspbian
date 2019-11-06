# System updates

We periodically update the SD card image that supports both the Vision Kit and
Voice Kit. Each release is based on [Raspbian][raspbian], with a few
customizations, and they are tested on various Raspberry Pi models.

You can flash the latest system image for your kit as follows:

1. Download the latest `.img.xz` file from the [releases page on GitHub][github-releases]. (For release details, see the [Change log][changelog].)
1. Use an adapter to connect your MicroSD card to your computer.
1. Use a program such as [balenaEtcher](https://www.balena.io/etcher/) to flash the `.img.xy` file onto your MicroSD card. (balenaEtcher is free and works on Windows, Mac OS, and Linux.)

When flashing is done, put the MicroSD card back in your kit and you're good to go!

If you prefer to update an existing Raspbian image yourself, follow the steps below.

## AIY Debian Package Repo

Add AIY package repo:
```
echo "deb https://packages.cloud.google.com/apt aiyprojects-stable main" | tee /etc/apt/sources.list.d/aiyprojects.list
```

Add Google package keys from https://www.google.com/linuxrepositories/:
```
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
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

## AIY Debian Packages

### Vision and Voice Bonnets

* `aiy-dkms` contains MCU drivers:

  * `aiy-io-i2c` &mdash; firmware update support
  * `pwm-aiy-io` &mdash; [PWM][kernel-pwm] sysfs interface
  * `gpio-aiy-io` &mdash; [GPIO][kernel-gpio] sysfs interface
  * `aiy-adc`  &mdash; [Industrial I/O][kernel-iio] ADC interface

* `aiy-io-mcu-firmware` contains MCU firmware update service
* `leds-ktd202x-dkms` contains `leds-ktd202x` LED driver
* `pwm-soft-dkms` contains `pwm-soft` software PWM driver

* `aiy-python-wheels` contains optimized `protobuf` python
wheel (until [this issue][protobuf-issue] is fixed) along with [Google Assistant Library][assistant-library] for different Raspberry Pi boards.

### Vision Bonnet

* `aiy-vision-dkms` contains `aiy-vision` Myriad driver
* `aiy-vision-firmware` contains Myriad firmware
* `aiy-models` contains [models][aiy-models] for on-device inference:

  * Face Detection
  * Object Detection
  * Image Classification
  * Dish Detection
  * Dish Classification
  * iNaturalist Classification (plants, insects, birds)

### Voice Bonnet

* `aiy-voicebonnet-soundcard-dkms` contains sound drivers:

  * `rl6231`
  * `rt5645`
  * `snd_aiy_voicebonnet`

## AIY Setup

### Vision Bonnet (minimal)

Install drivers:
```bash
sudo apt-get install -y aiy-vision-dkms
```

Install package with [models][aiy-models]:
```bash
sudo apt-get install -y aiy-models
```

Install optimized `protobuf` library for better performance:
```bash
sudo apt-get install -y aiy-python-wheels
```

Reboot:
```bash
sudo reboot
```
and verify that `dmesg` output contains `Myriad ready` message:
```bash
dmesg | grep -i "Myriad ready"
```

### Voice Bonnet (minimal)

Install drivers:
```bash
sudo apt-get install -y aiy-voicebonnet-soundcard-dkms aiy-dkms
```

Install PulseAudio:
```bash
sudo apt-get install -y pulseaudio
sudo mkdir -p /etc/pulse/daemon.conf.d/
echo "default-sample-rate = 48000" | sudo tee /etc/pulse/daemon.conf.d/aiy.conf
```

Install optimized `protobuf` and `google-assistant-library`:
```bash
sudo apt-get install -y aiy-python-wheels
```

Reboot:
```bash
sudo reboot
```
and verify that you can record
```bash
arecord -f cd test.wav
```
and play a sound:
```bash
aplay test.wav
```

### Vision and Voice Bonnet (additional)

Install LED driver to control button RGB LED:
```bash
sudo apt-get install -y leds-ktd202x-dkms
```

Install software PWM driver to control buzzer:
```bash
sudo apt-get install -y pwm-soft-dkms
```

Reboot:
```bash
sudo reboot
```

## Python Library

### Installation

Make sure you already installed `aiy-python-wheels`:
```bash
sudo apt-get install -y aiy-python-wheels
```

Install `git` first:
```bash
sudo apt-get install -y git
```

Then clone `aiyprojects-raspbian` repo from GitHub:
```bash
git clone https://github.com/google/aiyprojects-raspbian.git AIY-projects-python
```

And install library in editable mode:
```bash
sudo pip3 install -e AIY-projects-python/src
```

### Cloud access for Voice HAT or Voice Bonnet

To access the cloud services you need to register a project and generate
credentials for cloud APIs. This is documented in the
[setup instructions][aiy-voice-setup] on the webpage.

[changelog]: CHANGES.html
[raspbian]: https://www.raspberrypi.org/downloads/raspbian/
[image-flash]: https://www.raspberrypi.org/documentation/installation/installing-images/
[aiy-models]: https://aiyprojects.withgoogle.com/models/
[github-releases]: https://github.com/google/aiyprojects-raspbian/releases
[aiy-voice-setup]: https://aiyprojects.withgoogle.com/voice#google-assistant--get-credentials
[assistant-library]: https://pypi.org/project/google-assistant-library/
[protobuf-issue]: https://github.com/bennuttall/piwheels/issues/97
[kernel-pwm]: https://www.kernel.org/doc/Documentation/pwm.txt
[kernel-gpio]: https://www.kernel.org/doc/Documentation/gpio/sysfs.txt
[kernel-iio]: https://www.kernel.org/doc/Documentation/driver-api/iio/core.rst
