"""Boids-style flocking forces for inner voice leading."""

from __future__ import annotations

from typing import List


def flocking_voice_force(
    current_midi: int,
    other_voices: List[int],
    nearest_chord_tone: int,
    avg_melodic_direction: float,
    *,
    w_cohesion: float = 0.5,
    w_separation: float = 0.3,
    w_alignment: float = 0.2,
    separation_threshold: int = 3,
) -> float:
    """Compute a Boids-style force for inner voice leading.

    Three forces:
      * Cohesion  -- attract toward *nearest_chord_tone*.
      * Separation -- repel from voices within *separation_threshold* semitones.
      * Alignment -- bias toward the average melodic direction of other voices.

    Returns a signed float representing the net pitch adjustment.
    """
    # Cohesion: pull toward nearest chord tone
    cohesion = nearest_chord_tone - current_midi

    # Separation: push away from close voices
    separation = 0.0
    for v in other_voices:
        dist = current_midi - v
        if 0 < abs(dist) <= separation_threshold:
            # Repel proportionally (stronger when closer)
            separation += (separation_threshold - abs(dist) + 1) * (1 if dist > 0 else -1)

    # Alignment: bias toward the average direction of other voices
    alignment = avg_melodic_direction

    return w_cohesion * cohesion + w_separation * separation + w_alignment * alignment
