# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A simple melodic music player for the piezo buzzer.

This API is designed for the Vision Kit, but has no dependency on the Vision
Bonnet, so may be used without it. It only requires a piezo buzzer connected to
:any:`aiy.pins.BUZZER_GPIO_PIN`.
"""

import re
import time

from ._buzzer import PWMController


class Rest:
    """Simple internal class to represent a musical rest note.

    Used in part with the TonePlayer class, this object represents a period of
    time in a song where no sound is made. End users shouldn't have to care
    about this too much and instead focus on the music language described in the
    TonePlayer class.
    """

    WHOLE = 1
    HALF = 2
    QUARTER = 4
    EIGHTH = 8
    SIXTEENTH = 16

    def __init__(self, bpm=120, period=QUARTER):
        self.bpm = bpm
        self.period = period

    def to_length_secs(self):
        """Converts from musical notation to a period of time in seconds."""
        return (self.bpm / 60.0) / self.period


class Note(Rest):
    """Simple internal class to represent a musical note.

    Used in part with the TonePlayer class, this object represents a musical
    note, including its name, octave, and how long it is played. End users
    shouldn't have to care about this too much and instead focus on the music
    language described in the TonePlayer class."""

    BASE_OCTAVE = 4

    def __init__(self, name, octave=BASE_OCTAVE, bpm=120, period=Rest.QUARTER):
        super(Note, self).__init__(bpm, period)
        self.name = name
        self.octave = octave

    def to_frequency(self, tuning=440.0):
        """Converts from a name and octave to a frequency in Hz.

        Uses the specified tuning.

        Args:
            tuning: the frequency of the natural A note, in Hz.
        """

        NOTES = 'CcDdEFfGgAaB'
        base = NOTES.find('A')

        octave_delta = self.octave - Note.BASE_OCTAVE   # 0
        octave_halfsteps = octave_delta * 12            # 0
        offset = NOTES.find(self.name) - base           # -1
        halfsteps = octave_halfsteps + offset           # -2
        freq = tuning * (1.059463 ** halfsteps)

        return freq

    def __str__(self):
        return self.name + str(self.octave)


class TonePlayer:
    """Class to play a simplified music notation via a PWMController.

    This class makes use of a very simple music notation to play simple musical
    tones out of a PWM controlled piezo buzzer.

    The language consists of notes and rests listed in an array. Rests are
    moments in the song when no sound is produced, and are written in this way:

        r<length>

    The <length> may be one of the following five characters, or omitted:

        w: whole note
        h: half note
        q: quarter note (the default -- if you don't specify the length, we
        assume quarter)
        e: eighth note
        s: sixteenth note

    So a half note rest would be written as "rh". A quarter note rest could be
    written as "r" or "rq".

    Notes are similar to rests, but take the following form:

        <note_name><octave><length>

    <note_names> are written using the upper and lower case letters A-G and a-g.
    Uppercase letters are the natural notes, whereas lowercase letters are
    shifted up one semitone (sharp). Represented on a piano keyboard, the
    lowercase letters are the black keys. Thus, 'C' is the natural note C, whereas
    'c' is actually C#, the first black key to the right of the C key.

    The octave is optional, but is the numbers 1-8. If omitted, the TonePlayer
    assumes octave 4. Like the rests, the <length> may also be omitted and uses
    the same notation as the rest <length> parameter. If omitted, TonePlayer
    assumes a length of one quarter.

    With this in mind, a middle C whole note could be written "C3w". Likewise, a
    C# quarter note in the 4th octave could be written as "c" or "c4q" or "cq".
    """

    REST_RE = re.compile(r"r(?P<length>[whqes])?")
    NOTE_RE = re.compile(r"(?P<name>[A-Ga-g])(?P<octave>[1-8])?(?P<length>[whqes])?")

    PERIOD_MAP = {
        'w': Rest.WHOLE,
        'h': Rest.HALF,
        'q': Rest.QUARTER,
        'e': Rest.EIGHTH,
        's': Rest.SIXTEENTH
    }

    def __init__(self, gpio, bpm=120, debug=False):
        """Initializes the TonePlayer for playing on a given GPIO pin with the
        given tempo in beats per minute.

        Args:
            gpio: the GPIO to initialize for PWM output to a piezo buzzer.
            bpm: the tempo of the song to play in beats per minute. Defaults to
                 120bpm (each whole note takes 1 second to play).
        """
        self.gpio = gpio
        self.bpm = bpm
        self.debug = debug

    def _parse(self, array):
        """Helper method to parse an array of notes into Notes and Rests."""
        return [self._parse_note(x) for x in array]

    def _parse_note(self, note_str):
        """Parses a single note/rest string into its given class instance."""
        result = TonePlayer.REST_RE.match(note_str)
        if result is not None:
            length = TonePlayer.PERIOD_MAP[result.group('length')]
            return Rest(self.bpm, length)

        result = TonePlayer.NOTE_RE.match(note_str)
        if result is not None:
            name = result.group('name')

            octave = 4
            if result.group('octave') is not None:
                octave = int(result.group('octave'))
                if octave > 8:
                    octave = 8
                if octave < 1:
                    octave = 1

            length = Rest.QUARTER
            if result.group('length') is not None:
                length = TonePlayer.PERIOD_MAP[result.group('length')]

            return Note(name, octave, self.bpm, length)

        raise Exception("Couldn't parse '" + str(note_str) + "'")

    def play(self, *args):
        """Plays a sequence of notes out the piezo buzzer."""
        parsed_notes = self._parse(args)
        with PWMController(self.gpio) as controller:
            for note in parsed_notes:
                if isinstance(note, Note):
                    if self.debug:
                        print(note.name + str(note.octave),
                              '(' + str(note.to_frequency()) + ')',
                              str(note.to_length_secs()) + 's')
                    controller.set_frequency(note.to_frequency())
                else:
                    controller.set_frequency(0)
                time.sleep(note.to_length_secs())
