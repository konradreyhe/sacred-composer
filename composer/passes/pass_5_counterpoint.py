"""PASS 5: Counterpoint (fill alto + tenor, check parallels)."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)

from music21 import key as m21key, roman

from SYSTEM_ARCHITECTURE import (
    FormIR, VoiceLeadingIR, MelodicNote,
)
from composer.voice_leader import VoiceLeader
from composer.parser import _KEY_TO_M21
from composer.helpers.flocking import flocking_voice_force


def pass_5_counterpoint(vl_ir: VoiceLeadingIR, form_ir: FormIR) -> VoiceLeadingIR:
    """
    PASS 5: Add inner voices (alto, tenor) using optimal voice leading.

    For each chord event:
      1. Soprano and bass come from schema realization (Passes 3-4).
      2. Realize the Roman numeral to get available pitch classes.
      3. Place alto and tenor to minimize movement, avoid parallel 5ths/8ves.
    """
    m21_key_str = _KEY_TO_M21.get(form_ir.home_key, "C")
    key_obj = m21key.Key(m21_key_str)
    voice_leader = VoiceLeader()

    # Voice ranges (MIDI)
    alto_range = (55, 76)
    tenor_range = (48, 69)

    prev_voicing = None

    for chord_evt in vl_ir.chords:
        soprano = chord_evt.soprano if chord_evt.soprano != 0 else 72
        bass = chord_evt.bass if chord_evt.bass != 0 else 48

        available_pcs = _resolve_available_pitch_classes(
            chord_evt, bass, m21_key_str,
        )
        avg_outer_direction = _outer_voice_direction(
            soprano, bass, prev_voicing,
        )
        best_alto, best_tenor = _pick_best_inner_voicing(
            soprano, bass, available_pcs,
            alto_range, tenor_range, prev_voicing,
            voice_leader, avg_outer_direction,
        )

        chord_evt.soprano = soprano
        chord_evt.alto = best_alto
        chord_evt.tenor = best_tenor
        chord_evt.bass = bass

        prev_voicing = (soprano, best_alto, best_tenor, bass)

    _populate_inner_and_bass_lines(vl_ir)
    return vl_ir


def _resolve_available_pitch_classes(
    chord_evt, bass: int, default_m21_key_str: str,
) -> list[int]:
    """Realize a Roman numeral to its pitch classes; fall back to a bass triad."""
    try:
        local_key_str = _KEY_TO_M21.get(chord_evt.key, default_m21_key_str)
        rn = roman.RomanNumeral(chord_evt.roman_numeral, m21key.Key(local_key_str))
        return [p.pitchClass for p in rn.pitches]
    except (KeyError, ValueError, AttributeError) as exc:
        _log.debug("roman numeral parse failed for %r: %s; "
                   "falling back to triad from bass",
                   chord_evt.roman_numeral, exc)
        return [bass % 12, (bass + 4) % 12, (bass + 7) % 12]


def _outer_voice_direction(
    soprano: int, bass: int, prev_voicing: Optional[Tuple[int, int, int, int]],
) -> float:
    if not prev_voicing:
        return 0.0
    soprano_dir = soprano - prev_voicing[0]
    bass_dir = bass - prev_voicing[3]
    return (soprano_dir + bass_dir) / 2.0


def _chord_tones_in_range(
    available_pcs: list[int], voice_range: Tuple[int, int],
) -> list[int]:
    lo, hi = voice_range
    return [m for pc in available_pcs for m in range(lo, hi + 1) if m % 12 == pc]


def _pick_best_inner_voicing(
    soprano: int, bass: int, available_pcs: list[int],
    alto_range: Tuple[int, int], tenor_range: Tuple[int, int],
    prev_voicing: Optional[Tuple[int, int, int, int]],
    voice_leader, avg_outer_direction: float,
) -> Tuple[int, int]:
    """Exhaustive search for the lowest-cost (alto, tenor) pair."""
    alto_chord_tones = _chord_tones_in_range(available_pcs, alto_range)
    tenor_chord_tones = _chord_tones_in_range(available_pcs, tenor_range)

    best_alto: Optional[int] = None
    best_tenor: Optional[int] = None
    best_cost = float("inf")

    for pc in available_pcs:
        for alto_midi in range(alto_range[0], alto_range[1] + 1):
            if alto_midi % 12 != pc:
                continue
            if alto_midi >= soprano or alto_midi <= bass:
                continue
            for pc2 in available_pcs:
                for tenor_midi in range(tenor_range[0], tenor_range[1] + 1):
                    if tenor_midi % 12 != pc2:
                        continue
                    if tenor_midi >= alto_midi or tenor_midi <= bass:
                        continue
                    cost = _score_inner_voicing(
                        soprano, alto_midi, tenor_midi, bass,
                        prev_voicing, voice_leader,
                        alto_chord_tones, tenor_chord_tones,
                        avg_outer_direction,
                    )
                    if cost < best_cost:
                        best_cost = cost
                        best_alto = alto_midi
                        best_tenor = tenor_midi

    # Fallback if nothing found
    if best_alto is None:
        best_alto = max(alto_range[0], min(alto_range[1], (soprano + bass) // 2 + 2))
    if best_tenor is None:
        best_tenor = max(tenor_range[0], min(tenor_range[1], (soprano + bass) // 2 - 3))
    return best_alto, best_tenor


def _score_inner_voicing(
    soprano: int, alto_midi: int, tenor_midi: int, bass: int,
    prev_voicing: Optional[Tuple[int, int, int, int]],
    voice_leader,
    alto_chord_tones: list[int], tenor_chord_tones: list[int],
    avg_outer_direction: float,
) -> float:
    voicing = (soprano, alto_midi, tenor_midi, bass)
    cost: float = 0

    if prev_voicing:
        cost += abs(alto_midi - prev_voicing[1])
        cost += abs(tenor_midi - prev_voicing[2])
        if voice_leader.has_parallel_fifths_or_octaves(prev_voicing, voicing):
            cost += 1000

    if soprano - alto_midi > 12:
        cost += 500
    if alto_midi - tenor_midi > 12:
        cost += 500

    nearest_alto_ct = (min(alto_chord_tones, key=lambda t: abs(t - alto_midi))
                       if alto_chord_tones else alto_midi)
    alto_force = flocking_voice_force(
        alto_midi,
        other_voices=[soprano, tenor_midi, bass],
        nearest_chord_tone=nearest_alto_ct,
        avg_melodic_direction=avg_outer_direction,
    )
    nearest_tenor_ct = (min(tenor_chord_tones, key=lambda t: abs(t - tenor_midi))
                        if tenor_chord_tones else tenor_midi)
    tenor_force = flocking_voice_force(
        tenor_midi,
        other_voices=[soprano, alto_midi, bass],
        nearest_chord_tone=nearest_tenor_ct,
        avg_melodic_direction=avg_outer_direction,
    )
    cost += abs(alto_force) * 2.0
    cost += abs(tenor_force) * 2.0
    return cost


def _populate_inner_and_bass_lines(vl_ir: VoiceLeadingIR) -> None:
    alto_notes = []
    tenor_notes = []
    for ce in vl_ir.chords:
        alto_notes.append(MelodicNote(
            midi=ce.alto, bar=ce.bar, beat=ce.beat,
            duration_beats=ce.duration_beats, is_chord_tone=True,
        ))
        tenor_notes.append(MelodicNote(
            midi=ce.tenor, bar=ce.bar, beat=ce.beat,
            duration_beats=ce.duration_beats, is_chord_tone=True,
        ))
    vl_ir.inner_voices = {"alto": alto_notes, "tenor": tenor_notes}
    vl_ir.bass_line = [
        MelodicNote(midi=ce.bass, bar=ce.bar, beat=ce.beat,
                    duration_beats=ce.duration_beats, is_chord_tone=True)
        for ce in vl_ir.chords
    ]
