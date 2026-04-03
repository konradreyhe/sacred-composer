"""Phyllotaxis-inspired melodic interval selection."""

from __future__ import annotations

import random


def phyllotaxis_interval() -> int:
    """Choose a melodic interval inspired by the golden angle.

    The golden angle as a fraction of chromatic space is ~4.58 semitones.
    We approximate this as: 58 % chance of a perfect 4th (5 semitones),
    42 % chance of a major 3rd (4 semitones).  This produces melodies
    that spread through pitch space efficiently, like leaves on a stem.
    """
    return 5 if random.random() < 0.58 else 4
