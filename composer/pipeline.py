"""
MASTER PIPELINE: 9-pass orchestrator, MIDI export, post-processing fixes.
"""

from __future__ import annotations

import os
import random
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
from midiutil import MIDIFile
from music21 import (
    interval as m21interval,
    key as m21key,
    note as m21note,
    pitch as m21pitch,
    stream,
)

from SYSTEM_ARCHITECTURE import (
    FormIR, FormType, VoiceLeadingIR, MelodicNote,
    PerformanceIR, PerformanceNote, CadenceType, SchemaToken,
    KeyToken,
)
from classical_music_gen import VoiceLeader

from composer.parser import (
    parse_prompt, _KEY_TO_M21, MIDI_PROGRAMS, _INST_VOICE_ORDER,
    INSTRUMENT_RANGES, SAMPLE_PROMPTS,
    _key_is_minor, _relative_major, _subdominant_key,
)
from composer.passes.pass_1_plan import pass_1_plan
from composer.passes.pass_2_schema import pass_2_schema, pass_2_schema_fugue
from composer.passes.pass_3_harmony import pass_3_harmony
from composer.passes.pass_4_melody import (
    pass_4_melody, pass_4_melody_fugue,
    _apply_rondo_refrain_replay, _apply_ternary_refrain_replay,
)
from composer.passes.pass_5_counterpoint import pass_5_counterpoint
from composer.passes.pass_6_orchestration import (
    pass_6_orchestration, pass_6_orchestration_fugue,
    _smooth_section_transitions, pass_6b_phrase_breathing,
)
from composer.passes.pass_7_expression import pass_7_expression
from composer.passes.pass_8_humanization import pass_8_humanization
from composer.passes.pass_9_validation import pass_9_validation, ValidationReport
from sacred_composer.constants import PHI_INVERSE

import logging
_log = logging.getLogger(__name__)


# =============================================================================
# POST-PROCESSING FIXES
# =============================================================================

def fix_augmented_intervals(notes: List[MelodicNote], key_token: KeyToken) -> List[MelodicNote]:
    """
    Fix augmented melodic intervals (tritones = 6 semitones, augmented 2nds = 3
    semitones in minor keys).
    """
    for i in range(1, len(notes)):
        p1 = m21pitch.Pitch(midi=notes[i - 1].midi)
        p2 = m21pitch.Pitch(midi=notes[i].midi)
        try:
            ivl = m21interval.Interval(p1, p2)
            if ivl.specifier == m21interval.Specifier.AUGMENTED:
                direction = 1 if notes[i].midi > notes[i - 1].midi else -1
                fixed = False
                for delta in (-1, 1):
                    candidate = notes[i].midi + delta
                    p2c = m21pitch.Pitch(midi=candidate)
                    try:
                        ivl2 = m21interval.Interval(p1, p2c)
                        if ivl2.specifier != m21interval.Specifier.AUGMENTED:
                            notes[i].midi = candidate
                            fixed = True
                            break
                    except (ValueError, TypeError) as exc:
                        _log.debug("candidate interval rejected: %s", exc)
                        continue
                if not fixed:
                    notes[i].midi -= direction
        except (ValueError, TypeError) as exc:
            _log.debug("interval analysis skipped for pair %d: %s", i, exc)
    return notes


def fix_leading_tone_resolution(vl_ir: VoiceLeadingIR, key_token: KeyToken) -> VoiceLeadingIR:
    """Ensure leading tones resolve up by semitone to the tonic."""
    lt_pairs = set()
    for ce in vl_ir.chords:
        local_key_str = _KEY_TO_M21.get(ce.key, "C")
        local_key_obj = m21key.Key(local_key_str)
        tonic_pc = local_key_obj.tonic.pitchClass
        lt_pc = (tonic_pc - 1) % 12
        lt_pairs.add((lt_pc, tonic_pc))
    home_key_str = _KEY_TO_M21.get(key_token, "C")
    home_key_obj = m21key.Key(home_key_str)
    home_tonic_pc = home_key_obj.tonic.pitchClass
    home_lt_pc = (home_tonic_pc - 1) % 12
    lt_pairs.add((home_lt_pc, home_tonic_pc))

    chords = vl_ir.chords
    for i in range(len(chords) - 1):
        curr = chords[i]
        nxt = chords[i + 1]
        is_strong = (curr.beat <= 1.5 or abs(curr.beat - 3.0) < 0.5)
        if not is_strong and not curr.is_cadential:
            continue
        for voice_attr in ("soprano", "alto", "tenor", "bass"):
            curr_midi = getattr(curr, voice_attr)
            curr_pc = curr_midi % 12
            for lt_pc, tonic_pc in lt_pairs:
                if curr_pc == lt_pc:
                    target = curr_midi + 1
                    if target % 12 == tonic_pc:
                        setattr(nxt, voice_attr, target)
                    break
    return vl_ir


def fix_seventh_resolution(vl_ir: VoiceLeadingIR) -> VoiceLeadingIR:
    """Ensure chord 7ths resolve downward by step."""
    chords = vl_ir.chords
    for i in range(len(chords) - 1):
        curr = chords[i]
        nxt = chords[i + 1]
        bass = curr.bass
        if bass == 0:
            continue
        is_strong = (curr.beat <= 1.5 or abs(curr.beat - 3.0) < 0.5)
        if not is_strong:
            continue
        for voice_attr in ("soprano", "alto", "tenor"):
            curr_midi = getattr(curr, voice_attr)
            if curr_midi == 0:
                continue
            interval_above_bass = (curr_midi - bass) % 12
            if interval_above_bass in (10, 11):
                nxt_midi = getattr(nxt, voice_attr)
                motion = nxt_midi - curr_midi
                if motion > 2:
                    setattr(nxt, voice_attr, curr_midi - random.choice([1, 2]))
    return vl_ir


def fix_leap_recovery(notes: List[MelodicNote], recovery_pct: float = 0.85) -> List[MelodicNote]:
    """After any melodic leap of 4+ semitones, the next note should step back."""
    for i in range(1, len(notes) - 1):
        leap = notes[i].midi - notes[i - 1].midi
        if abs(leap) >= 4:
            recovery = notes[i + 1].midi - notes[i].midi
            opposite_direction = -1 if leap > 0 else 1
            already_recovered = (
                recovery * opposite_direction > 0 and abs(recovery) <= 2
            )
            if not already_recovered and random.random() < recovery_pct:
                step_size = random.choice([1, 2])
                notes[i + 1].midi = notes[i].midi + opposite_direction * step_size
    return notes


def _fix_melody_voice_spacing(vl_ir: VoiceLeadingIR) -> None:
    """Constrain melody notes so they don't cross below the alto voice."""
    if not vl_ir.melody or not vl_ir.chords:
        return

    alto_at: Dict[Tuple[int, float], int] = {}
    for ce in vl_ir.chords:
        alto_at[(ce.bar, ce.beat)] = ce.alto

    for mn in vl_ir.melody:
        best_alto = None
        best_dist = float("inf")
        for (b, bt), a_midi in alto_at.items():
            abs_pos = (b - 1) * 4 + bt
            mn_pos = (mn.bar - 1) * 4 + mn.beat
            dist = mn_pos - abs_pos
            if 0 <= dist < best_dist:
                best_dist = dist
                best_alto = a_midi
        if best_alto is None:
            continue
        if mn.midi < best_alto + 1:
            mn.midi = best_alto + 1
        if mn.midi > best_alto + 10:
            mn.midi = best_alto + 10


def fix_voice_crossing(vl_ir: VoiceLeadingIR) -> VoiceLeadingIR:
    """Ensure register order soprano >= alto >= tenor >= bass."""
    for chord_evt in vl_ir.chords:
        voices = [chord_evt.soprano, chord_evt.alto, chord_evt.tenor, chord_evt.bass]
        changed = True
        while changed:
            changed = False
            for j in range(len(voices) - 1):
                if voices[j] < voices[j + 1]:
                    voices[j], voices[j + 1] = voices[j + 1], voices[j]
                    changed = True
        chord_evt.soprano = voices[0]
        chord_evt.alto = voices[1]
        chord_evt.tenor = voices[2]
        chord_evt.bass = voices[3]

    alto_notes = vl_ir.inner_voices.get("alto", [])
    tenor_notes = vl_ir.inner_voices.get("tenor", [])
    for k in range(min(len(alto_notes), len(tenor_notes))):
        if alto_notes[k].midi < tenor_notes[k].midi:
            alto_notes[k].midi, tenor_notes[k].midi = (
                tenor_notes[k].midi, alto_notes[k].midi
            )
    return vl_ir


def mark_cadence_positions(vl_ir: VoiceLeadingIR, schema_ir) -> VoiceLeadingIR:
    """Mark cadence positions at the end of each schema sequence."""
    cadence_bars: set = set()
    running_bar = 1
    for sub_schema in schema_ir.schema_plan:
        for slot in sub_schema.schema_sequence:
            if isinstance(slot.schema, CadenceType):
                cadence_bars.add(running_bar)
            else:
                running_bar += slot.bars
        cadence_bars.add(running_bar)

    for chord_evt in vl_ir.chords:
        if chord_evt.bar in cadence_bars:
            chord_evt.is_cadential = True

    return vl_ir


# =============================================================================
# MIDI EXPORT
# =============================================================================

def export_midi(perf_ir: PerformanceIR, output_path: str,
                tempo_bpm: int = 120) -> str:
    """Convert PerformanceIR to a multi-track MIDI file."""
    instruments = sorted(set(n.instrument for n in perf_ir.notes),
                         key=lambda i: _INST_VOICE_ORDER.get(i, 99))
    if not instruments:
        print("  [MIDI] Warning: no notes to export!")
        return output_path

    inst_to_track = {inst: i for i, inst in enumerate(instruments)}
    midi = MIDIFile(numTracks=len(instruments), ticks_per_quarternote=480,
                    deinterleave=False)
    midi.addTempo(0, 0, tempo_bpm)

    for inst in instruments:
        track = inst_to_track[inst]
        channel = track % 16
        if channel == 9:
            channel = 10
        program = MIDI_PROGRAMS.get(inst, 0)
        midi.addTrackName(track, 0, inst)
        midi.addProgramChange(track, channel, 0, program)

    seen_keys: set = set()
    for note in perf_ir.notes:
        track = inst_to_track.get(note.instrument, 0)
        channel = track % 16
        if channel == 9:
            channel = 10
        beat_time = note.start_time_sec * tempo_bpm / 60.0
        duration_beats = note.duration_sec * tempo_bpm / 60.0

        pitch = max(0, min(127, note.midi_pitch))
        time_key = round(beat_time, 4)
        dedup_key = (track, channel, pitch, time_key)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        midi.addNote(
            track=track,
            channel=channel,
            pitch=pitch,
            time=max(0, beat_time),
            duration=max(0.01, duration_beats),
            volume=max(1, min(127, note.velocity)),
        )

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    return output_path


# =============================================================================
# QUALITY REPORT
# =============================================================================

def print_quality_report(perf_ir: PerformanceIR, form_ir: FormIR):
    """Print a quality summary."""
    try:
        from evaluation_framework import EvaluationReport
        score = _perf_ir_to_music21_score(perf_ir, form_ir)
        from evaluation_framework import (
            rule_parallel_fifths, rule_parallel_octaves, rule_voice_range
        )
        violations = []
        violations.extend(rule_parallel_fifths(score))
        violations.extend(rule_parallel_octaves(score))
        violations.extend(rule_voice_range(score))
        print(f"\n  Evaluation Framework Results:")
        print(f"    Parallel 5ths violations:  {sum(1 for v in violations if v.rule_name == 'parallel_5ths')}")
        print(f"    Parallel 8ves violations:  {sum(1 for v in violations if v.rule_name == 'parallel_octaves')}")
        print(f"    Voice range violations:    {sum(1 for v in violations if v.rule_name == 'voice_range')}")
        print(f"    Total Level-1 violations:  {len(violations)}")
    except Exception as e:
        print(f"\n  [Note] Could not run full evaluation framework: {e}")
        print(f"  Using Pass 9 validation report instead.")


def _perf_ir_to_music21_score(perf_ir: PerformanceIR, form_ir: FormIR) -> stream.Score:
    """Build a minimal music21 Score from PerformanceIR for evaluation."""
    score = stream.Score()
    instruments = sorted(set(n.instrument for n in perf_ir.notes),
                         key=lambda i: _INST_VOICE_ORDER.get(i, 99))
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo

    for inst in instruments:
        part = stream.Part()
        part.id = inst
        inst_notes = sorted(
            [n for n in perf_ir.notes if n.instrument == inst],
            key=lambda n: n.start_time_sec,
        )
        for pn in inst_notes:
            offset_beats = pn.start_time_sec / sec_per_beat
            dur_beats = max(0.25, pn.duration_sec / sec_per_beat)
            n = m21note.Note(pn.midi_pitch)
            n.quarterLength = dur_beats
            part.insert(offset_beats, n)
        score.insert(0, part)
    return score


# =============================================================================
# COMPOSE (main pipeline)
# =============================================================================

def compose(prompt: str, output_file: str = "composed_output.mid",
            seed: Optional[int] = None) -> Tuple[PerformanceIR, FormIR, ValidationReport]:
    """
    The complete end-to-end composition pipeline.

    Input:  A natural-language prompt string.
    Output: (PerformanceIR, FormIR, ValidationReport) + MIDI file on disk.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    print("=" * 60)
    print("  CLASSICAL MUSIC COMPOSITION PIPELINE")
    print("=" * 60)
    print(f"\n  Prompt: \"{prompt}\"\n")

    # Parse the text prompt into a structured plan
    parsed = parse_prompt(prompt)
    print(f"  Parsed: form={parsed['form'].value}, key={parsed['home_key'].value}, "
          f"character={parsed['character'].value}, bars={parsed['total_bars']}, "
          f"instruments={parsed['instrumentation']}")

    # --- Pass 1: Plan ---
    print(f"\n[Pass 1] Planning form structure...")
    form_ir = pass_1_plan(parsed)
    print(f"  Form: {form_ir.form.value}, {form_ir.total_bars} bars, "
          f"{len(form_ir.sections)} sections")
    for sec in form_ir.sections:
        sub_str = ", ".join(f"{s.type.value}({s.bars}b)" for s in sec.subsections)
        print(f"    {sec.type.value}: [{sub_str}]")

    # --- Pass 2: Schema ---
    is_fugue = (form_ir.form == FormType.FUGUE)
    print(f"\n[Pass 2] Filling sections with {'fugue harmonic plan' if is_fugue else 'galant schemata'}...")
    schema_ir = pass_2_schema_fugue(form_ir) if is_fugue else pass_2_schema(form_ir)
    total_schemas = sum(len(s.schema_sequence) for s in schema_ir.schema_plan)
    print(f"  Total schema slots: {total_schemas}")
    for sub_schema in schema_ir.schema_plan:
        names = [s.schema.value if hasattr(s.schema, 'value') else str(s.schema)
                 for s in sub_schema.schema_sequence]
        print(f"    {sub_schema.subsection_ref.type.value}: {' -> '.join(names)}")

    # --- Pass 3: Harmony ---
    print(f"\n[Pass 3] Realizing harmony (Roman numerals -> chords)...")
    vl_ir = pass_3_harmony(schema_ir)
    print(f"  Chord events: {len(vl_ir.chords)}")
    for ce in vl_ir.chords[:6]:
        print(f"    Bar {ce.bar} beat {ce.beat}: {ce.roman_numeral} in {ce.key.value} "
              f"[S={ce.soprano} B={ce.bass}]")
    if len(vl_ir.chords) > 6:
        print(f"    ... ({len(vl_ir.chords) - 6} more)")

    # --- Fix 5: Mark explicit cadence positions (before melody pass) ---
    vl_ir = mark_cadence_positions(vl_ir, schema_ir)
    cadence_marked = sum(1 for ce in vl_ir.chords if ce.is_cadential)
    print(f"  Cadence positions marked: {cadence_marked}")

    # --- Pass 4: Melody ---
    if is_fugue:
        print(f"\n[Pass 4] Generating 3-voice fugue texture...")
        vl_ir = pass_4_melody_fugue(vl_ir, form_ir)
    else:
        print(f"\n[Pass 4] Generating melodic lines...")
        vl_ir = pass_4_melody(vl_ir, form_ir)
    print(f"  Melody notes: {len(vl_ir.melody)}")
    ct = sum(1 for m in vl_ir.melody if m.is_chord_tone)
    nct = len(vl_ir.melody) - ct
    print(f"    Chord tones: {ct}, Non-chord tones: {nct}")

    # --- Rondo refrain replay ---
    if form_ir.form == FormType.RONDO:
        vl_ir = _apply_rondo_refrain_replay(vl_ir, form_ir)

    # --- Ternary refrain replay ---
    if form_ir.form == FormType.TERNARY:
        vl_ir = _apply_ternary_refrain_replay(vl_ir, form_ir)

    # --- Fix 1: Augmented intervals in melody ---
    vl_ir.melody = fix_augmented_intervals(vl_ir.melody, form_ir.home_key)
    print(f"  [Fix] Augmented intervals cleaned in melody")

    # --- Fix 3: Leap recovery in melody ---
    vl_ir.melody = fix_leap_recovery(vl_ir.melody)
    print(f"  [Fix] Leap recovery applied to melody")

    # For fugue: also fix augmented intervals and leap recovery in alto and bass lines
    if is_fugue:
        alto_notes = vl_ir.inner_voices.get("alto", [])
        if alto_notes:
            vl_ir.inner_voices["alto"] = fix_augmented_intervals(alto_notes, form_ir.home_key)
            vl_ir.inner_voices["alto"] = fix_leap_recovery(vl_ir.inner_voices["alto"])
        if vl_ir.bass_line:
            vl_ir.bass_line = fix_augmented_intervals(vl_ir.bass_line, form_ir.home_key)
            vl_ir.bass_line = fix_leap_recovery(vl_ir.bass_line)

    # --- Pass 5: Counterpoint ---
    print(f"\n[Pass 5] Adding inner voices (counterpoint)...")
    vl_ir = pass_5_counterpoint(vl_ir, form_ir)
    print(f"  Alto notes: {len(vl_ir.inner_voices.get('alto', []))}")
    print(f"  Tenor notes: {len(vl_ir.inner_voices.get('tenor', []))}")
    p5_count = 0
    for i in range(len(vl_ir.chords) - 1):
        c1 = vl_ir.chords[i]
        c2 = vl_ir.chords[i + 1]
        v1 = (c1.soprano, c1.alto, c1.tenor, c1.bass)
        v2 = (c2.soprano, c2.alto, c2.tenor, c2.bass)
        if VoiceLeader.has_parallel_fifths_or_octaves(v1, v2):
            p5_count += 1
    print(f"  Parallel 5th/8ve checks: {p5_count} issues found")

    # --- Fix 2: Leading tone resolution ---
    vl_ir = fix_leading_tone_resolution(vl_ir, form_ir.home_key)
    print(f"  [Fix] Leading tone resolution enforced at strong beats")

    # --- Fix 2b: Seventh resolution ---
    vl_ir = fix_seventh_resolution(vl_ir)
    print(f"  [Fix] Chord seventh resolution enforced at strong beats")

    # --- Fix 4: Voice crossing ---
    vl_ir = fix_voice_crossing(vl_ir)
    print(f"  [Fix] Voice crossing corrected (S >= A >= T >= B)")

    # --- Fix 5: Augmented intervals in all voice lines ---
    for voice_attr in ("soprano", "alto", "tenor", "bass"):
        voice_notes = [
            MelodicNote(midi=getattr(ce, voice_attr), bar=ce.bar,
                        beat=ce.beat, duration_beats=ce.duration_beats,
                        is_chord_tone=True)
            for ce in vl_ir.chords if getattr(ce, voice_attr) != 0
        ]
        if voice_notes:
            fixed = fix_augmented_intervals(voice_notes, form_ir.home_key)
            idx = 0
            for ce in vl_ir.chords:
                if getattr(ce, voice_attr) != 0:
                    setattr(ce, voice_attr, fixed[idx].midi)
                    idx += 1

    if vl_ir.inner_voices:
        for i, ce in enumerate(vl_ir.chords):
            if i < len(vl_ir.inner_voices.get("alto", [])):
                vl_ir.inner_voices["alto"][i].midi = ce.alto
            if i < len(vl_ir.inner_voices.get("tenor", [])):
                vl_ir.inner_voices["tenor"][i].midi = ce.tenor
    if vl_ir.bass_line:
        for i, ce in enumerate(vl_ir.chords):
            if i < len(vl_ir.bass_line):
                vl_ir.bass_line[i].midi = ce.bass

    # --- Fix 6: Melody voice spacing ---
    _fix_melody_voice_spacing(vl_ir)
    print(f"  [Fix] Melody voice spacing constrained (no crossing below alto)")

    # --- Pass 6: Orchestration ---
    print(f"\n[Pass 6] Assigning to instruments...")
    if is_fugue:
        tracks = pass_6_orchestration_fugue(vl_ir, form_ir)
    else:
        tracks = pass_6_orchestration(vl_ir, form_ir)
    total_notes = sum(len(notes) for notes in tracks.values())
    for inst, notes in tracks.items():
        print(f"    {inst}: {len(notes)} notes")
    print(f"  Total performance notes: {total_notes}")

    # --- Pass 6a: Smooth section transitions ---
    print(f"\n[Pass 6a] Smoothing section boundary density transitions...")
    tracks = _smooth_section_transitions(tracks, form_ir)

    # --- Pass 6b: Phrase Breathing ---
    print(f"\n[Pass 6b] Inserting phrase breathing (rests at cadences, general pause)...")
    tracks = pass_6b_phrase_breathing(tracks, vl_ir, form_ir)
    cadence_count = sum(1 for ce in vl_ir.chords if ce.is_cadential)
    print(f"  Cadence points processed: {cadence_count}")
    print(f"  General pause at {form_ir.total_bars * PHI_INVERSE:.0f} bars (~62% golden ratio)")

    # --- Pass 7: Expression ---
    print(f"\n[Pass 7] Applying expression with tension arc (climax at 62%)...")
    tracks = pass_7_expression(tracks, form_ir)
    vels = [n.velocity for notes in tracks.values() for n in notes]
    if vels:
        print(f"  Velocity range: {min(vels)}-{max(vels)}")
        print(f"  Mean velocity: {np.mean(vels):.0f}")

    # --- Pass 8: Humanization ---
    print(f"\n[Pass 8] Humanizing performance...")
    tracks = pass_8_humanization(tracks, form_ir)
    offsets = [abs(n.timing_offset_ms) for notes in tracks.values() for n in notes]
    if offsets:
        print(f"  Timing offset range: 0-{max(offsets):.1f}ms")
        print(f"  Mean timing offset:  {np.mean(offsets):.1f}ms")

    # Assemble PerformanceIR
    perf_ir = PerformanceIR()
    for inst_name, notes in tracks.items():
        perf_ir.notes.extend(notes)
    if perf_ir.notes:
        perf_ir.total_duration_sec = max(
            n.start_time_sec + n.duration_sec for n in perf_ir.notes
        )
    perf_ir.tempo_map = [(0.0, form_ir.tempo_bpm)]

    # --- Pass 9: Validation ---
    print(f"\n[Pass 9] Validating output...")
    report = pass_9_validation(perf_ir, form_ir)
    print(report.summary())

    # --- Export MIDI ---
    print(f"\n[Export] Writing MIDI to {output_file}...")
    export_midi(perf_ir, output_file, form_ir.tempo_bpm)
    print(f"  Done. {len(perf_ir.notes)} notes, "
          f"{perf_ir.total_duration_sec:.1f}s duration.")

    # --- Quality report ---
    print_quality_report(perf_ir, form_ir)

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"  COMPOSITION COMPLETE")
    print(f"  Title:       {form_ir.title}")
    print(f"  Form:        {form_ir.form.value}")
    print(f"  Key:         {form_ir.home_key.value}")
    print(f"  Character:   {form_ir.character.value}")
    print(f"  Bars:        {form_ir.total_bars}")
    print(f"  Tempo:       {form_ir.tempo_bpm} BPM")
    print(f"  Instruments: {', '.join(form_ir.instrumentation)}")
    print(f"  Notes:       {len(perf_ir.notes)}")
    print(f"  Duration:    {perf_ir.total_duration_sec:.1f}s")
    print(f"  MIDI file:   {output_file}")
    print(f"  Validation:  {'PASS' if report.is_valid else 'FAIL'}")
    avg_score = np.mean(list(report.scores.values())) if report.scores else 0
    print(f"  Avg quality: {avg_score:.2f}")
    print(f"{'=' * 60}")

    return perf_ir, form_ir, report


# =============================================================================
# MULTI-MOVEMENT SUITE
# =============================================================================

def compose_suite(prompt: str, output_path: str = "output/suite.mid",
                  seed: Optional[int] = None) -> dict:
    """
    Compose a complete 3-movement work (classical suite / sonata cycle).
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    print("=" * 60)
    print("  MULTI-MOVEMENT SUITE COMPOSITION")
    print("=" * 60)
    print(f"\n  Prompt: \"{prompt}\"\n")

    parsed = parse_prompt(prompt)
    home_key = parsed["home_key"]
    character = parsed["character"]
    is_minor = _key_is_minor(home_key)
    instruments = ", ".join(parsed["instrumentation"])

    if is_minor:
        mv2_key = _relative_major(home_key)
    else:
        mv2_key = _subdominant_key(home_key)

    mv3_key = home_key

    mv1_prompt = (f"A sonata exposition in {home_key.value}, "
                  f"heroic character, 36 bars, for {instruments}")
    mv2_prompt = (f"A ternary piece in {mv2_key.value}, "
                  f"lyrical character, 32 bars, for {instruments}")
    mv3_prompt = (f"A rondo in {mv3_key.value}, "
                  f"playful character, 40 bars, for {instruments}")

    movement_prompts = [
        ("Movement 1 - Allegro", mv1_prompt),
        ("Movement 2 - Andante", mv2_prompt),
        ("Movement 3 - Rondo", mv3_prompt),
    ]

    movement_results = []
    movement_perfs: List[PerformanceIR] = []
    movement_forms: List[FormIR] = []

    for i, (title, mv_prompt) in enumerate(movement_prompts):
        print(f"\n{'#' * 60}")
        print(f"# {title}")
        print(f"{'#' * 60}\n")
        mv_seed = (seed + i * 1000) if seed is not None else None
        perf_ir, form_ir, report = compose(
            mv_prompt,
            output_file=f"output/_suite_mv{i+1}.mid",
            seed=mv_seed,
        )
        avg_score = float(np.mean(list(report.scores.values()))) if report.scores else 0.0
        movement_results.append({
            "title": title,
            "key": form_ir.home_key.value,
            "form": form_ir.form.value,
            "bars": form_ir.total_bars,
            "duration_sec": perf_ir.total_duration_sec,
            "avg_score": avg_score,
            "valid": report.is_valid,
        })
        movement_perfs.append(perf_ir)
        movement_forms.append(form_ir)

    GAP_SEC = 2.0
    combined_perf = PerformanceIR()
    time_offset = 0.0

    for i, (perf, form) in enumerate(zip(movement_perfs, movement_forms)):
        for note in perf.notes:
            shifted = PerformanceNote(
                midi_pitch=note.midi_pitch,
                start_time_sec=note.start_time_sec + time_offset,
                duration_sec=note.duration_sec,
                velocity=note.velocity,
                channel=note.channel,
                instrument=note.instrument,
                timing_offset_ms=note.timing_offset_ms,
                velocity_offset=note.velocity_offset,
                articulation=note.articulation,
                dynamic=note.dynamic,
                pedal_on=note.pedal_on,
                pedal_off_time_sec=(note.pedal_off_time_sec + time_offset
                                    if note.pedal_off_time_sec is not None
                                    else None),
            )
            combined_perf.notes.append(shifted)
        time_offset += perf.total_duration_sec + GAP_SEC

    combined_perf.total_duration_sec = time_offset - GAP_SEC
    combined_perf.tempo_map = [(0.0, movement_forms[0].tempo_bpm)]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    export_midi(combined_perf, output_path, movement_forms[0].tempo_bpm)

    total_duration = sum(r["duration_sec"] for r in movement_results)
    total_bars = sum(r["bars"] for r in movement_results)
    avg_scores = [r["avg_score"] for r in movement_results]

    print(f"\n{'=' * 60}")
    print(f"  SUITE COMPLETE")
    print(f"{'=' * 60}")
    for r in movement_results:
        print(f"  {r['title']}: {r['form']} in {r['key']}, "
              f"{r['bars']} bars, {r['duration_sec']:.1f}s, "
              f"score={r['avg_score']:.2f}")
    print(f"  Total bars:     {total_bars}")
    print(f"  Total duration: {total_duration:.1f}s")
    print(f"  Avg score:      {np.mean(avg_scores):.2f}")
    print(f"  MIDI file:      {output_path}")
    print(f"{'=' * 60}")

    return {
        "output_path": output_path,
        "total_duration_sec": total_duration,
        "total_bars": total_bars,
        "movements": movement_results,
        "avg_score": float(np.mean(avg_scores)),
    }
