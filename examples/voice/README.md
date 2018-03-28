# Google Assistant and Cloud Speech Examples

To fully experience the interactions, you need an **LED** (+resistor) and a
**button**. The LED is for conveying the machine's "state of mind". The button
is to trigger the machine to listen, for cases where you don't want it to be
bothered by noises. Not all examples require a button.

I suggest you try the examples in the following order:

1. **assistant_library_demo.py**

    **Required credential file:** `/home/pi/assistant.json`

    **LED:** short end to ground, long end to GPIO 25

    **Usage:** Say "OK, Google", ask it a question, then listen to its sometimes
    hilarious responses. Notice how the LED changes.

2. **assistant_library_with_local_commands_demo.py**

    **Required credential file:** `/home/pi/assistant.json`

    **LED:** short end to ground, long end to GPIO 25

    **Usage:** Say "OK, Google", converse as before, or say one of these commands:

    - "power off": supposed to shutdown the pi, but I have commented out the
      actual shutdown system call

    - "reboot": supposed to reboot the pi, but I have commented out the actual
      reboot system call

    - "ip address": tells the internal IP address

    These commands use the `aiy.audio` module (which in turn uses the Pico
    text-to-speech engine) to generate the verbal responses. You can obviously
    hear the difference.

3. **assistant_grpc_demo.py**

    **Required credential file:** `/home/pi/assistant.json`

    **LED:** short end to ground, long end to GPIO 25

    **Button:** one end to ground, one end to GPIO 23

    **Usage:** Press the button before speaking. Ask some questions. Say
    "Goodbye" to exit.

4. **cloudspeech_demo.py**

    This one uses Google Cloud Speech, only able to recognize speech, but
    provide no verbal response.

    **Required credential file:** `/home/pi/cloud_speech.json`

    **LED:** short end to ground, long end to GPIO 25

    **Button:** one end to ground, one end to GPIO 23

    **Usage:** Press the button, say one of the commands and notice the LED
    changes:

    - "turn on the light"

    - "turn off the light"

    - "blink"

    Say "Goodbye" to exit.

## Utility modules

There are `aiy.util.LED` and `aiy.util.Button`. You should be able to glance
their basic usages from the examples. I encourage you to read the source code to
learn more. They are not that complicated.

And then there is the module `aiy.audio`. It allows you to say a sentence,
record a wav file, and play a file. Some usages are as follows:

```
aiy.audio.say('Whatever you want to say')
aiy.audio.record_to_wave('path/to/sound.wav', 5)
aiy.audio.play_wave('path/to/sound.wav')
aiy.audio.play_audio(open('path/to/sound.raw', 'rb').read())
```
