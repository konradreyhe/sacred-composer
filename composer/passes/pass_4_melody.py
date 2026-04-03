"""PASS 4: Melody (add melodic line to VoiceLeadingIR)."""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from music21 import key as m21key

from SYSTEM_ARCHITECTURE import (
    FormIR, FormType, VoiceLeadingIR, MelodicNote,
    SectionType, SubsectionType,
)
from composer.parser import (
    _KEY_TO_M21, SeedMotif, MotivicEngine,
)
from composer.helpers.phyllotaxis import phyllotaxis_interval
from composer.forms.fugue import (
    FugueSubject, _generate_fugue_subject, _build_fugue_episode_sequence,
    _get_fugue_voice_ranges, _fugue_start_pitch,
)
import composer.parser as _parser_module


# ============================================================================
# Bar-range utilities
# ============================================================================

def _build_subsection_bar_ranges(form_ir: FormIR
                                  ) -> List[Tuple[SubsectionType, SectionType, int, int, int]]:
    """
    Build a list of (subsection_type, section_type, section_index, start_bar,
    end_bar) from the form plan.
    """
    ranges: List[Tuple[SubsectionType, SectionType, int, int, int]] = []
    bar_cursor = 1
    for sec_idx, section in enumerate(form_ir.sections):
        for sub in section.subsections:
            ranges.append((sub.type, section.type, sec_idx,
                           bar_cursor, bar_cursor + sub.bars - 1))
            bar_cursor += sub.bars
    return ranges


def _subsection_for_bar(bar: int,
                        ranges: List[Tuple[SubsectionType, SectionType, int, int, int]]
                        ) -> SubsectionType:
    """Return the subsection type that contains the given bar number."""
    for stype, _sec_type, _sec_idx, start, end in ranges:
        if start <= bar <= end:
            return stype
    return SubsectionType.P_THEME  # fallback


def _section_info_for_bar(bar: int,
                          ranges: List[Tuple[SubsectionType, SectionType, int, int, int]]
                          ) -> Tuple[SubsectionType, SectionType, int]:
    """Return (subsection_type, section_type, section_index) for a bar."""
    for stype, sec_type, sec_idx, start, end in ranges:
        if start <= bar <= end:
            return stype, sec_type, sec_idx
    return SubsectionType.P_THEME, SectionType.A_SECTION, 0


def _is_return_section(sec_type: SectionType, sec_idx: int,
                       form_ir: FormIR) -> bool:
    """
    Detect whether this section is a 'return' (A' in ABA, recapitulation,
    or a later A_SECTION that repeats the opening).
    """
    if sec_type == SectionType.RECAPITULATION:
        return True
    if sec_type == SectionType.A_SECTION and sec_idx > 0:
        return True
    return False


def _motif_edit_distance(original: SeedMotif, transformed: SeedMotif) -> float:
    """
    Compute a normalized edit distance (0.0 = identical, 1.0 = totally different)
    between two motifs based on their interval sequences.
    """
    a = original.intervals
    b = transformed.intervals
    if not a and not b:
        return 0.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 0.0
    min_len = min(len(a), len(b))
    diff = 0
    for i in range(min_len):
        if a[i] != b[i]:
            diff += 1
    diff += abs(len(a) - len(b))
    return diff / max_len


def _make_consequent_from_antecedent(antecedent: SeedMotif,
                                      cadence_shift: int = -1) -> SeedMotif:
    """
    Build a consequent phrase that echoes the antecedent: identical notes
    except the last 2-3 intervals diverge to reach a different cadence.
    """
    ivls = list(antecedent.intervals)
    rhy = list(antecedent.rhythm)
    diverge_at = max(0, len(ivls) - 2)
    for j in range(diverge_at, len(ivls)):
        ivls[j] = ivls[j] + cadence_shift if ivls[j] != 0 else cadence_shift
    return SeedMotif(intervals=ivls, rhythm=rhy)


# ============================================================================
# Fugue helper
# ============================================================================

def _find_nearest_note(notes: List[MelodicNote], bar: int, beat: float
                       ) -> Optional[MelodicNote]:
    """Find the note closest to the given bar/beat position."""
    if not notes:
        return None
    target_pos = (bar - 1) * 4 + beat
    best = None
    best_dist = float("inf")
    for n in notes:
        pos = (n.bar - 1) * 4 + n.beat
        dist = abs(pos - target_pos)
        if dist < best_dist:
            best_dist = dist
            best = n
    return best


def _fix_fugue_parallels(voice_lines: Dict[str, List[MelodicNote]],
                         scale_pitches: List[int]) -> None:
    """
    Check for parallel 5ths and octaves between voice pairs at simultaneous
    time points and fix them by shifting the offending note by a step.
    """
    voice_names = ["soprano", "alto", "bass"]

    def _notes_by_pos(notes: List[MelodicNote]) -> Dict[float, MelodicNote]:
        d: Dict[float, MelodicNote] = {}
        for n in notes:
            pos = round((n.bar - 1) * 4 + n.beat, 2)
            d[pos] = n
        return d

    indexed = {v: _notes_by_pos(voice_lines[v]) for v in voice_names}
    all_positions = sorted(set().union(*(indexed[v].keys() for v in voice_names)))

    for i in range(len(all_positions) - 1):
        t1 = all_positions[i]
        t2 = all_positions[i + 1]

        for vi in range(len(voice_names)):
            for vj in range(vi + 1, len(voice_names)):
                v_upper = voice_names[vi]
                v_lower = voice_names[vj]

                n1_u = indexed[v_upper].get(t1)
                n1_l = indexed[v_lower].get(t1)
                n2_u = indexed[v_upper].get(t2)
                n2_l = indexed[v_lower].get(t2)

                if not (n1_u and n1_l and n2_u and n2_l):
                    continue

                int1 = (n1_u.midi - n1_l.midi) % 12
                int2 = (n2_u.midi - n2_l.midi) % 12

                if int1 in (0, 7) and int1 == int2:
                    if n1_u.midi != n2_u.midi and n1_l.midi != n2_l.midi:
                        target = n2_l.midi
                        for delta in [1, -1, 2, -2]:
                            candidate = target + delta
                            new_int = (n2_u.midi - candidate) % 12
                            if new_int not in (0, 7):
                                n2_l.midi = candidate
                                break


# ============================================================================
# pass_4_melody_fugue
# ============================================================================

def pass_4_melody_fugue(vl_ir: VoiceLeadingIR, form_ir: FormIR) -> VoiceLeadingIR:
    """
    PASS 4 (Fugue variant): Generate 3-voice fugue texture.
    """
    if _parser_module._current_seed_motif is None:
        _parser_module._current_seed_motif = MotivicEngine.generate_seed(
            _KEY_TO_M21.get(form_ir.home_key, "C"))

    sub_ranges = _build_subsection_bar_ranges(form_ir)
    if not sub_ranges:
        return vl_ir

    first_sub = sub_ranges[0]
    subject_bars = first_sub[4] - first_sub[3] + 1

    fugue = _generate_fugue_subject(_parser_module._current_seed_motif, form_ir.home_key,
                                     subject_bars=subject_bars)
    _parser_module._current_fugue = fugue

    home_key = form_ir.home_key
    m21_key_str = _KEY_TO_M21.get(home_key, "C")
    key_obj = m21key.Key(m21_key_str)

    voice_names = ["soprano", "alto", "bass"]
    voice_starts = {v: _fugue_start_pitch(v, home_key) for v in voice_names}
    voice_ranges = _get_fugue_voice_ranges()

    sc = key_obj.getScale()
    scale_pitches = sorted(
        [p.midi for p in sc.getPitches("C2", "C7")],
    )

    voice_lines: Dict[str, List[MelodicNote]] = {v: [] for v in voice_names}
    voice_busy_until: Dict[str, int] = {v: 0 for v in voice_names}

    for sub_type, sec_type, sec_idx, start_bar, end_bar in sub_ranges:
        section_bars = end_bar - start_bar + 1

        local_key = home_key
        for section in form_ir.sections:
            for si, sub in enumerate(section.subsections):
                if sub.type == sub_type and sub.notes:
                    local_key = sub.key
                    break

        local_key_str = _KEY_TO_M21.get(local_key, m21_key_str)
        local_key_obj = m21key.Key(local_key_str)
        local_tonic_pc = local_key_obj.tonic.pitchClass

        if sec_type == SectionType.FUGUE_EXPOSITION:
            notes_annotation = ""
            for section in form_ir.sections:
                for sub in section.subsections:
                    if (sub.type == sub_type and sub.key == local_key
                            and sub.bars == section_bars):
                        notes_annotation = sub.notes
                        break

            if "voice_0" in notes_annotation or (
                    sub_type == SubsectionType.SUBJECT_ENTRY and sec_idx == 0
                    and start_bar == sub_ranges[0][3]):
                entering_voice = "soprano"
                motif = fugue.subject
                start_pitch = voice_starts["soprano"]
            elif "voice_1" in notes_annotation or sub_type == SubsectionType.ANSWER_ENTRY:
                entering_voice = "alto"
                motif = fugue.answer
                start_pitch = voice_starts["alto"] + 7
                lo, hi = voice_ranges["alto"]
                while start_pitch > hi:
                    start_pitch -= 12
                while start_pitch < lo:
                    start_pitch += 12
            else:
                entering_voice = "bass"
                motif = fugue.subject
                start_pitch = voice_starts["bass"]

            entry_notes = MotivicEngine.realize_motif(
                motif, start_pitch, start_bar, 1.0)
            lo, hi = voice_ranges[entering_voice]
            for n in entry_notes:
                n.midi = max(lo, min(hi, n.midi))
                if n.bar <= end_bar:
                    voice_lines[entering_voice].append(n)
            voice_busy_until[entering_voice] = end_bar

            for v in voice_names:
                if v == entering_voice:
                    continue
                if voice_busy_until[v] < start_bar:
                    continue
                cs_pitch = voice_starts[v]
                if v == "soprano" and entering_voice == "alto":
                    cs_pitch = voice_starts["soprano"]
                elif v == "soprano" and entering_voice == "bass":
                    cs_pitch = voice_starts["soprano"]
                elif v == "alto" and entering_voice == "bass":
                    cs_pitch = voice_starts["alto"]

                cs_notes = MotivicEngine.realize_motif(
                    fugue.countersubject, cs_pitch, start_bar, 1.0)
                lo_v, hi_v = voice_ranges[v]
                for n in cs_notes:
                    n.midi = max(lo_v, min(hi_v, n.midi))
                    if n.bar <= end_bar:
                        voice_lines[v].append(n)

        elif sec_type == SectionType.EPISODE:
            episode_seq = _build_fugue_episode_sequence(
                fugue.subject, section_bars, direction=-1)

            for vi, v in enumerate(voice_names):
                ep_start_beat = 1.0 + vi * 0.5
                ep_start_bar = start_bar
                if ep_start_beat > 4.0:
                    ep_start_beat -= 4.0
                    ep_start_bar += 1

                pitch_offset = vi * 7
                ep_pitch = voice_starts[v] + (pitch_offset % 12)
                lo_v, hi_v = voice_ranges[v]
                ep_pitch = max(lo_v, min(hi_v, ep_pitch))

                ep_notes = MotivicEngine.realize_motif(
                    episode_seq, ep_pitch, ep_start_bar, ep_start_beat)
                for n in ep_notes:
                    n.midi = max(lo_v, min(hi_v, n.midi))
                    if n.bar <= end_bar:
                        voice_lines[v].append(n)
                voice_busy_until[v] = end_bar

        elif sec_type == SectionType.MIDDLE_ENTRY:
            rel_tonic = _fugue_start_pitch("alto", local_key)
            mid_notes = MotivicEngine.realize_motif(
                fugue.subject, rel_tonic, start_bar, 1.0)
            lo_a, hi_a = voice_ranges["alto"]
            for n in mid_notes:
                n.midi = max(lo_a, min(hi_a, n.midi))
                if n.bar <= end_bar:
                    voice_lines["alto"].append(n)

            for v in ["soprano", "bass"]:
                fp_pitch = voice_starts[v]
                frag = MotivicEngine.transform(
                    fugue.countersubject, MotivicEngine.FRAGMENTATION)
                fp_motif = _build_fugue_episode_sequence(
                    frag, section_bars, direction=1 if v == "soprano" else -1)
                fp_notes = MotivicEngine.realize_motif(
                    fp_motif, fp_pitch, start_bar, 1.0)
                lo_v, hi_v = voice_ranges[v]
                for n in fp_notes:
                    n.midi = max(lo_v, min(hi_v, n.midi))
                    if n.bar <= end_bar:
                        voice_lines[v].append(n)

        elif sec_type == SectionType.STRETTO:
            tight_offset_beats = 2.0

            trial_voices: Dict[str, List[MelodicNote]] = {}
            for vi, v in enumerate(voice_names):
                total_offset_beats = vi * tight_offset_beats
                st_bar = start_bar + int(total_offset_beats // 4)
                st_beat = 1.0 + (total_offset_beats % 4)
                if st_bar > end_bar:
                    break
                st_pitch = _fugue_start_pitch(v, home_key)
                st_notes = MotivicEngine.realize_motif(
                    fugue.subject, st_pitch, st_bar, st_beat)
                lo_v, hi_v = voice_ranges[v]
                for n in st_notes:
                    n.midi = max(lo_v, min(hi_v, n.midi))
                trial_voices[v] = [n for n in st_notes if n.bar <= end_bar]

            dissonant_beats = 0
            total_overlap_beats = 0
            if len(trial_voices) >= 2:
                v_list = list(trial_voices.values())
                for notes_a in v_list:
                    for na in notes_a:
                        pos_a = (na.bar - 1) * 4 + na.beat
                        for notes_b in v_list:
                            if notes_b is notes_a:
                                continue
                            for nb in notes_b:
                                pos_b = (nb.bar - 1) * 4 + nb.beat
                                if abs(pos_a - pos_b) < 0.5:
                                    total_overlap_beats += 1
                                    interval = abs(na.midi - nb.midi) % 12
                                    if interval in (1, 2, 6, 11):
                                        dissonant_beats += 1

            dissonance_ratio = (dissonant_beats / max(1, total_overlap_beats))
            use_tight = dissonance_ratio < 0.30

            if use_tight:
                for v, notes in trial_voices.items():
                    voice_lines[v].extend(notes)
                print(f"  [Fugue] Tight stretto used "
                      f"(dissonance: {dissonance_ratio:.0%})")
            else:
                stretto_offset_bars = max(1, fugue.subject_bars // 2)
                for vi, v in enumerate(voice_names):
                    stretto_start = start_bar + vi * stretto_offset_bars
                    if stretto_start > end_bar:
                        break
                    st_pitch = _fugue_start_pitch(v, home_key)
                    st_notes = MotivicEngine.realize_motif(
                        fugue.subject, st_pitch, stretto_start, 1.0)
                    lo_v, hi_v = voice_ranges[v]
                    for n in st_notes:
                        n.midi = max(lo_v, min(hi_v, n.midi))
                        if n.bar <= end_bar:
                            voice_lines[v].append(n)
                print(f"  [Fugue] Wide stretto used "
                      f"(tight dissonance: {dissonance_ratio:.0%} > 30%)")

        elif sec_type == SectionType.CODA:
            dominant_pitch = _fugue_start_pitch("bass", home_key) + 7
            tonic_pitch_bass = _fugue_start_pitch("bass", home_key)
            lo_b, hi_b = voice_ranges["bass"]
            dominant_pitch = max(lo_b, min(hi_b, dominant_pitch))
            tonic_pitch_bass = max(lo_b, min(hi_b, tonic_pitch_bass))

            dom_pedal_bars = max(2, round(section_bars * 0.67))
            tonic_pedal_bars = max(1, section_bars - dom_pedal_bars)

            for bar in range(start_bar, start_bar + dom_pedal_bars):
                if bar <= end_bar:
                    voice_lines["bass"].append(MelodicNote(
                        midi=dominant_pitch,
                        bar=bar,
                        beat=1.0,
                        duration_beats=4.0,
                        is_chord_tone=True,
                    ))

            for bar in range(start_bar + dom_pedal_bars, end_bar + 1):
                voice_lines["bass"].append(MelodicNote(
                    midi=tonic_pitch_bass,
                    bar=bar,
                    beat=1.0,
                    duration_beats=4.0,
                    is_chord_tone=True,
                ))

            for v in ["soprano", "alto"]:
                dim_frag = MotivicEngine.transform(
                    fugue.subject, MotivicEngine.DIMINUTION)
                frag = MotivicEngine.transform(
                    dim_frag, MotivicEngine.FRAGMENTATION)
                fp_pitch = voice_starts[v]
                fp_notes = MotivicEngine.realize_motif(
                    frag, fp_pitch, start_bar, 1.0)
                lo_v, hi_v = voice_ranges[v]
                for n in fp_notes:
                    n.midi = max(lo_v, min(hi_v, n.midi))
                    if n.bar <= end_bar:
                        voice_lines[v].append(n)

                tonic_start_bar = start_bar + dom_pedal_bars
                if tonic_start_bar <= end_bar:
                    inv_frag = MotivicEngine.transform(
                        frag, MotivicEngine.INVERSION)
                    inv_notes = MotivicEngine.realize_motif(
                        inv_frag, fp_pitch, tonic_start_bar, 1.0)
                    for n in inv_notes:
                        n.midi = max(lo_v, min(hi_v, n.midi))
                        if n.bar <= end_bar:
                            voice_lines[v].append(n)

                tonic_v = _fugue_start_pitch(v, home_key)
                voice_lines[v].append(MelodicNote(
                    midi=tonic_v, bar=end_bar, beat=3.0,
                    duration_beats=2.0, is_chord_tone=True,
                ))

        else:
            for v in voice_names:
                fp_pitch = voice_starts[v]
                fp_motif = _build_fugue_episode_sequence(
                    fugue.countersubject, section_bars, direction=-1)
                fp_notes = MotivicEngine.realize_motif(
                    fp_motif, fp_pitch, start_bar, 1.0)
                lo_v, hi_v = voice_ranges[v]
                for n in fp_notes:
                    n.midi = max(lo_v, min(hi_v, n.midi))
                    if n.bar <= end_bar:
                        voice_lines[v].append(n)

    _fix_fugue_parallels(voice_lines, scale_pitches)

    vl_ir.melody = voice_lines["soprano"]
    vl_ir.inner_voices = {"alto": voice_lines["alto"], "tenor": []}
    vl_ir.bass_line = voice_lines["bass"]

    for ce in vl_ir.chords:
        s_note = _find_nearest_note(voice_lines["soprano"], ce.bar, ce.beat)
        a_note = _find_nearest_note(voice_lines["alto"], ce.bar, ce.beat)
        b_note = _find_nearest_note(voice_lines["bass"], ce.bar, ce.beat)
        if s_note:
            ce.soprano = s_note.midi
        if a_note:
            ce.alto = a_note.midi
            ce.tenor = a_note.midi
        if b_note:
            ce.bass = b_note.midi

    total_notes = sum(len(v) for v in voice_lines.values())
    print(f"  [Fugue] Subject: {len(fugue.subject.intervals)+1} notes, "
          f"{fugue.subject_bars} bars")
    print(f"  [Fugue] Voice lines: S={len(voice_lines['soprano'])}, "
          f"A={len(voice_lines['alto'])}, B={len(voice_lines['bass'])}")
    print(f"  [Fugue] Total notes: {total_notes}")

    return vl_ir


# ============================================================================
# pass_4_melody (non-fugue)
# ============================================================================

def pass_4_melody(vl_ir: VoiceLeadingIR, form_ir: FormIR) -> VoiceLeadingIR:
    """
    PASS 4: Generate melodies by DERIVING them from the seed motif.
    """
    m21_key_str = _KEY_TO_M21.get(form_ir.home_key, "C")

    sub_ranges = _build_subsection_bar_ranges(form_ir)

    current_sub_type: Optional[SubsectionType] = None
    current_sec_idx: Optional[int] = None
    current_transform: Optional[str] = None
    transformed_motif: Optional[SeedMotif] = None

    melody_notes: List[MelodicNote] = []
    motif_note_count = 0
    total_note_count = 0
    motif_appearance_count = 0

    antecedent_motif: Optional[SeedMotif] = None
    antecedent_pitch: int = 72
    is_antecedent_next = True

    key_obj = m21key.Key(m21_key_str)
    sc = key_obj.getScale()
    pool = sorted(
        [p for p in sc.getPitches("C4", "C6")],
        key=lambda p: p.midi,
    )

    _current_seed_motif = _parser_module._current_seed_motif

    for i, chord_evt in enumerate(vl_ir.chords):
        soprano = chord_evt.soprano if chord_evt.soprano != 0 else 72

        sub_type, sec_type, sec_idx = _section_info_for_bar(
            chord_evt.bar, sub_ranges)

        if sub_type != current_sub_type or sec_idx != current_sec_idx:
            current_sub_type = sub_type
            current_sec_idx = sec_idx
            is_antecedent_next = True
            antecedent_motif = None

            if _current_seed_motif is not None:
                is_return = _is_return_section(sec_type, sec_idx, form_ir)

                if is_return:
                    current_transform = MotivicEngine.LITERAL
                elif sub_type in (SubsectionType.P_THEME,):
                    current_transform = random.choice(
                        [MotivicEngine.LITERAL, MotivicEngine.TRANSPOSITION])
                elif sub_type in (SubsectionType.S_THEME,):
                    current_transform = MotivicEngine.TRANSPOSITION
                else:
                    current_transform = MotivicEngine.pick_transform(sub_type)

                seq_offset = random.choice([2, 3, 4, 5])
                transformed_motif = MotivicEngine.transform(
                    _current_seed_motif, current_transform,
                    transpose_semitones=seq_offset)

                motif_appearance_count += 1
                if _current_seed_motif is not None and transformed_motif is not None:
                    dist = _motif_edit_distance(_current_seed_motif, transformed_motif)
                    max_allowed = 0.15 if motif_appearance_count <= 3 else 0.30
                    if dist > max_allowed:
                        fallback = random.choice(
                            [MotivicEngine.LITERAL, MotivicEngine.TRANSPOSITION])
                        transformed_motif = MotivicEngine.transform(
                            _current_seed_motif, fallback,
                            transpose_semitones=seq_offset)
                        current_transform = fallback
            else:
                transformed_motif = None

        is_phrase_start = ((chord_evt.bar - 1) % 4 == 0 and chord_evt.beat <= 1.5)
        use_motif = (
            transformed_motif is not None
            and chord_evt.duration_beats >= 2
            and (is_phrase_start or i == 0)
        )

        if use_motif:
            active_motif = transformed_motif
            if sub_type in (SubsectionType.P_THEME, SubsectionType.S_THEME):
                if is_antecedent_next:
                    antecedent_motif = transformed_motif
                    is_antecedent_next = False
                else:
                    if antecedent_motif is not None:
                        active_motif = _make_consequent_from_antecedent(
                            antecedent_motif,
                            cadence_shift=random.choice([-1, -2, 1]))
                    is_antecedent_next = True

            motif_notes = MotivicEngine.realize_motif(
                active_motif, soprano,
                chord_evt.bar, chord_evt.beat)

            max_end_beat = (chord_evt.bar - 1) * 4 + chord_evt.beat + chord_evt.duration_beats
            for mn in motif_notes:
                note_abs_beat = (mn.bar - 1) * 4 + mn.beat
                if note_abs_beat < max_end_beat:
                    melody_notes.append(mn)
                    total_note_count += 1
                    motif_note_count += 1
        else:
            melody_notes.append(MelodicNote(
                midi=soprano,
                bar=chord_evt.bar,
                beat=chord_evt.beat,
                duration_beats=1.0,
                is_chord_tone=True,
            ))
            total_note_count += 1

            if chord_evt.duration_beats >= 2:
                remaining_beats = chord_evt.duration_beats - 1
                if i + 1 < len(vl_ir.chords):
                    next_soprano = vl_ir.chords[i + 1].soprano
                    if next_soprano == 0:
                        next_soprano = soprano
                else:
                    next_soprano = soprano

                current_midi = soprano
                beat_pos = chord_evt.beat + 1.0
                bar = chord_evt.bar
                prev_direction = 0
                momentum_steps = 0

                for step in range(int(remaining_beats)):
                    direction = 1 if next_soprano > current_midi else (
                        -1 if next_soprano < current_midi else 0)
                    if direction == 0:
                        direction = 1 if step % 2 == 0 else -1

                    if prev_direction != 0 and momentum_steps < 4:
                        if direction != prev_direction:
                            direction = prev_direction

                    if random.random() < 0.25:
                        target_interval = phyllotaxis_interval()
                    else:
                        target_interval = random.choice([1, 1, 2, 2, 2])
                    target_midi = current_midi + direction * target_interval
                    candidates = [p for p in pool
                                  if (p.midi - current_midi) * direction > 0
                                  and abs(p.midi - current_midi) <= target_interval + 1]
                    if candidates:
                        chosen = min(candidates,
                                     key=lambda p: abs(p.midi - target_midi))
                        current_midi = chosen.midi

                    if direction == prev_direction:
                        momentum_steps += 1
                    else:
                        prev_direction = direction
                        momentum_steps = 1

                    if beat_pos > 4.0:
                        beat_pos -= 4.0
                        bar += 1

                    melody_notes.append(MelodicNote(
                        midi=current_midi,
                        bar=bar,
                        beat=beat_pos,
                        duration_beats=1.0,
                        is_chord_tone=False,
                        ornament_type="passing" if direction != 0 else "neighbor",
                    ))
                    beat_pos += 1.0
                    total_note_count += 1

    if melody_notes:
        n = len(melody_notes)
        for idx, mn in enumerate(melody_notes):
            t = idx / max(n - 1, 1)
            arch = math.sin(math.pi * t)
            contour_shift = int(arch * 1.5 - 0.75)
            mn.midi = max(48, min(96, mn.midi + contour_shift))

    if total_note_count > 0:
        coverage = motif_note_count / total_note_count
        print(f"  [Motif] Coverage: {motif_note_count}/{total_note_count} "
              f"notes ({coverage:.0%}) derived from seed motif")
    if motif_appearance_count > 0:
        print(f"  [Motif] Theme appearances: {motif_appearance_count}, "
              f"transform used: {current_transform}")

    vl_ir.melody = melody_notes
    return vl_ir


# ============================================================================
# Rondo / Ternary refrain replay
# ============================================================================

def _apply_rondo_refrain_replay(vl_ir: VoiceLeadingIR,
                                form_ir: FormIR) -> VoiceLeadingIR:
    """
    For rondo form: find all A sections tagged "rondo_refrain", cache the
    melody and chord voicings from the first one, then OVERWRITE subsequent
    A sections with literal copies (transposed to the same bar offset).
    """
    if form_ir.form != FormType.RONDO:
        return vl_ir

    refrain_ranges: List[Tuple[int, int]] = []
    bar_cursor = 1
    for section in form_ir.sections:
        for sub in section.subsections:
            if sub.notes == "rondo_refrain":
                refrain_ranges.append((bar_cursor, bar_cursor + sub.bars - 1))
            bar_cursor += sub.bars

    if len(refrain_ranges) < 2:
        return vl_ir

    first_start, first_end = refrain_ranges[0]
    first_refrain_melody = [
        n for n in vl_ir.melody
        if first_start <= n.bar <= first_end
    ]
    first_refrain_chords = [
        ce for ce in vl_ir.chords
        if first_start <= ce.bar <= first_end
    ]

    if not first_refrain_melody:
        return vl_ir

    refrain_replays = 0

    for rng_idx in range(1, len(refrain_ranges)):
        target_start, target_end = refrain_ranges[rng_idx]
        bar_offset = target_start - first_start

        vl_ir.melody = [
            n for n in vl_ir.melody
            if not (target_start <= n.bar <= target_end)
        ]

        for orig_note in first_refrain_melody:
            new_bar = orig_note.bar + bar_offset
            if new_bar > target_end:
                continue
            copy = MelodicNote(
                midi=orig_note.midi,
                bar=new_bar,
                beat=orig_note.beat,
                duration_beats=orig_note.duration_beats,
                is_chord_tone=orig_note.is_chord_tone,
                ornament_type=orig_note.ornament_type,
            )
            vl_ir.melody.append(copy)

        for orig_chord in first_refrain_chords:
            new_bar = orig_chord.bar + bar_offset
            if new_bar > target_end:
                continue
            for ce in vl_ir.chords:
                if ce.bar == new_bar and abs(ce.beat - orig_chord.beat) < 0.5:
                    ce.soprano = orig_chord.soprano
                    ce.bass = orig_chord.bass
                    ce.roman_numeral = orig_chord.roman_numeral
                    break

        refrain_replays += 1

    vl_ir.melody.sort(key=lambda n: (n.bar, n.beat))

    print(f"  [Rondo] Refrain replayed {refrain_replays} times "
          f"(source: bars {first_start}-{first_end}, "
          f"{len(first_refrain_melody)} notes)")

    return vl_ir


def _apply_ternary_refrain_replay(vl_ir: VoiceLeadingIR,
                                  form_ir: FormIR) -> VoiceLeadingIR:
    """
    For ternary form: find all A sections tagged "ternary_a_section", cache
    the melody and chord voicings from the first one, then OVERWRITE the A'
    return with a literal copy.
    """
    if form_ir.form != FormType.TERNARY:
        return vl_ir

    a_ranges: List[Tuple[int, int]] = []
    bar_cursor = 1
    for section in form_ir.sections:
        for sub in section.subsections:
            if sub.notes == "ternary_a_section":
                a_ranges.append((bar_cursor, bar_cursor + sub.bars - 1))
            bar_cursor += sub.bars

    if len(a_ranges) < 2:
        return vl_ir

    first_start, first_end = a_ranges[0]
    first_a_melody = [
        n for n in vl_ir.melody
        if first_start <= n.bar <= first_end
    ]
    first_a_chords = [
        ce for ce in vl_ir.chords
        if first_start <= ce.bar <= first_end
    ]

    if not first_a_melody:
        return vl_ir

    refrain_replays = 0

    for rng_idx in range(1, len(a_ranges)):
        target_start, target_end = a_ranges[rng_idx]
        bar_offset = target_start - first_start

        vl_ir.melody = [
            n for n in vl_ir.melody
            if not (target_start <= n.bar <= target_end)
        ]

        for orig_note in first_a_melody:
            new_bar = orig_note.bar + bar_offset
            if new_bar > target_end:
                continue
            copy = MelodicNote(
                midi=orig_note.midi,
                bar=new_bar,
                beat=orig_note.beat,
                duration_beats=orig_note.duration_beats,
                is_chord_tone=orig_note.is_chord_tone,
                ornament_type=orig_note.ornament_type,
            )
            vl_ir.melody.append(copy)

        for orig_chord in first_a_chords:
            new_bar = orig_chord.bar + bar_offset
            if new_bar > target_end:
                continue
            for ce in vl_ir.chords:
                if ce.bar == new_bar and abs(ce.beat - orig_chord.beat) < 0.5:
                    ce.soprano = orig_chord.soprano
                    ce.bass = orig_chord.bass
                    ce.roman_numeral = orig_chord.roman_numeral
                    break

        refrain_replays += 1

    vl_ir.melody.sort(key=lambda n: (n.bar, n.beat))

    print(f"  [Ternary] A-section replayed {refrain_replays} times "
          f"(source: bars {first_start}-{first_end}, "
          f"{len(first_a_melody)} notes)")

    return vl_ir
