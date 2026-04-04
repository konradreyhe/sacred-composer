"""Sacred and mathematical constants."""

import math
import os

# Project root directory (parent of sacred_composer package)
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The golden ratio
phi: float = (1 + math.sqrt(5)) / 2  # 1.6180339887...

# Inverse of the golden ratio (phi - 1, the golden section proportion)
PHI_INVERSE: float = 1 / phi  # 0.6180339887...

# The golden angle in degrees (360 / phi^2)
golden_angle: float = 360 / (phi ** 2)  # 137.5077640...

# Fibonacci semitone intervals (Bartok's vocabulary)
fibonacci_intervals: tuple[int, ...] = (1, 1, 2, 3, 5, 8, 13)

# Feigenbaum's first constant (period-doubling universality)
FEIGENBAUM_DELTA: float = 4.669201609

# ---- MIDI constants ----
MIDI_MAX_VELOCITY: int = 127
MIDI_PITCH_BEND_CENTER: int = 8192
MIDI_MIN_NOTE_DURATION: float = 0.0625  # 1/16 beat
DEFAULT_TEMPO: int = 72

# Common sacred/significant numbers
sacred_numbers: dict[str, float] = {
    "phi": phi,
    "pi": math.pi,
    "e": math.e,
    "sqrt2": math.sqrt(2),
    "sqrt3": math.sqrt(3),
    "sqrt5": math.sqrt(5),
}

# Scale definitions: name -> semitone intervals from root
SCALES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "whole_tone": (0, 2, 4, 6, 8, 10),
    "chromatic": tuple(range(12)),
    "pentatonic_major": (0, 2, 4, 7, 9),
    "pentatonic_minor": (0, 3, 5, 7, 10),
    # Japanese scales
    "in_sen": (0, 1, 5, 7, 10),
    "yo": (0, 2, 5, 7, 9),
    "miyako_bushi": (0, 1, 5, 7, 8),
    "hirajoshi": (0, 2, 3, 7, 8),
    "kumoi": (0, 2, 3, 7, 9),
    "iwato": (0, 1, 5, 6, 10),
    # Indian-derived (approximate 12-TET mappings)
    "bhairav": (0, 1, 4, 5, 7, 8, 11),
    "yaman": (0, 2, 4, 6, 7, 9, 11),
    "todi": (0, 1, 3, 6, 7, 8, 11),
    "malkauns": (0, 3, 5, 8, 10),
}

# Note name to MIDI pitch class
NOTE_NAMES: dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


def parse_scale(scale_name: str) -> list[int]:
    """Parse a scale name like 'C_major' or 'F#_harmonic_minor' into MIDI note numbers across all octaves."""
    parts = scale_name.split("_", 1)
    root_name = parts[0]
    scale_type = parts[1] if len(parts) > 1 else "major"

    if root_name not in NOTE_NAMES:
        raise ValueError(f"Unknown note: '{root_name}'. Valid: {list(NOTE_NAMES.keys())}")
    if scale_type not in SCALES:
        import logging
        logging.getLogger(__name__).warning(
            f"Unknown scale type '{scale_type}', defaulting to 'major'. Valid: {list(SCALES.keys())}"
        )

    root_pc = NOTE_NAMES[root_name]
    intervals = SCALES.get(scale_type, SCALES["major"])

    notes = []
    for octave in range(11):  # MIDI octaves 0-10
        base = octave * 12
        for interval in intervals:
            midi = base + root_pc + interval
            if 0 <= midi <= 127:
                notes.append(midi)
    return sorted(set(notes))
