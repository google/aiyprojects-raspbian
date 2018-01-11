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

"""Tracker-based music player for the piezo buzzer."""


import math
import re
import time

from aiy._drivers._buzzer import PWMController
from aiy.toneplayer import Note


class Command(object):
    """Base class for all commands."""

    def apply(self, player, controller, note, tick_delta):
        """Applies the effect of this command."""
        pass

    @classmethod
    def parse(klass, *args):
        """Parses the arguments to this command into a new command instance.

        Returns:
          A tuple of an instance of this class and how many arguments were
          consumed from the argument list.
        """
        pass


class Glissando(Command):
    """Pitchbends a note up or down by the given rate."""

    def __init__(self, direction, hz_per_tick):
        self.direction = direction
        self.hz_per_tick = hz_per_tick

    def apply(self, player, controller, note, tick_delta):
        frequency = controller.frequency_hz()
        controller.set_frequency(frequency + (self.hz_per_tick * tick_delta * self.direction))

    def __str__(self):
        return 'glis(dir=%d, hz_per_tick=%d)' % (self.direction, self.hz_per_tick)

    @classmethod
    def parse(klass, *args):
        direction = int(args[0])
        hz_per_tick = int(args[1])
        return klass(direction, hz_per_tick), 2


class PulseChange(Command):
    """Changes the pulse width of a note up or down by the given rate."""

    def __init__(self, direction, usec_per_tick):
        self.direction = direction
        self.usec_per_tick = usec_per_tick

    def apply(self, player, controller, note, tick_delta):
        pulse = controller.pulse_usec()
        controller.set_pulse_usec(pulse + (self.usec_per_tick * tick_delta * self.direction))

    def __str__(self):
        return 'puls(dir=%d, usec_per_tick=%d)' % (self.direction, self.usec_per_tick)

    @classmethod
    def parse(klass, *args):
        direction = int(args[0])
        usec_per_tick = int(args[1])
        return klass(direction, usec_per_tick), 2


class SetPulseWidth(Command):
    """Changes the pulse width of a note up or down by the given rate."""

    def __init__(self, pulse_width_usec):
        self.pulse = pulse_width_usec

    def apply(self, player, controller, note, tick_delta):
        controller.set_pulse_usec(self.pulse)

    def __str__(self):
        return 'spwd(pulse=' + str(self.pulse) + ')'

    @classmethod
    def parse(klass, *args):
        pulse_width_usec = int(args[0])
        return klass(pulse_width_usec), 1


class Arpeggio(Command):
    """Plays an arpeggiated chord."""

    def __init__(self, *args):
        self.chord = args

    def apply(self, player, controller, note, tick_delta):
        note_number = tick_delta % (len(self.chord) + 1)
        if note_number == 0:
            controller.set_frequency(note.to_frequency())
        else:
            chord_note = self.chord[note_number - 1]
            controller.set_frequency(chord_note.to_frequency())

    def __str__(self):
        return 'arpg(chord=' + ', '.join([str(x) for x in self.chord]) + ')'

    @classmethod
    def parse(klass, *args):
        chord = []
        for arg in args:
            if len(arg) > 2:
                break
            chord.append(Note(arg[0], octave=int(arg[1])))

        return klass(*chord), len(chord)


class Vibrato(Command):
    """Vibrates the frequency by the given amount."""

    def __init__(self, depth_hz, speed):
        self.depth_hz = depth_hz
        self.speed = speed

    def apply(self, player, controller, note, tick_delta):
        freq_delta = round(math.sin(tick_delta * (1 / self.speed)))
        freq = note.to_frequency()
        freq += freq_delta * self.depth_hz
        controller.set_frequency(int(freq))

    def __str__(self):
        return 'vibr(depth=%d, speed=%d)' % (self.depth_hz, self.speed)

    @classmethod
    def parse(klass, *args):
        depth_hz = int(args[0])
        speed = int(args[1])
        return klass(depth_hz, speed), 2


class Retrigger(Command):
    """Retriggers a note a consecutive number of times."""

    def __init__(self, times):
        self.times = times

    def apply(self, player, controller, note, tick_delta):
        if tick_delta > self.times * 2:
            return
        elif tick_delta % 2 == 0:
            controller.set_frequency(0)
        else:
            controller.set_frequency(note.to_frequency())

    def __str__(self):
        return 'retg(times=' + str(self.times) + ')'

    @classmethod
    def parse(klass, *args):
        times = int(args[0])
        return klass(times), 1


class NoteOff(Command):
    """Stops a given note from playing."""

    def apply(self, player, controller, note, tick_delta):
        if tick_delta == 0:
            controller.set_frequency(0)

    def __str__(self):
        return 'noff'

    @classmethod
    def parse(klass, *args):
        return klass(), 0


class SetSpeed(Command):
    """Changes the speed of the given song."""

    def __init__(self, speed):
        self.speed = speed

    def apply(self, player, controller, note, tick_delta):
        if tick_delta == 0:
            controller.set_speed(self.speed)

    def __str__(self):
        return 'sspd(speed=' + str(self.speed) + ')'

    @classmethod
    def parse(klass, *args):
        speed = int(args[0])
        return klass(speed), 1


class JumpToPosition(Command):
    """Jumps to the given position in a song."""

    def __init__(self, position):
        self.position = position

    def apply(self, player, controller, note, tick_delta):
        if tick_delta == 0:
            controller.set_position(self.position)

    def __str__(self):
        return 'jump(pos=' + str(self.position) + ')'

    @classmethod
    def parse(klass, *args):
        position = int(args[0])
        return klass(position), 1


class StopPlaying(Command):
    """Stops the TrackPlayer from playing."""

    def apply(self, player, controller, note, tick_delta):
        if tick_delta == 0:
            controller.set_frequency(0)
            player.stop()

    def __str__(self):
        return 'stop'

    @classmethod
    def parse(klass, *args):
        return klass(), 0


class TrackPlayer(object):
    """Plays a tracker-like song."""

    def __init__(self, gpio, speed=3, debug=False):
        """Constructs a new TrackPlayer.

        Args:
          gpio: integer. The GPIO to use for PWM output.
          speed: integer. How many ticks per row to play.
          debug: boolean. Defaults to False. Whether or not to output debug
          information such as the status bar.
        """
        self.gpio = gpio
        self.initial_speed = speed
        self.tick = 0
        self.debug = debug
        self.patterns = []
        self.order = []
        self.playing = False

    def add_pattern(self, pattern):
        """Adds a new pattern to the player.

        Returns:
          The new pattern index.
        """
        self.patterns.append(pattern)
        if self.debug:
            print('Added new pattern %d' % (len(self.patterns) - 1))
        return len(self.patterns) - 1

    def add_order(self, pattern_number):
        """Adds a pattern index to the order."""
        if self.debug:
            print('Adding order[%d] == %d' % (len(self.order), pattern_number))
        self.order.append(pattern_number)

    def set_order(self, position, pattern_number):
        """Changes a pattern index in the order."""
        if self.debug:
            print('Setting order[%d] == %d' % (position, pattern_number))
        self.order[position] = pattern_number

    def set_speed(self, new_speed):
        """Sets the playing speed in ticks/row."""
        if self.debug:
            print('Setting speed to %d' % (new_speed))
        self.speed = new_speed

    def set_position(self, new_position):
        """Sets the position inside of the current pattern."""
        if self.debug:
            print('Jumping position to %d' % (new_position))
        self.current_position = new_Position

    def stop(self):
        """Stops playing any currently playing track."""
        self.playing = False

    def play(self):
        """Plays the currently configured track."""
        self.tick = 0
        self.set_speed(self.initial_speed)
        self.current_order = 0
        self.playing = True

        with PWMController(self.gpio) as controller:
            while self.playing:
                if self.current_order >= len(self.order):
                    self.current_order = 0

                self.current_pattern = self.order[self.current_order]
                self.current_position = 0

                pattern = self.patterns[self.current_pattern]
                last_note = None

                while self.current_position < len(pattern):
                    row = pattern[self.current_position]
                    last_command = None

                    for t in range(self.speed):
                        for note_command in row:
                            if isinstance(note_command, Note) and t == 0:
                                last_note = note_command
                                controller.set_frequency(note_command.to_frequency())

                            if isinstance(note_command, Command):
                                last_command = note_command
                                note_command.apply(self, controller, last_note, t)
                                if self.playing:
                                    print()
                                    return

                        self.tick += 1
                        time.sleep(0.01)

                    if self.debug:
                        print(' ' * 70 + '\r', end='')
                        print('pos: %03d  pattern: %02d' %
                              (self.current_position, self.current_pattern), end='')
                        if last_note is not None:
                            print('  note: %s' % (str(last_note)), end='')
                        else:
                            print('          ', end='')
                        if last_command is not None:
                            print('  command: %s' % (str(last_command)), end='')

                    self.current_position += 1

                self.current_order += 1

            controller.set_frequency(0)


class TrackLoader(object):
    """Simple track module loader.

    This class, given a filename and a gpio will load and parse in the given
    track file and initialize a TrackPlayer instance to play it.

    The format of a track file is a plain text file consisting of a header,
    followed by a number of pattern definitions. Whitespace is ignored in the
    header and between the patterns.

    The header may contain a set of key value pairs like so:

      title Some arbitrary song name
      speed <speed>
      order <number> [<number>...]
      end

    "title" specifies the title of the song. Optional. This isn't actually used
    by the player, but is a nice bit of metadata for humans.

    "speed" sets the speed in ticks/row. Optional. The argument, <speed> must be
    an int. If this isn't present, the player defaults to a speed of 3.

    "order" sets the order of the patterns. It is a single line of
    space separated integers, starting at 0. Each integer refers to the pattern
    in order in the file. This keyword must be present.

    The keyword "end", which ends the header.

    Patterns take the form:

      pattern
      [E5] [cmnd [<arg>...] ...]
      end

    Patterns are started with the "pattern" keyword and end with the "end"
    keyword. Blank lines inside a pattern are significant -- they add time to
    the song. Any notes that were played continue to play unless they were
    stopped.

    Each row of a pattern consists of a note followed by any number of commands
    and arguments. A note consists of an upper or lowercase letter A-G
    (lowercase are sharp notes) and an octave number between 1 and 8. Any time a
    note appears, it will play only on the first tick, augmented by any commands
    on the same row. Notes are optional per row.

    Commands are four letter lowercase words whose effect is applied every tick.
    A row may contain nothing but commands, if need be. If the current speed is
    3, that means each effect will occur 3 times per row. There may be any
    number of commands followed by arguments on the same row. Commands available
    as of this writing are as follows:

        glis <direction> <amount-per-tick>
        puls <direction> <amount-per-tick>
        spwd <width>
        arpg [<note>...]
        vibr <depth> <speed>
        retg <times>
        noff
        sspd <speed>
        jump <position>
        stop

    glis is a glissando effect, which takes in a <direction> (a positive or
    negative number) as a direction to go in terms of frequency shift. The
    <amount-per-tick> value is an integer that is how much of a shift in Hz to
    apply in the given direction every tick.

    puls changes the pulse width of the current PWM waveform in the given
    <direction> by the <amount-per-tick> in microseconds. <direction> is like
    <direction> to the glis command.

    spwd sets the pulse width of the current PWM waveform directly. <width> is
    the width of the pulse in microseconds.

    arpg performs an arpeggio using the currently playing note and any number of
    notes listed as arguments. Each note is played sequentially, starting with
    the currently playing note, every tick. Note that to continue the arpeggio,
    it will be necessary to list multiple arpg commands in sequence.

    vibr performs a vibrato using the currently playing note. The vibrato is
    applied using the given <depth> in Hz, and the given <speed>.

    retg retriggers the note every tick the given number of <times>. This allows
    for very fast momentary effects when combined with glis, puls, and arpg and
    high speed values.

    noff stops any previously playing note.

    sspd sets the current playing speed in <speed> ticks per row.

    jump jumps to the given row <position> (offset from the start of the
    pattern) and continues playing.

    stop stops the Player from playing.
    """

    NOTE_RE = re.compile(r'(?P<name>[A-Ga-g])(?P<octave>[1-8])')
    COMMAND_RE = re.compile(r'(?P<name>[a-z]{4})')

    COMMANDS = {
        'glis': Glissando,
        'puls': PulseChange,
        'spwd': SetPulseWidth,
        'arpg': Arpeggio,
        'vibr': Vibrato,
        'retg': Retrigger,
        'noff': NoteOff,
        'sspd': SetSpeed,
        'jump': JumpToPosition,
        'stop': StopPlaying
    }

    def __init__(self, gpio, filename, debug=False):
        """Constructs a TrackLoader.

        Args:
          gpio: integer. The GPIO to configure the TrackPlayer with.
          filename: string. The track filename to load in.
          debug: boolean. Defaults to False.
        """
        self.gpio = gpio
        self.filename = filename
        self.debug = debug

    def _parse_pattern_line(self, line):
        """Parses a single row of a pattern.

        Args:
          line: a string containing a pattern line from a track file.

        Returns:
          an array of Notes and Commands.
        """
        row = []
        word_idx = 0

        while word_idx < len(line):
            word = line[word_idx]
            result = TrackLoader.NOTE_RE.match(word)
            if result is not None:
                name = result.group('name')
                octave = result.group('octave')
                row.append(Note(result.group('name'), int(result.group('octave'))))

            result = TrackLoader.COMMAND_RE.match(word)
            if result is not None:
                name = result.group('name')
                args = line[word_idx + 1:]
                klass = TrackLoader.COMMANDS[name]
                command, args_used = klass.parse(*args)
                row.append(command)
                word_idx += args_used

            word_idx += 1

        return row

    def _debug(self, str, *args):
        """Helper method to print out a line only if debug is on."""
        if self.debug:
            print(str % args)

    def load(self):
        """Loads the track module from disk.

        Returns:
          A fully initialized TrackPlayer instance, ready to play.
        """
        speed = 3
        patterns = []
        current_pattern = []
        pattern_count = 0
        order = []

        with open(self.filename, 'r') as module:
            lines = module.readlines()
            self._debug('Loaded %d lines.', len(lines))

            header_finished = False
            between_patterns = True

            for line in lines:
                line = line.split()

                if header_finished:
                    if len(line) == 0:
                        if not between_patterns:
                            current_pattern.append([])
                    elif line[0] == 'pattern':
                        between_patterns = False
                        current_pattern = []
                        patterns.append(current_pattern)
                    elif line[0] == 'end':
                        between_patterns = True
                    else:
                        row = self._parse_pattern_line(line)
                        current_pattern.append(row)
                else:
                    if len(line) == 0:
                        continue
                    if line[0] == 'speed':
                        speed = int(line[1])
                    elif line[0] == 'order':
                        order = [int(x) for x in line[1:]]
                    elif line[0] == 'end':
                        if len(order) == 0:
                            raise Exception('No pattern order found!')
                        header_finished = True

        player = TrackPlayer(self.gpio, speed, debug=self.debug)
        for pattern in patterns:
            player.add_pattern(pattern)
        for pattern_idx in order:
            player.add_order(pattern_idx)

        return player
