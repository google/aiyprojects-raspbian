# AIY Voice Only

[Google AIY Voice Kit](https://aiyprojects.withgoogle.com/voice) is a cool
project.  The unfortunate thing is it locks you into its custom hardware. I have
separated its software to work on Raspberry Pi (3B and 3B+) independently,
just using a normal speaker and microphone.

The following instructions aim at:

**Raspberry Pi (3B, 3B+)**  
**Raspbian Stretch**  
**Python 3**

Additionally, you need:

- a **Speaker** to plug into Raspberry Pi's headphone jack
- a **USB Microphone**

**Plug them in.** Let's go.

## Find your speaker and mic

Locate your speaker in the list of playback hardware devices. Normally, it is at
**card 0, device 0**, as indicated by the sample output below.

```
$ aplay -l

**** List of PLAYBACK Hardware Devices ****
card 0: ALSA [bcm2835 ALSA], device 0: bcm2835 ALSA [bcm2835 ALSA]
  Subdevices: 8/8
  Subdevice #0: subdevice #0
  Subdevice #1: subdevice #1
  Subdevice #2: subdevice #2
  Subdevice #3: subdevice #3
  Subdevice #4: subdevice #4
  Subdevice #5: subdevice #5
  Subdevice #6: subdevice #6
  Subdevice #7: subdevice #7
card 0: ALSA [bcm2835 ALSA], device 1: bcm2835 ALSA [bcm2835 IEC958/HDMI]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

Locate your USB microphone in the list of capture hardware devices. Normally, it
is at **card 1, device 0**, as indicated by the sample output below.

```
$ arecord -l

**** List of CAPTURE Hardware Devices ****
card 1: Device [USB PnP Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

*Your hardware's number might be different from mine. Adapt accordingly.*

## Make them the defaults

Create a new file named `.asoundrc` in the home directory (`/home/pi`). Put in
the following contents, replacing `<card number>` and `<device number>` with the
appropriate numbers.

```
pcm.!default {
  type asym
  capture.pcm "mic"
  playback.pcm "speaker"
}
pcm.mic {
  type plug
  slave {
    pcm "hw:<card number>,<device number>"
  }
}
pcm.speaker {
  type plug
  slave {
    pcm "hw:<card number>,<device number>"
  }
}
```

For example, if your mic is at **card 1, device 0**, that block should look
like:

```
pcm.mic {
  type plug
  slave {
    pcm "hw:1,0"
  }
}
```

If your speaker is at **card 0, device 0**, that block should look like:

```
pcm.speaker {
  type plug
  slave {
    pcm "hw:0,0"
  }
}
```

## Make sure sound output to headphone jack

Sound may be output via HDMI or headphone jack. We want to use the headphone
jack.

Enter `sudo raspi-config`. Select **Advanced Options**, then **Audio**. You are
presented with three options:

- `Auto` should work
- `Force 3.5mm (headphone) jack` should definitely work
- `Force HDMI` won't work

## Turn up the volume

A lot of times when sound applications seem to fail, it is because we forget to
turn up the volume.

Volume adjustment can be done with `alsamixer`. This program makes use of some
function keys (`F1`, `F2`, etc). For function keys to function properly on
PuTTY, we need to change some settings (click on the top-left corner of the
PuTTY window, then select **Change Settings ...**):

1. Go to **Terminal** / **Keyboard**
2. Look for section **The Function keys and keypad**
3. Select **Xterm R6**
4. Press button **Apply**

Now, we are ready to turn up the volume, for both the speaker and the mic:

```
$ alsamixer
```
`F6` to select between sound cards  
`F3` to select playback volume (for speaker)  
`F4` to select capture volume (for mic)  
`⬆` `⬇` arrow keys to adjust  
`Esc` to exit

*If you unplug the USB microphone at any moment, all volume settings
(including that of the speaker) may be reset. Make sure to check the volume
again.*

Hardware all set, let's test them.

## Test the speaker

```
$ speaker-test -t wav
```

Press `Ctrl-C` when done.

## Record a WAV file

```
$ arecord --format=S16_LE --duration=5 --rate=16000 --file-type=wav out.wav
```

## Play a WAV file

```
$ aplay out.wav
```

## Register for Google Assistant or Google Cloud Speech

Although we are not using Google's hardware, there is no escaping from its
software. We still rely on Google Assistant or Google Cloud Speech API to
perform voice recognition. To use these cloud services, you have to go through a
series of registration steps:

- [Configure Google Assistant API](https://developers.google.com/assistant/sdk/guides/library/python/embed/config-dev-project-and-account)
- [Configure Google Cloud Speech API](https://aiyprojects.withgoogle.com/voice#makers-guide-3-1--change-to-the-cloud-speech-api)

Which one to use depends on what you need. **Google Assistant** can recognize
speech *and* talk back intelligently, but supports fewer languages. **Google
Cloud Speech** only recognizes speech (no talk-back), but supports far more
languages.

Usage of these APIs changes constantly. Here is a summary of the steps for using
**Google Assistant**, as of 2019-02-13:

1. Create a Project

2. Enable Google Assistant API

3. Configure OAuth consent screen (must fill in **Support email** and
   **Application Homepage link**)

4. Enable activity controls

5. Register device model, Download credentials file (check `project_id`)

6. Install system dependencies:
    ```
    $ sudo apt-get install portaudio19-dev libffi-dev libssl-dev libmpg123-dev
    ```

7. Install Python packages:
    ```
    $ sudo pip3 install google-assistant-library==1.0.0 \
                        google-assistant-sdk[samples]==0.5.1 \
                        google-auth-oauthlib[tool] \
                        google-cloud-speech
    ```

8. Use `google-oauthlib-tool` to authenticate once

9. Use [`googlesamples-assistant-devicetool`](https://developers.google.com/assistant/sdk/reference/device-registration/device-tool)
   to register your Raspberry Pi. A few useful commands may be:
   ```
   $ googlesamples-assistant-devicetool --project-id <Project ID> register-device \
   --model <Model ID> \
   --device <Make up a new Device ID> \
   --client-type LIBRARY

   $ googlesamples-assistant-devicetool --project-id <Project ID> list --model

   $ googlesamples-assistant-devicetool --project-id <Project ID> list --device
   ```

## How to use this library

I used to have it uploaded to PYPI for easy installation. But Google Assistant
is changing too rapidly. I find it more informing to download and try to
integrate it manually:

1. Download the `aiy` directory

2. Set environment variable `PYTHONPATH` so Python can find the `aiy` package

3. You may have to install the Pico text-to-speech engine, `libttspico-utils`,
   to allow it to generate speech dynamically

The best way to experience the software is to try it.
**[Let's go to the examples.](https://github.com/nickoala/aiy-voice-only/tree/aiyprojects/examples/voice)**

## Changes to original library

Here is an outline of the changes I have made to the original [AIY Voice
Kit](https://github.com/google/aiyprojects-raspbian) source code:

1. No Vision stuff: The AIY project actually includes the [Vision
Kit](https://aiyprojects.withgoogle.com/vision) and associated software, which
are of no concern to this project. I have removed those.

2. No Voice Hat stuff: This project does not rely on the Voice Hat.

3. Expose LED and Button: There are, nonetheless, some useful underlying utility
classes. I have exposed them in the `aiy.util` module.

4. Allow using custom credentials file path.
