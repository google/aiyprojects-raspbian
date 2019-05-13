# Google Assistant and Cloud Speech Examples

To fully experience the interactions, you need an **LED** (+resistor) and a
**button**. The LED is for conveying the machine's "state of mind". The button
is to trigger the machine to listen, for cases where you don't want it to be
bothered by noises. Not all examples require a button.

I suggest you try the examples in the following order:

1. **assistant_library_demo.py**

    **Required credential file:** `/home/pi/assistant.json`

    **LED:** short end to ground, long end to GPIO 17

    **Run:** `python3 assistant_library_demo.py`

    **Usage:** Say "OK, Google", ask it a question, then listen to its responses.
    Notice how the LED changes.

2. **assistant_library_with_local_commands_demo.py**

    **Required credential file:** `/home/pi/assistant.json`

    **LED:** short end to ground, long end to GPIO 17

    **Run:** `python3 assistant_library_with_local_commands_demo.py`

    **Usage:** Say "OK, Google", converse as before, or say one of these commands:

    - "Power off": supposed to shutdown the pi, but I have commented out the
      actual shutdown system call

    - "Reboot": supposed to reboot the pi, but I have commented out the actual
      reboot system call

    - "IP address": tells the internal IP address

    These commands use the `aiy.voice.tts` module (which in turn uses the Pico
    text-to-speech engine) to generate verbal responses. You can obviously hear
    the difference.

    `sudo apt-get install libttspico-utils` to install Pico if you haven't done
    so already.

3. **assistant_grpc_demo.py**

    **Required credential file:** `/home/pi/assistant.json`

    **LED:** short end to ground, long end to GPIO 17

    **Button:** one end to ground, one end to GPIO 27

    **Run:** `python3 assistant_grpc_demo.py --language en-US`. If you don't
    supply the language, it assumes the Pi's default language, which may not be
    supported.

    **Usage:** Press the button before speaking. Ask some questions.

4. **cloudspeech_demo.py**

    This one uses Google Cloud Speech, only able to recognize speech, but
    provide no verbal response.

    **Required credential file:** `/home/pi/cloud_speech.json`

    **LED:** short end to ground, long end to GPIO 17

    **Run:** `python3 cloudspeech_demo.py`

    **Usage:** Say something to see it translate, or say one of the commands and
    notice how the LED changes:

    - "Turn on the light"

    - "Turn off the light"

    - "Blink the light"

    Say "Goodbye" to exit.
