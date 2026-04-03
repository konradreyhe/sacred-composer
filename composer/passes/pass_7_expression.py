"""PASS 7: Expression (dynamics, articulation)."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from SYSTEM_ARCHITECTURE import (
    FormIR, PerformanceNote,
    CharacterToken, ArticulationToken, DynamicToken,
)


# Character -> expression parameters
CHARACTER_EXPRESSION = {
    CharacterToken.HEROIC:     {"base_vel": 90, "art": ArticulationToken.MARCATO,   "dynamic": DynamicToken.F},
    CharacterToken.LYRICAL:    {"base_vel": 65, "art": ArticulationToken.LEGATO,    "dynamic": DynamicToken.MP},
    CharacterToken.MYSTERIOUS: {"base_vel": 50, "art": ArticulationToken.PORTATO,   "dynamic": DynamicToken.PP},
    CharacterToken.AGITATED:   {"base_vel": 85, "art": ArticulationToken.STACCATO,  "dynamic": DynamicToken.F},
    CharacterToken.SERENE:     {"base_vel": 55, "art": ArticulationToken.LEGATO,    "dynamic": DynamicToken.P},
    CharacterToken.TRIUMPHANT: {"base_vel": 100,"art": ArticulationToken.MARCATO,   "dynamic": DynamicToken.FF},
    CharacterToken.TRAGIC:     {"base_vel": 60, "art": ArticulationToken.LEGATO,    "dynamic": DynamicToken.MP},
    CharacterToken.PASTORAL:   {"base_vel": 60, "art": ArticulationToken.LEGATO,    "dynamic": DynamicToken.P},
    CharacterToken.STORMY:     {"base_vel": 95, "art": ArticulationToken.MARCATO,   "dynamic": DynamicToken.FF},
    CharacterToken.NOBLE:      {"base_vel": 80, "art": ArticulationToken.TENUTO,    "dynamic": DynamicToken.MF},
    CharacterToken.PLAYFUL:    {"base_vel": 75, "art": ArticulationToken.STACCATO,  "dynamic": DynamicToken.MF},
    CharacterToken.TENDER:     {"base_vel": 50, "art": ArticulationToken.LEGATO,    "dynamic": DynamicToken.PP},
    CharacterToken.ANGUISHED:  {"base_vel": 85, "art": ArticulationToken.ACCENT,    "dynamic": DynamicToken.F},
    CharacterToken.MAJESTIC:   {"base_vel": 90, "art": ArticulationToken.TENUTO,    "dynamic": DynamicToken.F},
}


def _tension_curve(t: float) -> float:
    """
    Global tension curve: rises from 0.0 to peak 1.0 at the golden ratio
    (t=0.618), then descends to 0.0 at t=1.0.
    """
    CLIMAX = 0.618
    t = max(0.0, min(1.0, t))
    if t <= CLIMAX:
        return (t / CLIMAX) ** 1.5
    else:
        return ((1.0 - t) / (1.0 - CLIMAX)) ** 2.0


def pass_7_expression(tracks: Dict[str, List[PerformanceNote]],
                      form_ir: FormIR) -> Dict[str, List[PerformanceNote]]:
    """
    PASS 7: Apply expression with a global tension arc.
    """
    character = form_ir.character
    params = CHARACTER_EXPRESSION.get(character, CHARACTER_EXPRESSION[CharacterToken.HEROIC])
    art = params["art"]
    dyn = params["dynamic"]

    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    total_bars = form_ir.total_bars
    total_time = total_bars * 4 * sec_per_beat
    if total_time <= 0:
        total_time = 1.0

    vel_start = 70
    vel_climax = 110
    vel_end = 55

    if character in (CharacterToken.HEROIC, CharacterToken.TRIUMPHANT, CharacterToken.MAJESTIC):
        vel_start = 70
        vel_climax = 110
        vel_end = 90
    elif character in (CharacterToken.LYRICAL, CharacterToken.TENDER, CharacterToken.SERENE):
        vel_start = 55
        vel_climax = 95
        vel_end = 40
    elif character in (CharacterToken.AGITATED, CharacterToken.STORMY, CharacterToken.ANGUISHED):
        vel_start = 70
        vel_climax = 110
        vel_end = 55
    elif character in (CharacterToken.MYSTERIOUS, CharacterToken.PASTORAL):
        vel_start = 50
        vel_climax = 85
        vel_end = 45

    max_register_shift = 4

    melody_instruments = set()
    if "violin1" in tracks:
        melody_instruments.add("violin1")
    if "flute" in tracks:
        melody_instruments.add("flute")
    if "piano" in tracks:
        melody_instruments.add("piano")
    if "piano_rh" in tracks:
        melody_instruments.add("piano_rh")
    if "piano_s" in tracks:
        melody_instruments.add("piano_s")
    if not melody_instruments and tracks:
        melody_instruments.add(list(tracks.keys())[0])

    bass_instruments = {"cello", "bass", "bassoon", "tuba", "trombone", "piano_lh", "piano_b"}

    for inst_name, notes in tracks.items():
        if not notes:
            continue
        is_melody = inst_name in melody_instruments
        is_bass = inst_name in bass_instruments

        notes.sort(key=lambda n: n.start_time_sec)

        for note in notes:
            t = note.start_time_sec / total_time
            tension = _tension_curve(t)

            base_vel = vel_start + (vel_end - vel_start) * t
            vel = base_vel + tension * (vel_climax - base_vel)

            vel += (15 if is_melody else -10)

            beat_in_bar = (note.start_time_sec / sec_per_beat) % 4
            if beat_in_bar < 0.5:
                vel += 8
            elif 1.5 < beat_in_bar < 2.5:
                vel += 4

            note.velocity = max(1, min(127, int(vel)))
            note.articulation = art
            note.dynamic = dyn

            register_shift = int(tension * min(max_register_shift, 2))
            if is_melody and register_shift > 0:
                note.midi_pitch = min(127, note.midi_pitch + register_shift)
            elif is_bass and register_shift > 0:
                note.midi_pitch = max(0, note.midi_pitch - register_shift)

    return tracks
