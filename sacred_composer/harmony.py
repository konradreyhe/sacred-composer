"""Harmonic engine — chord progression generation via weighted state machine.

Implements functional harmony as a directed graph with corpus-derived
transition probabilities (informed by Rohrmeier & Pearce 2018 chord
grammar and Bach chorale analysis). All functions are deterministic
given a seed — uses random.Random(seed), never global state.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from sacred_composer.constants import NOTE_NAMES, SCALES


# ---------------------------------------------------------------------------
# Chord grammar: Roman numeral -> weighted transitions
# Probabilities derived from Bach chorale corpus analysis.
# ---------------------------------------------------------------------------

CHORD_GRAMMAR: dict[str, list[tuple[str, float]]] = {
    "I":   [("IV", 0.25), ("V", 0.30), ("vi", 0.20), ("ii", 0.15), ("iii", 0.10)],
    "ii":  [("V", 0.60), ("vii", 0.20), ("IV", 0.10), ("ii", 0.10)],
    "iii": [("vi", 0.40), ("IV", 0.35), ("ii", 0.25)],
    "IV":  [("V", 0.45), ("I", 0.20), ("ii", 0.15), ("vii", 0.10), ("vi", 0.10)],
    "V":   [("I", 0.55), ("vi", 0.25), ("IV", 0.10), ("V", 0.10)],
    "vi":  [("ii", 0.35), ("IV", 0.30), ("V", 0.20), ("iii", 0.15)],
    "vii": [("I", 0.55), ("iii", 0.25), ("vi", 0.20)],
}

# Semitone offsets from scale root for each Roman numeral (major-key basis).
# Lowercase = minor triad, uppercase = major triad, vii = diminished.
_ROMAN_SCALE_DEGREE: dict[str, int] = {
    "I": 0, "ii": 1, "iii": 2, "IV": 3, "V": 4, "vi": 5, "vii": 6,
}

# Quality implied by each Roman numeral in a major key.
_ROMAN_QUALITY: dict[str, str] = {
    "I": "major", "ii": "minor", "iii": "minor", "IV": "major",
    "V": "major", "vi": "minor", "vii": "dim",
}

# Interval templates (semitones from root) for chord qualities.
_QUALITY_INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (0, 4, 7),
    "minor": (0, 3, 7),
    "dim":   (0, 3, 6),
}


# ---------------------------------------------------------------------------
# Chord dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Chord:
    """A chord defined by root pitch class, quality, and pitch classes."""

    root: int                          # pitch class 0-11
    quality: str                       # 'major', 'minor', 'dim'
    pitch_classes: tuple[int, ...]     # pitch classes 0-11
    roman: str = ""                    # original Roman numeral label

    def to_midi_pitches(self, octave: int = 4) -> list[int]:
        """Return MIDI note numbers for a close-position voicing.

        Parameters
        ----------
        octave : Base octave for the root (C4 = octave 4 = MIDI 60).
        """
        base = octave * 12 + 12  # MIDI convention: octave 4 -> 60
        intervals = _QUALITY_INTERVALS[self.quality]
        return [base + self.root + iv for iv in intervals]

    def __repr__(self) -> str:
        label = self.roman or f"pc{self.root}"
        return f"Chord({label}, {self.quality}, pcs={list(self.pitch_classes)})"


# ---------------------------------------------------------------------------
# Roman numeral -> Chord resolution
# ---------------------------------------------------------------------------

def roman_to_chord(numeral: str, key: str) -> Chord:
    """Resolve a Roman numeral chord symbol in a given key.

    Parameters
    ----------
    numeral : One of 'I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii'.
    key : Scale name such as 'C_major', 'D_minor', 'A_harmonic_minor'.

    Returns
    -------
    Chord with concrete pitch classes.
    """
    parts = key.split("_", 1)
    root_name = parts[0]
    scale_type = parts[1] if len(parts) > 1 else "major"

    key_root_pc = NOTE_NAMES.get(root_name, 0)
    intervals = SCALES.get(scale_type, SCALES["major"])

    degree = _ROMAN_SCALE_DEGREE[numeral]
    # The chord root is the scale degree's pitch class.
    if degree < len(intervals):
        chord_root_pc = (key_root_pc + intervals[degree]) % 12
    else:
        chord_root_pc = (key_root_pc + degree * 2) % 12  # fallback

    quality = _ROMAN_QUALITY[numeral]
    chord_intervals = _QUALITY_INTERVALS[quality]
    pitch_classes = tuple((chord_root_pc + iv) % 12 for iv in chord_intervals)

    return Chord(
        root=chord_root_pc,
        quality=quality,
        pitch_classes=pitch_classes,
        roman=numeral,
    )


# ---------------------------------------------------------------------------
# Progression generation
# ---------------------------------------------------------------------------

def _weighted_choice(transitions: list[tuple[str, float]], rng: random.Random) -> str:
    """Pick a chord symbol from weighted transitions."""
    r = rng.random()
    cumulative = 0.0
    for symbol, weight in transitions:
        cumulative += weight
        if r <= cumulative:
            return symbol
    # Floating-point safety: return the last option.
    return transitions[-1][0]


def generate_progression(
    n_chords: int = 8,
    key: str = "C_major",
    seed: int = 42,
    start: str = "I",
) -> list[Chord]:
    """Walk the chord grammar graph stochastically for *n_chords* steps.

    Forces a V-I authentic cadence at the end.

    Parameters
    ----------
    n_chords : Total number of chords (minimum 2 for the cadence).
    key : Scale key such as 'C_major' or 'D_minor'.
    seed : Random seed for reproducibility.
    start : Starting chord symbol.

    Returns
    -------
    List of Chord objects forming the progression.
    """
    if n_chords < 2:
        n_chords = 2

    rng = random.Random(seed)

    if n_chords == 2:
        # Minimal cadence only.
        return [roman_to_chord("V", key), roman_to_chord("I", key)]

    symbols: list[str] = [start]
    current = start

    # Generate interior chords, reserving the last 2 slots for the cadence.
    for _ in range(n_chords - 3):
        transitions = CHORD_GRAMMAR.get(current, CHORD_GRAMMAR["I"])
        current = _weighted_choice(transitions, rng)
        symbols.append(current)

    # Force authentic cadence: V -> I
    symbols.append("V")
    symbols.append("I")

    return [roman_to_chord(s, key) for s in symbols]


# ---------------------------------------------------------------------------
# Voice leading
# ---------------------------------------------------------------------------

def voice_lead(current_voicing: list[int], next_chord: Chord) -> list[int]:
    """Find the voicing of *next_chord* that minimises total voice movement.

    Each voice moves to the nearest available chord tone (any octave).
    Voices are assigned greedily from smallest to largest movement.

    Parameters
    ----------
    current_voicing : List of MIDI note numbers (one per voice).
    next_chord : The target Chord.

    Returns
    -------
    List of MIDI note numbers for the new voicing (same length as input).
    """
    pcs = next_chord.pitch_classes

    # Build candidate pitches across a wide range around the current voicing.
    if current_voicing:
        center = sum(current_voicing) // len(current_voicing)
    else:
        center = 60
    candidates: list[int] = []
    for pc in pcs:
        for octave_midi in range(center - 18, center + 19):
            note = (octave_midi // 12) * 12 + pc
            if 24 <= note <= 108 and abs(note - center) <= 18:
                candidates.append(note)
    candidates = sorted(set(candidates))

    if not candidates:
        return list(current_voicing)

    # Greedy assignment: for each voice, pick the closest unused candidate.
    result = [0] * len(current_voicing)
    used: set[int] = set()

    # Sort voices by how constrained they are (smallest movement first).
    voice_order = sorted(
        range(len(current_voicing)),
        key=lambda i: min(abs(c - current_voicing[i]) for c in candidates),
    )

    for vi in voice_order:
        target = current_voicing[vi]
        best = min(candidates, key=lambda c: (abs(c - target), c in used))
        result[vi] = best
        used.add(best)

    return result


# ---------------------------------------------------------------------------
# Melody from chord progression
# ---------------------------------------------------------------------------

def melody_from_chords(
    progression: list[Chord],
    scale_pitches: list[int],
    beats_per_chord: int = 4,
    seed: int = 42,
    octave: int = 5,
) -> tuple[list[int], list[float]]:
    """Generate a melody guided by a chord progression.

    Strategy: chord tones on strong beats (1, 3), scale steps on
    weak beats (2, 4). Returns both pitches and durations.

    Parameters
    ----------
    progression : List of Chord objects.
    scale_pitches : All valid MIDI pitches in the scale (from parse_scale).
    beats_per_chord : How many beats each chord lasts.
    seed : Random seed.
    octave : Target octave for the melody.

    Returns
    -------
    (pitches, durations) — lists of MIDI note numbers and beat durations.
    """
    rng = random.Random(seed)
    lo = octave * 12 + 12
    hi = lo + 14  # roughly one octave + a step
    melody_scale = [p for p in scale_pitches if lo <= p <= hi]
    if not melody_scale:
        melody_scale = [p for p in scale_pitches if 60 <= p <= 84]
    if not melody_scale:
        melody_scale = list(range(lo, hi + 1))

    pitches: list[int] = []
    durations: list[float] = []
    prev_pitch = melody_scale[len(melody_scale) // 2]

    for chord in progression:
        # Chord tones in the melody octave.
        chord_tones_in_range = []
        for pc in chord.pitch_classes:
            for candidate in melody_scale:
                if candidate % 12 == pc:
                    chord_tones_in_range.append(candidate)
        if not chord_tones_in_range:
            chord_tones_in_range = melody_scale[:3]

        for beat in range(beats_per_chord):
            is_strong = (beat % 2 == 0)

            if is_strong:
                # Strong beat: pick a chord tone near the previous pitch.
                candidates = sorted(chord_tones_in_range, key=lambda p: abs(p - prev_pitch))
                pitch = candidates[0] if candidates else prev_pitch
            else:
                # Weak beat: stepwise motion in the scale.
                idx_candidates = [
                    i for i, p in enumerate(melody_scale)
                    if abs(p - prev_pitch) <= 3
                ]
                if idx_candidates:
                    idx = rng.choice(idx_candidates)
                    pitch = melody_scale[idx]
                else:
                    pitch = min(melody_scale, key=lambda p: abs(p - prev_pitch))

            pitches.append(pitch)
            durations.append(1.0)
            prev_pitch = pitch

    return pitches, durations


# ---------------------------------------------------------------------------
# Bass line from progression
# ---------------------------------------------------------------------------

def bass_from_chords(
    progression: list[Chord],
    beats_per_chord: int = 4,
    octave: int = 2,
) -> tuple[list[int], list[float]]:
    """Generate a bass line using chord roots.

    Root on beat 1, held or repeated on remaining beats.

    Parameters
    ----------
    progression : List of Chord objects.
    beats_per_chord : Beats per chord.
    octave : Bass octave.

    Returns
    -------
    (pitches, durations)
    """
    pitches: list[int] = []
    durations: list[float] = []

    for chord in progression:
        root_midi = octave * 12 + 12 + chord.root
        # Beat 1: root, full duration.
        pitches.append(root_midi)
        durations.append(float(beats_per_chord))

    return pitches, durations


# ---------------------------------------------------------------------------
# HarmonicEngine — top-level orchestrator
# ---------------------------------------------------------------------------

class HarmonicEngine:
    """Combines chord grammar, voice leading, melody, and bass generation.

    Usage::

        engine = HarmonicEngine(key="D_minor", n_chords=16, seed=7)
        progression = engine.progression
        melody_pitches, melody_durs = engine.melody()
        bass_pitches, bass_durs = engine.bass()

        # Or apply directly to a CompositionBuilder:
        builder = CompositionBuilder(key="D_minor", bars=64)
        engine.apply_to_builder(builder)
        piece = builder.build()
    """

    def __init__(
        self,
        key: str = "C_major",
        n_chords: int = 8,
        seed: int = 42,
        beats_per_chord: int = 4,
    ) -> None:
        self.key = key
        self.n_chords = n_chords
        self.seed = seed
        self.beats_per_chord = beats_per_chord

        self.progression: list[Chord] = generate_progression(
            n_chords=n_chords, key=key, seed=seed,
        )

        # Pre-compute voice-led inner voicings.
        self._voicings: list[list[int]] = self._compute_voicings()

    def _compute_voicings(self) -> list[list[int]]:
        """Compute voice-led chord voicings for the whole progression."""
        if not self.progression:
            return []
        voicings: list[list[int]] = []
        current = self.progression[0].to_midi_pitches(octave=4)
        voicings.append(current)
        for chord in self.progression[1:]:
            current = voice_lead(current, chord)
            voicings.append(current)
        return voicings

    def melody(self, octave: int = 5) -> tuple[list[int], list[float]]:
        """Generate a melody over the progression."""
        from sacred_composer.constants import parse_scale
        scale_pitches = parse_scale(self.key)
        return melody_from_chords(
            self.progression,
            scale_pitches,
            beats_per_chord=self.beats_per_chord,
            seed=self.seed + 1,
            octave=octave,
        )

    def bass(self, octave: int = 2) -> tuple[list[int], list[float]]:
        """Generate a bass line from chord roots."""
        return bass_from_chords(
            self.progression,
            beats_per_chord=self.beats_per_chord,
            octave=octave,
        )

    def voicings(self) -> list[list[int]]:
        """Return the voice-led inner voicings."""
        return list(self._voicings)

    def apply_to_builder(self, builder) -> None:
        """Add harmony-driven voices to a CompositionBuilder.

        Adds melody, inner harmony, and bass voices to the builder's
        underlying Composition. Call this *before* ``builder.build()``,
        then the builder's own voices layer on top.

        Parameters
        ----------
        builder : A ``CompositionBuilder`` instance.
        """
        from sacred_composer.core import Composition

        mel_pitches, mel_durs = self.melody()
        bass_pitches, bass_durs = self.bass()

        # Store voices as pre-built specs so build() includes them.
        # We inject directly into the builder's voice list as raw dicts
        # with a special role that build() will pass through.
        builder._harmony_voices = {
            "melody": (mel_pitches, mel_durs),
            "bass": (bass_pitches, bass_durs),
            "voicings": self._voicings,
            "progression": self.progression,
            "beats_per_chord": self.beats_per_chord,
        }

    def to_composition(
        self,
        title: str = "Harmonic Composition",
        tempo: int = 72,
        melody_instrument: str = "violin",
        bass_instrument: str = "cello",
        inner_instrument: str = "viola",
    ) -> "Composition":
        """Build a standalone Composition from this engine's output.

        A convenience method when you don't need the full builder.
        """
        from sacred_composer.core import Composition

        piece = Composition(tempo=tempo, title=title)

        # Melody
        mel_pitches, mel_durs = self.melody()
        piece.add_voice(
            name="harmony_melody",
            pitches=mel_pitches,
            durations=mel_durs,
            instrument=melody_instrument,
        )

        # Inner voices (from voice-led voicings).
        if self._voicings:
            inner_pitches: list[int] = []
            inner_durs: list[float] = []
            for voicing in self._voicings:
                # Use the middle note of each voicing.
                mid = voicing[len(voicing) // 2] if voicing else 60
                inner_pitches.append(mid)
                inner_durs.append(float(self.beats_per_chord))
            piece.add_voice(
                name="harmony_inner",
                pitches=inner_pitches,
                durations=inner_durs,
                instrument=inner_instrument,
            )

        # Bass
        bass_pitches, bass_durs = self.bass()
        piece.add_voice(
            name="harmony_bass",
            pitches=bass_pitches,
            durations=bass_durs,
            instrument=bass_instrument,
        )

        return piece

    def info(self) -> dict:
        """Return a summary of the harmonic plan."""
        return {
            "key": self.key,
            "n_chords": self.n_chords,
            "seed": self.seed,
            "beats_per_chord": self.beats_per_chord,
            "total_beats": self.n_chords * self.beats_per_chord,
            "progression": [c.roman for c in self.progression],
            "cadence": (
                f"{self.progression[-2].roman}-{self.progression[-1].roman}"
                if len(self.progression) >= 2 else "none"
            ),
        }

    def __repr__(self) -> str:
        symbols = " ".join(c.roman for c in self.progression)
        return f"HarmonicEngine(key={self.key!r}, [{symbols}])"
