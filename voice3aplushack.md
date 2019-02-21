https://github.com/google/aiyprojects-raspbian/issues/568#issuecomment-466014958

11-16-18 AIY image is the latest image, and the only image late enough to support the new 3A+ released also in November 2018. Unfortunately that particular image, I've encounter many audio playback issues, some microphone issues also. There would be no sound which I suspect has something to do with pulseaudio that was introduced with August 2018 AIY image. The most recent AIY image that worked as expected was 4-13-18, but unfortunately does not support futureware 3A+. 3A+ would not boot unless with November 2018 the latest AIY image.

Therefore I experimented by downloading the most recent Raspbian image from raspberrypi.org 11-13-18 to ensure that 3A+ would boot. From there I followed the hacking.md guide from google/aiy-raspbian to proceed to add setup AIY voice with src files from 4-13-18 the version that did not include pulseaudio and worked fine. Along with minor changes to configuration files as you will see.

My experiment worked. 3A+ was able to boot, play audio from the v1 voice hat.

I suspect pulseaudio to be the culprit. Additionally, the script folder with install-alsa and install-services with asound.conf seem to disappear from the most recent image. These were found in the 4-13-18 AIY image src/scripts.

Happy hacking!


I have figured out how to get 3A+ to work with voicehat v1. Install latest Raspbian 11-13-18 on your own from raspberrypi.org.

Then follow a bit of the instructions from https://github.com/google/aiyprojects-raspbian/blob/aiyprojects/HACKING.md starting with:

`To update your system image, download the latest .img.xz file from our releases page. Once downloaded, write the image to your SD card, and you're good to go!`

**DO NOT FLASH WITH IMAGE**
simply go to the [release page](https://github.com/google/aiyprojects-raspbian/releases) to 4-13-18 and download the zip or tar.

Follow these steps

AIY Debian Package Repo
Add AIY package repo:

`echo "deb https://dl.google.com/aiyprojects/deb stable main" | sudo tee /etc/apt/sources.list.d/aiyprojects.list`
Add Google package keys from https://www.google.com/linuxrepositories/:

`wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -`
if the above doesn't work. download the key.pub file separately then `sudo apt-key add linux_signing_key.pub`

Update and install the latest system updates (including kernel):

`` sudo apt-get update ``sudo apt-get upgrade ``Reboot after update:

`sudo reboot `
unzip or tar the aiyprojects-raspbian-20180413.zip,tar then move into it
`cd aiyprojects-raspbian-20180413/scripts/`
then run the scripts in the following order:
`install-alsa-config.sh`
`install-services.sh`

change the boot file and comment out everything existing
`sudo nano /boot/config.txt`
add the following

```
dtoverlay=dwc2
start_x=1
gpu_mem=128
dtoverlay=googlevoicehat-soundcard
```
reboot and audio should work on 3A+ and v1 voicehat. cheers let me know if you have any issues.
