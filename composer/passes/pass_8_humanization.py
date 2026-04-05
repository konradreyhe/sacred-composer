"""PASS 8: Humanization (timing jitter, velocity curves, rubato)."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from SYSTEM_ARCHITECTURE import (
    FormIR, PerformanceNote, ArticulationToken,
)
from composer._rng import np_rng
from composer.helpers.pink_noise import generate_1f_noise


def pass_8_humanization(tracks: Dict[str, List[PerformanceNote]],
                        form_ir: FormIR) -> Dict[str, List[PerformanceNote]]:
    """
    PASS 8: Apply human-like performance deviations.

    1. Timing jitter: 1/f (pink) noise for natural rubato.
    2. Melody leads accompaniment by 10-20ms.
    3. Cadential ritardando: slow down last 2 beats of cadence bars by 15-25%.
    4. Velocity micro-variation: Gaussian (sigma=3).
    5. Articulation realization: adjust durations for staccato/legato/portato.
    """
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    total_bars = form_ir.total_bars
    total_time = total_bars * 4 * sec_per_beat

    melody_instruments = {"violin1", "flute", "oboe", "piano", "piano_rh", "piano_s"}

    for inst_name, notes in tracks.items():
        is_melody = inst_name in melody_instruments

        notes.sort(key=lambda n: n.start_time_sec)

        pink_noise = generate_1f_noise(len(notes), sigma_ms=12.0)

        for i, note in enumerate(notes):
            jitter_sec = pink_noise[i] if i < len(pink_noise) else 0.0
            melody_lead_ms = -15.0 if is_melody else 0.0
            note.timing_offset_ms = jitter_sec * 1000.0 + melody_lead_ms

            if total_time > 0 and note.start_time_sec > total_time * 0.95:
                ritard_factor = 1.20
                note.duration_sec *= ritard_factor

            note.velocity_offset = int(np_rng().normal(0, 3))
            note.velocity = max(1, min(127, note.velocity + note.velocity_offset))

            if note.articulation == ArticulationToken.STACCATO:
                note.duration_sec *= np_rng().uniform(0.35, 0.50)
            elif note.articulation == ArticulationToken.LEGATO:
                note.duration_sec *= np_rng().uniform(0.95, 1.05)
            elif note.articulation == ArticulationToken.PORTATO:
                note.duration_sec *= np_rng().uniform(0.75, 0.88)
            elif note.articulation == ArticulationToken.MARCATO:
                note.duration_sec *= np_rng().uniform(0.80, 0.95)
                note.velocity = min(127, note.velocity + 5)
            elif note.articulation == ArticulationToken.TENUTO:
                note.duration_sec *= np_rng().uniform(0.98, 1.02)

            note.start_time_sec = max(0, note.start_time_sec + note.timing_offset_ms / 1000.0)

    return tracks
