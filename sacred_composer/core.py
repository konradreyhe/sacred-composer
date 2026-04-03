"""Core data model and rendering — Note, Voice, Score, Composition.

The Composition object collects mapped patterns into voices, layers
them in time, and renders to output formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sacred_composer.mappers import FormSection


@dataclass
class Note:
    """A single musical event."""
    pitch: int          # MIDI note number (0-127), -1 for rest
    duration: float     # Duration in beats (negative = rest)
    velocity: int = 80  # MIDI velocity (1-127)
    time: float = 0.0   # Start time in beats (set during assembly)
    pitch_bend: float = 0.0  # Microtonal offset in semitones (-2.0 to +2.0)

    @property
    def is_rest(self) -> bool:
        return self.pitch < 0 or self.duration < 0

    @property
    def exact_pitch(self) -> float:
        """Exact pitch including microtonal offset."""
        return self.pitch + self.pitch_bend


@dataclass
class Voice:
    """A sequence of notes forming a single musical line."""
    name: str
    notes: list[Note] = field(default_factory=list)
    channel: int = 0
    instrument: int = 0  # General MIDI program number

    @property
    def duration(self) -> float:
        """Total duration in beats."""
        if not self.notes:
            return 0.0
        last = self.notes[-1]
        return last.time + abs(last.duration)

    def append(self, pitch: int, duration: float, velocity: int = 80) -> None:
        """Append a note at the end of this voice."""
        t = self.duration
        self.notes.append(Note(pitch=pitch, duration=duration, velocity=velocity, time=t))


@dataclass
class Score:
    """A collection of voices — the complete musical content."""
    voices: list[Voice] = field(default_factory=list)
    tempo: int = 72

    def add_voice(self, voice: Voice) -> None:
        self.voices.append(voice)

    @property
    def duration(self) -> float:
        """Total duration in beats (longest voice)."""
        if not self.voices:
            return 0.0
        return max(v.duration for v in self.voices)


# GM instrument mapping for convenience
GM_INSTRUMENTS = {
    "piano": 0, "harpsichord": 6, "celesta": 8, "vibraphone": 11,
    "marimba": 12, "organ": 19, "guitar": 24, "violin": 40,
    "viola": 41, "cello": 42, "contrabass": 43, "harp": 46,
    "strings": 48, "choir": 52, "trumpet": 56, "horn": 60,
    "trombone": 57, "tuba": 58, "oboe": 68, "clarinet": 71,
    "bassoon": 70, "flute": 73, "recorder": 74, "pan_flute": 75,
}


class Composition:
    """The main composition object — assembles patterns into music.

    Usage:
        piece = Composition(tempo=72)
        piece.add_voice("melody", pitches, durations, velocities)
        piece.render("output.mid")
    """

    def __init__(self, tempo: int = 72, title: str = "Sacred Composition") -> None:
        self.tempo = tempo
        self.title = title
        self.score = Score(tempo=tempo)
        self.form: list[FormSection] = []
        self._metadata: dict[str, Any] = {}

    def add_voice(
        self,
        name: str,
        pitches: list[int] | list[float],
        durations: list[float],
        velocities: list[int] | None = None,
        instrument: str | int = "piano",
        channel: int | None = None,
        microtonal: bool = False,
    ) -> Voice:
        """Add a voice from mapped pattern data.

        Parameters
        ----------
        name : Voice name (e.g., "melody", "bass").
        pitches : MIDI note numbers from to_pitch(). When *microtonal* is True,
            these may be floats (e.g. 69.5 = A4 + quarter tone); the integer
            part becomes the MIDI note and the fractional part becomes pitch bend.
        durations : Beat durations from to_rhythm(). Negative = rest.
        velocities : MIDI velocities from to_dynamics(). If None, defaults to 80.
        instrument : GM instrument name or program number.
        channel : MIDI channel (auto-assigned if None).
        microtonal : When True, pitches are treated as floats and pitch_bend
            is extracted from the fractional part.
        """
        n = min(len(pitches), len(durations))
        if len(pitches) != len(durations):
            import logging
            logging.getLogger(__name__).debug(
                f"Voice '{name}': pitches({len(pitches)}) and durations({len(durations)}) "
                f"differ in length, using min({n}). Pitches will cycle if shorter."
            )
        if velocities is None:
            velocities = [80] * n
        else:
            velocities = list(velocities[:n])
            while len(velocities) < n:
                velocities.append(80)

        if isinstance(instrument, str):
            prog = GM_INSTRUMENTS.get(instrument, 0)
        else:
            prog = instrument

        if channel is None:
            channel = len(self.score.voices) % 16

        voice = Voice(name=name, channel=channel, instrument=prog)

        time = 0.0
        for i in range(n):
            dur = durations[i]
            if dur < 0:
                # Rest
                voice.notes.append(Note(pitch=-1, duration=abs(dur), velocity=0, time=time))
                time += abs(dur)
            else:
                raw_pitch = pitches[i % len(pitches)]
                if microtonal:
                    midi_note = int(round(raw_pitch))
                    bend = raw_pitch - midi_note  # fractional semitones
                    voice.notes.append(Note(
                        pitch=max(0, min(127, midi_note)),
                        duration=dur,
                        velocity=velocities[i % len(velocities)],
                        time=time,
                        pitch_bend=bend,
                    ))
                else:
                    voice.notes.append(Note(
                        pitch=int(raw_pitch),
                        duration=dur,
                        velocity=velocities[i % len(velocities)],
                        time=time,
                    ))
                time += dur

        self.score.add_voice(voice)
        return voice

    def add_voice_microtonal(
        self,
        name: str,
        pitches: list[float],
        durations: list[float],
        velocities: list[int] | None = None,
        instrument: str | int = "piano",
        channel: int | None = None,
    ) -> Voice:
        """Add a voice with fractional MIDI pitches (microtonal).

        .. deprecated:: Use ``add_voice(..., microtonal=True)`` instead.
        """
        return self.add_voice(
            name=name, pitches=pitches, durations=durations,
            velocities=velocities, instrument=instrument,
            channel=channel, microtonal=True,
        )

    def add_drone(
        self,
        name: str,
        pitch: int,
        total_beats: float,
        velocity: int = 70,
        instrument: str | int = "cello",
        channel: int | None = None,
    ) -> Voice:
        """Add a sustained drone note."""
        return self.add_voice(
            name=name,
            pitches=[pitch],
            durations=[total_beats],
            velocities=[velocity],
            instrument=instrument,
            channel=channel,
        )

    def render(self, filename: str) -> str:
        """Render to MIDI file.

        Returns the filename written.
        """
        if filename.endswith(".mid") or filename.endswith(".midi"):
            return self._render_midi(filename)
        elif filename.endswith(".ly"):
            from sacred_composer.lilypond import render_lilypond
            return render_lilypond(self.score, filename, title=self.title)
        elif filename.endswith(".orch.wav"):
            from sacred_composer.orchestration import render_orchestral_wav
            return render_orchestral_wav(self.score, filename)
        elif filename.endswith(".musicxml") or filename.endswith(".xml"):
            from sacred_composer.musicxml import render_musicxml
            return render_musicxml(self.score, filename, title=self.title)
        elif filename.endswith(".wav"):
            # Try FluidSynth + SoundFont first for real instrument sounds.
            # Falls back to pure-Python synthesis if unavailable.
            try:
                return self._render_fluidsynth_wav(filename)
            except Exception:
                from sacred_composer.wav_renderer import render_wav
                return render_wav(self.score, filename)
        else:
            raise ValueError(f"Unsupported format: {filename}. Use .mid, .ly, .musicxml, .xml, .wav, or .orch.wav")

    def _render_fluidsynth_wav(self, filename: str) -> str:
        """Render via MIDI → FluidSynth + SoundFont → WAV.

        Produces real instrument sounds instead of synthetic sine waves.
        Raises an exception if FluidSynth or a SoundFont isn't available.
        """
        import tempfile
        import os

        # First render MIDI to a temp file
        tmp_mid = tempfile.mktemp(suffix=".mid")
        self._render_midi(tmp_mid)

        try:
            # Use the render_audio module's FluidSynth backend
            import sys
            # Ensure project root is importable
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from render_audio import find_soundfonts, render_fluidsynth

            soundfonts = find_soundfonts()
            if not soundfonts:
                raise RuntimeError("No SoundFont (.sf2) files found")

            sf = soundfonts[0]
            success = render_fluidsynth(tmp_mid, filename, sf)
            if not success:
                raise RuntimeError("FluidSynth rendering failed")

            return filename
        finally:
            if os.path.exists(tmp_mid):
                os.unlink(tmp_mid)

    def _render_midi(self, filename: str) -> str:
        from midiutil import MIDIFile

        n_tracks = len(self.score.voices)
        midi = MIDIFile(numTracks=max(1, n_tracks), ticks_per_quarternote=480)

        for track_idx, voice in enumerate(self.score.voices):
            midi.addTempo(track_idx, 0, self.tempo)
            midi.addTrackName(track_idx, 0, voice.name)
            midi.addProgramChange(track_idx, voice.channel, 0, voice.instrument)

            for note in voice.notes:
                if note.is_rest:
                    continue
                # Microtonal: add pitch bend if note has fractional pitch
                if abs(note.pitch_bend) > 1e-6:
                    # MIDI pitch bend: 8192 = center, range +/- 2 semitones
                    bend_value = int(8192 + note.pitch_bend * 4096)
                    bend_value = max(0, min(16383, bend_value))
                    midi.addPitchWheelEvent(
                        track=track_idx,
                        channel=voice.channel,
                        time=note.time,
                        pitchWheelValue=bend_value - 8192,
                    )
                midi.addNote(
                    track=track_idx,
                    channel=voice.channel,
                    pitch=max(0, min(127, note.pitch)),
                    time=note.time,
                    duration=max(0.0625, note.duration),
                    volume=max(1, min(127, note.velocity)),
                )
                # Reset pitch bend after microtonal note
                if abs(note.pitch_bend) > 1e-6:
                    midi.addPitchWheelEvent(
                        track=track_idx,
                        channel=voice.channel,
                        time=note.time + note.duration,
                        pitchWheelValue=0,
                    )

        with open(filename, "wb") as f:
            midi.writeFile(f)

        return filename

    def to_performance_ir(self):
        """Convert to PerformanceIR for humanization via the existing system."""
        from sacred_composer.bridge import score_to_performance_ir
        return score_to_performance_ir(self.score)

    def info(self) -> dict[str, Any]:
        """Return composition metadata."""
        total_notes = sum(
            len([n for n in v.notes if not n.is_rest])
            for v in self.score.voices
        )
        return {
            "title": self.title,
            "tempo": self.tempo,
            "voices": len(self.score.voices),
            "total_notes": total_notes,
            "duration_beats": self.score.duration,
            "duration_seconds": self.score.duration * 60.0 / self.tempo,
            "form_sections": len(self.form),
        }

    def to_visualization_json(self) -> dict:
        """Export composition data for Remotion/visualization consumption.

        Returns a dict with beat-based and second-based timings for every
        note, suitable for JSON serialization and frame-by-frame rendering.
        """
        bps = self.tempo / 60.0
        return {
            "meta": {
                "title": self.title,
                "tempo": self.tempo,
                "durationBeats": self.score.duration,
                "durationSec": self.score.duration / bps,
                "fps": 60,
            },
            "voices": [
                {
                    "name": v.name,
                    "instrument": v.instrument,
                    "channel": v.channel,
                    "notes": [
                        {
                            "pitch": n.pitch,
                            "velocity": n.velocity,
                            "startBeat": n.time,
                            "durationBeat": n.duration,
                            "startSec": n.time / bps,
                            "durationSec": n.duration / bps,
                            "pitchBend": n.pitch_bend,
                        }
                        for n in v.notes
                        if not n.is_rest
                    ],
                }
                for v in self.score.voices
            ],
            "formSections": [
                {
                    "label": s.label,
                    "startBar": s.start_bar,
                    "endBar": s.end_bar,
                    "bars": s.bars,
                }
                for s in self.form
            ],
        }

    def __repr__(self) -> str:
        info = self.info()
        return (
            f"Composition('{info['title']}', "
            f"{info['voices']} voices, "
            f"{info['total_notes']} notes, "
            f"{info['duration_seconds']:.1f}s)"
        )
