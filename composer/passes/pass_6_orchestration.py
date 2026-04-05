"""PASS 6: Orchestration, density ramping, and phrase breathing."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from SYSTEM_ARCHITECTURE import (
    FormIR, VoiceLeadingIR, MelodicNote,
    PerformanceNote,
)
from composer._rng import rng
from composer.parser import INSTRUMENT_RANGES
from sacred_composer.constants import PHI_INVERSE


def pass_6_orchestration(vl_ir: VoiceLeadingIR, form_ir: FormIR
                         ) -> Dict[str, List[PerformanceNote]]:
    """
    PASS 6: Assign SATB voices to instruments with range checking.

    Piano: soprano+alto in right hand, tenor+bass in left hand.
    String quartet: violin1=soprano, violin2=alto, viola=tenor, cello=bass.
    Orchestra: doubled assignments with octave transposition.
    """
    instrumentation = form_ir.instrumentation
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo

    tracks: Dict[str, List[PerformanceNote]] = defaultdict(list)

    doublings_map: Dict[str, List[Tuple[str, int]]] = {}

    if set(instrumentation) == {"piano"}:
        voice_map = {"soprano": "piano_s", "alto": "piano_a",
                     "tenor": "piano_t", "bass": "piano_b"}
    elif len(instrumentation) > 4 and "violin1" in instrumentation:
        voice_map = {
            "soprano": "violin1",
            "alto": "violin2" if "violin2" in instrumentation else "viola",
            "tenor": "viola",
            "bass": "cello",
        }
        assigned = set(voice_map.values())
        remaining = [inst for inst in instrumentation if inst not in assigned]
        soprano_doublers = [i for i in remaining if i in ("flute", "oboe", "clarinet", "trumpet")]
        alto_doublers = [i for i in remaining if i in ("clarinet", "horn") and i not in soprano_doublers]
        tenor_doublers = [i for i in remaining if i in ("horn", "bassoon", "trombone") and i not in soprano_doublers and i not in alto_doublers]
        bass_doublers = [i for i in remaining if i in ("bass", "bassoon", "tuba", "trombone") and i not in soprano_doublers and i not in alto_doublers and i not in tenor_doublers]
        all_doubled = set(soprano_doublers + alto_doublers + tenor_doublers + bass_doublers)
        unassigned = [i for i in remaining if i not in all_doubled]
        for idx, inst in enumerate(unassigned):
            if idx % 2 == 0:
                bass_doublers.append(inst)
            else:
                tenor_doublers.append(inst)

        for inst in soprano_doublers:
            doublings_map.setdefault("soprano", []).append((inst, 0))
        for inst in alto_doublers:
            doublings_map.setdefault("alto", []).append((inst, 0))
        for inst in tenor_doublers:
            doublings_map.setdefault("tenor", []).append((inst, 0))
        for inst in bass_doublers:
            doublings_map.setdefault("bass", []).append((inst, 0))
    elif "violin1" in instrumentation and "cello" in instrumentation:
        voice_map = {
            "soprano": "violin1",
            "alto": instrumentation[1] if len(instrumentation) > 1 else "violin1",
            "tenor": instrumentation[2] if len(instrumentation) > 2 else "viola",
            "bass": instrumentation[3] if len(instrumentation) > 3 else "cello",
        }
    else:
        voice_map = {}
        voices = ["soprano", "alto", "tenor", "bass"]
        for i, v in enumerate(voices):
            voice_map[v] = instrumentation[i % len(instrumentation)]

    def _clamp_to_range(midi_val: int, inst: str) -> int:
        lo, hi = INSTRUMENT_RANGES.get(inst, (21, 108))
        while midi_val < lo and midi_val + 12 <= 127:
            midi_val += 12
        while midi_val > hi and midi_val - 12 >= 0:
            midi_val -= 12
        return max(lo, min(hi, midi_val))

    for chord_evt in vl_ir.chords:
        start_sec = ((chord_evt.bar - 1) * 4 + (chord_evt.beat - 1)) * sec_per_beat
        dur_sec = chord_evt.duration_beats * sec_per_beat

        voice_data = [
            ("soprano", chord_evt.soprano),
            ("alto", chord_evt.alto),
            ("tenor", chord_evt.tenor),
            ("bass", chord_evt.bass),
        ]

        for voice_name, midi_val in voice_data:
            if midi_val == 0:
                continue
            inst = voice_map[voice_name]
            clamped = _clamp_to_range(midi_val, inst)

            pn = PerformanceNote(
                midi_pitch=clamped,
                start_time_sec=start_sec,
                duration_sec=dur_sec,
                velocity=80,
                channel=0,
                instrument=inst,
            )
            tracks[inst].append(pn)

            for dbl_inst, oct_offset in doublings_map.get(voice_name, []):
                dbl_midi = _clamp_to_range(midi_val + oct_offset * 12, dbl_inst)
                dpn = PerformanceNote(
                    midi_pitch=dbl_midi,
                    start_time_sec=start_sec,
                    duration_sec=dur_sec,
                    velocity=70,
                    channel=0,
                    instrument=dbl_inst,
                )
                tracks[dbl_inst].append(dpn)

    melody_inst = voice_map["soprano"]
    for mn in vl_ir.melody:
        if mn.is_chord_tone:
            continue
        start_sec = ((mn.bar - 1) * 4 + (mn.beat - 1)) * sec_per_beat
        dur_sec = mn.duration_beats * sec_per_beat
        midi_val = _clamp_to_range(mn.midi, melody_inst)
        pn = PerformanceNote(
            midi_pitch=midi_val,
            start_time_sec=start_sec,
            duration_sec=dur_sec,
            velocity=80,
            channel=0,
            instrument=melody_inst,
        )
        tracks[melody_inst].append(pn)

    if "piano" in instrumentation:
        _add_piano_accompaniment(vl_ir, tracks, form_ir)

    return dict(tracks)


def _add_piano_accompaniment(vl_ir: VoiceLeadingIR,
                             tracks: Dict[str, List[PerformanceNote]],
                             form_ir: FormIR):
    """Add Alberti bass figuration for piano pieces."""
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo

    for chord_evt in vl_ir.chords:
        bass = chord_evt.bass
        tenor = chord_evt.tenor if chord_evt.tenor != 0 else bass + 7
        alto = chord_evt.alto if chord_evt.alto != 0 else bass + 4

        bass_oct = max(36, bass - 12) if bass > 48 else bass
        third = max(36, min(72, (bass_oct + tenor) // 2))
        fifth = max(36, min(72, (third + bass_oct + 7) // 2))

        pattern_notes = [bass_oct, fifth, third, fifth]

        bar_start_sec = ((chord_evt.bar - 1) * 4 + (chord_evt.beat - 1)) * sec_per_beat
        eighth_dur = sec_per_beat * 0.5

        for step in range(min(int(chord_evt.duration_beats * 2), len(pattern_notes) * 2)):
            idx = step % len(pattern_notes)
            pn = PerformanceNote(
                midi_pitch=max(21, min(108, pattern_notes[idx])),
                start_time_sec=bar_start_sec + step * eighth_dur,
                duration_sec=eighth_dur * 0.9,
                velocity=60,
                channel=0,
                instrument="piano_b",
            )
            tracks["piano_b"].append(pn)


def pass_6_orchestration_fugue(vl_ir: VoiceLeadingIR, form_ir: FormIR
                                ) -> Dict[str, List[PerformanceNote]]:
    """
    PASS 6 (Fugue variant): Assign 3 fugue voices to piano tracks.
    """
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo

    tracks: Dict[str, List[PerformanceNote]] = defaultdict(list)

    voice_to_track = {
        "soprano": "piano_s",
        "alto": "piano_a",
        "bass": "piano_b",
    }

    def _add_notes(notes: List[MelodicNote], inst: str):
        lo, hi = INSTRUMENT_RANGES.get(inst, (21, 108))
        for mn in notes:
            start_sec = ((mn.bar - 1) * 4 + (mn.beat - 1)) * sec_per_beat
            dur_sec = mn.duration_beats * sec_per_beat
            pitch = max(lo, min(hi, mn.midi))
            pn = PerformanceNote(
                midi_pitch=pitch,
                start_time_sec=start_sec,
                duration_sec=dur_sec,
                velocity=75,
                channel=0,
                instrument=inst,
            )
            tracks[inst].append(pn)

    _add_notes(vl_ir.melody, voice_to_track["soprano"])

    alto_notes = vl_ir.inner_voices.get("alto", [])
    _add_notes(alto_notes, voice_to_track["alto"])

    _add_notes(vl_ir.bass_line, voice_to_track["bass"])

    return dict(tracks)


# ============================================================================
# Section boundary density ramping
# ============================================================================

def _smooth_section_transitions(
    tracks: Dict[str, List[PerformanceNote]],
    form_ir: FormIR,
) -> Dict[str, List[PerformanceNote]]:
    """
    Smooth out abrupt note-density jumps at section boundaries.
    """
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    ramp_bars = 2

    boundary_times = []
    bar_cursor = 0
    for sec in form_ir.sections:
        for sub in sec.subsections:
            bar_cursor += sub.bars
            t = (bar_cursor - 1) * 4 * sec_per_beat
            boundary_times.append(t)

    ramp_dur = ramp_bars * 4 * sec_per_beat

    accomp_keys = [k for k in tracks.keys() if any(
        tag in k.lower() for tag in ("_b", "_lh", "_a", "_t", "bass",
                                      "alberti", "viola", "cello",
                                      "violin2"))]

    for inst_name in accomp_keys:
        floor = 0.3
        new_notes = []
        for n in tracks[inst_name]:
            keep = True
            for bt in boundary_times:
                if bt - ramp_dur <= n.start_time_sec < bt:
                    progress = (bt - n.start_time_sec) / ramp_dur
                    keep_prob = floor + (1.0 - floor) * progress
                    if rng().random() > keep_prob:
                        keep = False
                        break
                elif bt <= n.start_time_sec < bt + ramp_dur:
                    progress = (n.start_time_sec - bt) / ramp_dur
                    keep_prob = floor + (1.0 - floor) * progress
                    if rng().random() > keep_prob:
                        keep = False
                        break
            if keep:
                new_notes.append(n)
        tracks[inst_name] = new_notes

    return tracks


# ============================================================================
# Phrase breathing
# ============================================================================

def _find_cadence_times(vl_ir: VoiceLeadingIR, form_ir: FormIR) -> List[float]:
    """Return absolute times (in seconds) of cadential chord events."""
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    cadence_times = []
    for ce in vl_ir.chords:
        if ce.is_cadential:
            t = ((ce.bar - 1) * 4 + (ce.beat - 1)) * sec_per_beat
            cadence_times.append(t)
    return sorted(cadence_times)


def pass_6b_phrase_breathing(
    tracks: Dict[str, List[PerformanceNote]],
    vl_ir: VoiceLeadingIR,
    form_ir: FormIR,
) -> Dict[str, List[PerformanceNote]]:
    """
    Insert musical breathing into the continuous note stream.
    """
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    total_bars = form_ir.total_bars
    total_time = total_bars * 4 * sec_per_beat

    cadence_times = _find_cadence_times(vl_ir, form_ir)
    if not cadence_times and vl_ir.chords:
        bar_cursor = 0
        for sec in form_ir.sections:
            for sub in sec.subsections:
                bar_cursor += sub.bars
                t = (bar_cursor - 1) * 4 * sec_per_beat
                cadence_times.append(t)

    tolerance = sec_per_beat * 1.5

    gp_time = total_time * PHI_INVERSE
    gp_duration = sec_per_beat * 1.0

    for inst_name, notes in tracks.items():
        if not notes:
            continue
        notes.sort(key=lambda n: n.start_time_sec)

        for cad_t in cadence_times:
            cad_idx = None
            best_dist = float("inf")
            for i, n in enumerate(notes):
                note_end = n.start_time_sec + n.duration_sec
                dist = abs(note_end - (cad_t + sec_per_beat))
                if dist < best_dist and dist < tolerance:
                    best_dist = dist
                    cad_idx = i

            if cad_idx is None:
                continue

            if cad_idx >= 1:
                pre_note = notes[cad_idx - 1]
                pre_note.duration_sec *= 1.5

            cad_note = notes[cad_idx]
            rest_beats = rng().uniform(0.5, 1.0)
            rest_sec = rest_beats * sec_per_beat
            original_end = cad_note.start_time_sec + cad_note.duration_sec
            cad_note.duration_sec = max(
                sec_per_beat * 0.5,
                cad_note.duration_sec - rest_sec * 0.5,
            )
            gap_end = original_end + rest_sec
            for j in range(cad_idx + 1, len(notes)):
                if notes[j].start_time_sec < gap_end:
                    shift = gap_end - notes[j].start_time_sec
                    notes[j].start_time_sec += shift

        gp_start = gp_time
        gp_end = gp_time + gp_duration
        for n in notes:
            note_end = n.start_time_sec + n.duration_sec
            if n.start_time_sec < gp_start and note_end > gp_start:
                n.duration_sec = max(0.05, gp_start - n.start_time_sec)
            elif gp_start <= n.start_time_sec < gp_end:
                shift = gp_end - n.start_time_sec
                n.start_time_sec += shift

        max_continuous_sec = 4 * 4 * sec_per_beat
        min_rest_sec = 1.5 * sec_per_beat
        if len(notes) >= 2:
            phrase_start = notes[0].start_time_sec
            for i in range(1, len(notes)):
                gap = notes[i].start_time_sec - (notes[i - 1].start_time_sec + notes[i - 1].duration_sec)
                if gap >= min_rest_sec:
                    phrase_start = notes[i].start_time_sec
                elif notes[i].start_time_sec - phrase_start > max_continuous_sec:
                    notes[i - 1].duration_sec = max(
                        0.05,
                        notes[i - 1].duration_sec - min_rest_sec,
                    )
                    phrase_start = notes[i].start_time_sec

    return tracks
