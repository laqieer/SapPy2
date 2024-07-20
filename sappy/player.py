# -*- coding: utf-8 -*-
"""M4A engine emulation functionality.

Attributes
----------
LOGGER : logging.Logger
    Module-level logger

"""
from logging import basicConfig, getLogger, DEBUG, WARNING
from os import remove
from time import perf_counter
from typing import Union

# Local library imports
from .config import (MAX_FMOD_TRACKS, PLAYBACK_FRAME_RATE, PLAYBACK_SPEED,
                     SHOW_FMOD_EXECUTION, SHOW_PROCESSOR_EXECUTION,
                     TICKS_PER_SECOND, CULL_FRAME_DELAY)
from .exceptions import BlankSong, InvalidROM, InvalidSongNumber
from pyfmodex.enums import SOUND_FORMAT, SOUND_TYPE, TIMEUNIT
from pyfmodex.flags import MODE
from pyfmodex.system import System
from pyfmodex.structures import CREATESOUNDEXINFO
from .inst_set import KeyArg
from .interface import Display
from .m4a import (FMODNote, M4ADirectSound, M4ADirectSoundSample, M4ADrum,
                  M4AKeyZone, M4ANoise, M4ASample, M4ASong, M4ASquare1,
                  M4ASquare2, M4ATrack, M4AWaveform, resample)
from .parser import Parser

LOGGER = getLogger(__name__)
LOGGER.setLevel(DEBUG)


class Player(object):
    """Interprets translated M4A commands and emulates M4A engine functionality.

    Attributes
    ----------
    Player.PROCESSOR_LOGGER : Logger
        Class-level logger exclusively for the M4A engine.
    Player.FMOD_LOGGER : Logger
        Class-level logger exclusively for the FMOD library.
    samples : Dict[Union[int, str], M4ASample]
        Dictionary of sample constructs from `M4ASong`.
    voices : Dict[int, M4AVoice]
        Dictionary of voice constructs from `M4ASong`.
    tracks : List[M4ATrack]
        List of tracks from `M4ASong`.
    song : M4ASong
        Song entry loaded from ROM.
    frame_ctr : int
        Global frame counter.

    """

    basicConfig(level=DEBUG)
    PROCESSOR_LOGGER = getLogger('PROCESSOR')
    FMOD_LOGGER = getLogger('FMOD')
    if not SHOW_PROCESSOR_EXECUTION:
        PROCESSOR_LOGGER.setLevel(WARNING)
    if not SHOW_FMOD_EXECUTION:
        FMOD_LOGGER.setLevel(WARNING)

    def __init__(self):
        self.song = M4ASong()
        self.samples = self.song.samples
        self.voices = self.song.voices
        self.tracks = self.song.tracks
        self.sdm = self.song.sdm
        self.frame_ctr = 0
        self.system = System()

    def debug_m4a(self, action: str, track_id: int):
        """Log M4A processor information."""
        self.PROCESSOR_LOGGER.log(DEBUG, f' {action:^24} | Track: {track_id:2}')

    def load_sample(self, sample):
        """Create sample handle in the FMOD player based on sample data.

        Parameters
        ----------
        rom_path : str
            File path to the raw PCM8 sound sample
        sample : M4ASample
            Sample information

        Returns
        -------
        int
            FMOD sample handle.

        """
        mode = MODE.OPENMEMORY | MODE.OPENRAW | MODE.CREATESTREAM
        if sample.looped:
            mode |= MODE.LOOP_NORMAL
        else:
            mode |= MODE.LOOP_OFF
        if type(sample) != M4ADirectSoundSample:
            sample.sample_data = bytes((byte + 128) % 256 for byte in sample.sample_data)
        sound = self.system.create_sound(sample.sample_data, mode=mode, 
                                         exinfo=CREATESOUNDEXINFO(length=sample.size,
                                                                  sound_type=SOUND_TYPE.RAW.value,
                                                                  format=SOUND_FORMAT.PCM8.value,
                                                                  numchannels=1,
                                                                  defaultfrequency=sample.frequency))
        if sample.looped:
            sound.set_loop_points(sample.loop_start, TIMEUNIT.PCMBYTES, sample.size - 1, TIMEUNIT.PCMBYTES)
        return sound

    def load_samples(self):
        """Load requisite DirectSound samples."""
        for sample in self.samples.values():
            sample.sound = self.load_sample(sample)

    def init_player(self):
        """Initialize FMOD player and load samples."""
        self.system.init(maxchannels=MAX_FMOD_TRACKS)
        self.load_samples()

    def play_song(self, path, song_id, table_ptr):
        """Start emulation of an M4A song entry.

        Parameters
        ----------
        path : str
            Path to GBA ROM.
        song_id : int
            Song entry number.
        table_ptr : int
            Address of M4A song table.

        Returns
        -------
        None

        """
        parser = Parser(path)
        try:
            song = parser.load_song(song_id, table_ptr)
        except (InvalidROM, InvalidSongNumber, BlankSong) as e:
            LOGGER.critical(e)
            return
        self.song = song
        self.tracks = song.tracks
        self.samples = song.samples
        self.voices = song.voices
        self.sdm = song.sdm
        self.init_player()

        self.execute_processor()

    def cull_notes(self):
        """Remove all disabled FMOD channels and discard ADSR dead notes from
        all tracks.

        Notes
        -----
            "Disabled" notes/channels are denoted as muted in the FMOD player to
            avoid any accidental playback on unused channels.

            This function is called indefinitely with a frame delay of
            `CULL_FRAME_DELAY`.

        """
        for track in self.tracks:
            for note in track.notes[::]:
                if note.muted:
                    track.notes.remove(note)
                    # note.set_mute(False)
                    # note.channel.stop()

    def execute_tracks(self, ticks):
        """Process each track under a various tick rate.

        Parameters
        ----------
        ticks : int
            Ticks to execute each track.

        """
        for _ in range(ticks):
            for track_id, track in enumerate(self.tracks):
                track.update()

    def play_notes(self):
        """Empty all track note queues and open new FMOD channels to simulate
        M4A playback."""
        for track in self.tracks:
            if track.voice == M4ATrack.NO_VOICE:
                track.note_queue.clear()
            for note in track.note_queue:
                sample_ptr, frequency = self.get_playback_data(note)
                output_frequency = round(frequency * track.frequency)
                output_panning = track.panning
                note.frequency = frequency
                sample = self.samples[sample_ptr].sound
                # note.channel = sample.play(paused=True)
                note.channel = self.system.play_sound(sample, paused=True)
                note.set_frequency(output_frequency)
                note.set_panning(output_panning)
                note.set_volume(0)
                note.channel.paused = False

                track.lfo_pos = 0
                track.notes.append(note)
            track.note_queue.clear()

    def execute_processor(self):
        """Execute M4A song instructions and update CLI display."""
        frame_delay = 1 / PLAYBACK_FRAME_RATE

        buffer = 0
        display = Display(self.tracks)
        ticker = Ticker()

        while buffer < M4ATrack.TEMPO:
            start_time = perf_counter()

            self.frame_ctr += 1
            self.frame_ctr %= CULL_FRAME_DELAY

            ticks = ticker()
            self.execute_tracks(ticks)
            self.play_notes()
            for track in self.tracks:
                # print(f"Track: program_ctr: {track.program_ctr}, Voice: {track.voice}, Note Queue: {track.note_queue}, Notes: {track.notes}")
                # print(self.system.channels_playing)
                track.update_envelope()
            if self.frame_ctr == 0:
                self.cull_notes()
            if not any(track.enabled for track in self.tracks):
                buffer += ticks

            code = display.update()
            if code is False:
                display.exit_scr()
                for sample in self.samples.values():
                    sample.sound.release()
                self.system.release()
                break
            display.draw()
            display.wait(frame_delay - (perf_counter() - start_time))

    def get_playback_data(self, note):
        """Retrieve the sample pointer and frequency of a note.

        Parameters
        ----------
        note : FMODNote

        Returns
        -------
        tuple of int
            Sample pointer and note frequency.

        """
        voice = self.voices[note.voice]
        if voice.mode == 0x40:
            voice: M4AKeyZone
            voice = voice.voice_table[voice.keymap[note.midi_note]]
            sample_key = note.midi_note
        elif voice.mode == 0x80:
            voice: M4ADrum
            voice = voice.voice_table[note.midi_note]
            sample_key = voice.root
        else:
            sample_key = note.midi_note + (KeyArg.Cn3 - voice.root)
        note.reset_mixer(voice)

        if voice.mode in (0x0, 0x8, 0x3, 0xB):
            voice: Union[M4ADirectSound, M4AWaveform]
            sample_ptr = voice.sample_ptr
            sample = self.samples[sample_ptr]
            if voice.mode == 0x8:
                frequency = sample.frequency
            elif voice.mode in (0x3, 0xB):
                frequency = resample(sample_key, -2)
            else:
                frequency = resample(sample_key, sample.frequency)
        elif voice.mode in (0x1, 0x2, 0x9, 0xA):
            voice: Union[M4ASquare1, M4ASquare2]
            sample_ptr = f'square{voice.duty_cycle % 4}'
            frequency = resample(sample_key, -4)
        else:
            voice: M4ANoise
            sample_ptr = f'noise{voice.period}'
            frequency = resample(sample_key)
        return sample_ptr, frequency


class Ticker(object):
    """M4A engine tick clock.

    Attributes
    ----------
    tick_ctr : int
        Global tick counter.

    """

    def __init__(self):
        self.tick_ctr = 0

    def __call__(self) -> int:
        """Execute one cycle of the tick clock."""
        prev_ticks = int(self.tick_ctr)
        average_ticks = M4ATrack.TEMPO / (TICKS_PER_SECOND / PLAYBACK_SPEED)
        self.tick_ctr += average_ticks
        ticks = int(self.tick_ctr - prev_ticks)
        self.tick_ctr %= TICKS_PER_SECOND
        return ticks
