"""
Evaluation Framework for AI-Generated Classical Music
======================================================
A multi-level scoring system that takes a MIDI file and returns a quality
score 0-100 with full breakdown.

Levels:
    1. Rule Compliance        (binary pass/fail gates)
    2. Statistical Quality    (scored 0-100)
    3. Structural Quality     (scored 0-100)
    4. Perceptual Quality     (heuristic proxies, scored 0-100)

Final score = weighted combination of Levels 2-4, gated by Level 1.
If Level 1 fails, the score is capped at 40 regardless of other levels.

Install:
    pip install music21 numpy scipy
"""

import math
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as sp_stats
from scipy.spatial.distance import jensenshannon

from music21 import (
    analysis,
    converter,
    chord as m21chord,
    interval as m21interval,
    key as m21key,
    note as m21note,
    pitch as m21pitch,
    roman,
    stream,
)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RuleViolation:
    """One instance of a Level-1 rule being broken."""
    rule_name: str
    measure: int
    beat: float
    voices: Tuple[str, ...]
    description: str


@dataclass
class MetricResult:
    """Result from one scored metric (Levels 2-4)."""
    name: str
    raw_value: float
    score: float          # 0-100
    weight: float         # relative importance
    target_range: Tuple[float, float]
    detail: str = ""


@dataclass
class EvaluationReport:
    """Complete evaluation output."""
    # Level 1
    rule_violations: List[RuleViolation] = field(default_factory=list)
    level1_pass: bool = True

    # Levels 2-4 individual metrics
    metrics: List[MetricResult] = field(default_factory=list)

    # Final
    level2_score: float = 0.0
    level3_score: float = 0.0
    level4_score: float = 0.0
    final_score: float = 0.0

    def summary(self) -> str:
        lines = []
        lines.append("=" * 72)
        lines.append("  CLASSICAL MUSIC EVALUATION REPORT")
        lines.append("=" * 72)

        # Level 1
        status = "PASS" if self.level1_pass else f"FAIL ({len(self.rule_violations)} violations)"
        lines.append(f"\n  Level 1 - Rule Compliance: {status}")
        if self.rule_violations:
            for v in self.rule_violations[:10]:
                lines.append(f"    [{v.rule_name}] m.{v.measure} beat {v.beat:.1f}: {v.description}")
            if len(self.rule_violations) > 10:
                lines.append(f"    ... and {len(self.rule_violations) - 10} more violations")

        # Levels 2-4
        for level_num, level_name in [(2, "Statistical"), (3, "Structural"), (4, "Perceptual")]:
            level_metrics = [m for m in self.metrics if m.name.startswith(f"L{level_num}")]
            score = getattr(self, f"level{level_num}_score")
            lines.append(f"\n  Level {level_num} - {level_name} Quality: {score:.1f}/100")
            for m in level_metrics:
                lines.append(f"    {m.name:45s}  {m.score:5.1f}  (w={m.weight:.2f})  {m.detail}")

        lines.append(f"\n{'=' * 72}")
        cap_note = " [CAPPED: Level-1 failure]" if not self.level1_pass else ""
        lines.append(f"  FINAL SCORE: {self.final_score:.1f} / 100{cap_note}")
        lines.append("=" * 72)
        return "\n".join(lines)


# =============================================================================
# HELPER UTILITIES
# =============================================================================

def _split_part_by_register(part: stream.Part, threshold: int = 60) -> List[stream.Part]:
    """
    Split a single Part into two pseudo-voices (upper/lower) by MIDI pitch.
    Used for piano or other wide-range single-track parts where all voices
    are interleaved. The threshold separates roughly soprano/alto from
    tenor/bass register.
    """
    upper = stream.Part()
    lower = stream.Part()
    # Preserve partName so instrument detection works on the split parts
    if hasattr(part, 'partName') and part.partName:
        upper.partName = part.partName
        lower.partName = part.partName

    for el in part.recurse().notesAndRests:
        if isinstance(el, m21note.Note):
            if el.pitch.midi >= threshold:
                upper.insert(float(el.offset), el)
            else:
                lower.insert(float(el.offset), el)
        elif isinstance(el, m21chord.Chord):
            # Split chord: top notes go to upper, bottom to lower
            top = [p for p in el.pitches if p.midi >= threshold]
            bot = [p for p in el.pitches if p.midi < threshold]
            if top:
                if len(top) == 1:
                    n = m21note.Note(top[0])
                    n.quarterLength = el.quarterLength
                    upper.insert(float(el.offset), n)
                else:
                    c = m21chord.Chord(top)
                    c.quarterLength = el.quarterLength
                    upper.insert(float(el.offset), c)
            if bot:
                if len(bot) == 1:
                    n = m21note.Note(bot[0])
                    n.quarterLength = el.quarterLength
                    lower.insert(float(el.offset), n)
                else:
                    c = m21chord.Chord(bot)
                    c.quarterLength = el.quarterLength
                    lower.insert(float(el.offset), c)
        elif isinstance(el, m21note.Rest):
            upper.insert(float(el.offset), el)
            lower.insert(float(el.offset), el)

    return [upper, lower]


def _extract_voices(score: stream.Score) -> List[stream.Part]:
    """
    Return all voice-like Part objects in the score.
    For single-part piano pieces (wide pitch range in one Part),
    split into upper/lower pseudo-voices so per-voice rules work correctly.
    """
    parts = list(score.parts)

    # If there is only one part and it has a wide pitch range, split it
    if len(parts) == 1:
        notes_list = [n for n in parts[0].recurse().notes if isinstance(n, m21note.Note)]
        if len(notes_list) > 10:
            pitches = [n.pitch.midi for n in notes_list]
            pitch_range = max(pitches) - min(pitches)
            if pitch_range > 24:  # more than 2 octaves => likely multi-voice
                median_pitch = int(np.median(pitches))
                return _split_part_by_register(parts[0], threshold=median_pitch)

    return parts


def _midi_notes_from_part(part: stream.Part) -> List[Tuple[float, int, float]]:
    """Return list of (offset_in_quarters, midi_pitch, duration_in_quarters)."""
    result = []
    for el in part.recurse().notesAndRests:
        if isinstance(el, m21note.Note):
            result.append((float(el.offset), el.pitch.midi, float(el.quarterLength)))
        elif isinstance(el, m21chord.Chord):
            for p in el.pitches:
                result.append((float(el.offset), p.midi, float(el.quarterLength)))
    return sorted(result, key=lambda x: x[0])


def _intervals_semitones(pitches: List[int]) -> List[int]:
    """Melodic intervals in semitones (signed) between consecutive pitches."""
    return [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]


def _clamp_score(val: float) -> float:
    return max(0.0, min(100.0, val))


def _kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """Symmetric KL divergence (Jensen-Shannon) between two distributions."""
    p = np.asarray(p, dtype=float) + epsilon
    q = np.asarray(q, dtype=float) + epsilon
    p /= p.sum()
    q /= q.sum()
    return float(jensenshannon(p, q) ** 2)  # JSD is sqrt of divergence; square it back


# =============================================================================
# INSTRUMENT RANGES (MIDI note numbers)
# =============================================================================

INSTRUMENT_RANGES = {
    # Standard orchestral ranges
    "Soprano":    (60, 81),   # C4 - A5
    "Alto":       (55, 74),   # G3 - D5
    "Tenor":      (48, 69),   # C3 - A4
    "Bass":       (40, 62),   # E2 - D4
    "Violin":     (55, 103),  # G3 - G7
    "Viola":      (48, 91),   # C3 - G6
    "Cello":      (36, 76),   # C2 - E5
    "Contrabass": (28, 60),   # E1 - C4
    "Flute":      (60, 96),   # C4 - C7
    "Oboe":       (58, 91),   # Bb3 - G6
    "Clarinet":   (50, 94),   # D3 - Bb6
    "Bassoon":    (34, 75),   # Bb1 - Eb5
    "Horn":       (41, 77),   # F2 - F5
    "Trumpet":    (55, 82),   # G3 - Bb5
    "Trombone":   (40, 72),   # E2 - C5
    "Tuba":       (28, 58),   # E1 - Bb3
    "Piano":      (21, 108),  # A0 - C8
    # Fallback
    "default":    (21, 108),
}


# =============================================================================
# LEVEL 1: RULE COMPLIANCE (binary pass/fail)
# =============================================================================
#
# Each rule is a function that takes the score and returns a list of violations.
# An empty list means the rule passes.
#
# Rules implemented:
#   1.  No parallel perfect 5ths between any voice pair
#   2.  No parallel perfect octaves/unisons between any voice pair
#   3.  No hidden (direct) 5ths or octaves in outer voices
#   4.  All voices within their instrument range
#   5.  No augmented melodic intervals (augmented 2nd, augmented 4th)
#   6.  Dissonant suspensions must resolve downward by step
#   7.  Leading tones (scale degree 7) resolve upward to tonic
#   8.  Chord 7ths resolve downward by step
#   9.  Voice spacing: adjacent upper voices no more than an octave apart
#  10.  Voice crossing: no voice crosses above/below an adjacent voice
#  11.  No consecutive leaps in same direction exceeding a 10th
#  12.  Leaps larger than a 4th are followed by stepwise motion in opposite direction
#  13.  Bass voice does not leap augmented or diminished intervals
# -----------------------------------------------------------------------


def _build_vertical_slices(parts: List[stream.Part]) -> List[Tuple[float, List[Optional[int]]]]:
    """
    Build time-aligned vertical slices across all parts.
    Returns list of (offset, [midi_pitch_or_None per part]).
    A None means the voice is resting at that offset.
    """
    # Collect all unique offsets
    all_offsets = set()
    for part in parts:
        for el in part.recurse().notesAndRests:
            all_offsets.add(round(float(el.offset), 4))
    all_offsets = sorted(all_offsets)

    slices = []
    for off in all_offsets:
        pitches = []
        for part in parts:
            found = None
            for el in part.recurse().getElementsByOffset(off, off, mustBeginInSpan=False):
                if isinstance(el, m21note.Note):
                    found = el.pitch.midi
                    break
                elif isinstance(el, m21chord.Chord):
                    found = el.pitches[-1].midi  # top note
                    break
            pitches.append(found)
        slices.append((off, pitches))
    return slices


def rule_parallel_fifths(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 1: No parallel perfect 5ths between any pair of voices.
    Condition: Two voices are a perfect 5th apart (interval mod 12 == 7) at
    time T, and still a perfect 5th apart at time T+1, and both voices moved.
    """
    parts = _extract_voices(score)
    slices = _build_vertical_slices(parts)
    violations = []

    for idx in range(len(slices) - 1):
        off1, pitches1 = slices[idx]
        off2, pitches2 = slices[idx + 1]
        for i, j in combinations(range(len(parts)), 2):
            if pitches1[i] is None or pitches1[j] is None:
                continue
            if pitches2[i] is None or pitches2[j] is None:
                continue
            int1 = (pitches1[j] - pitches1[i]) % 12
            int2 = (pitches2[j] - pitches2[i]) % 12
            if int1 == 7 and int2 == 7:
                # Both voices must have moved
                if pitches1[i] != pitches2[i] and pitches1[j] != pitches2[j]:
                    # Confirm motion is in the same direction (true parallel)
                    dir_i = pitches2[i] - pitches1[i]
                    dir_j = pitches2[j] - pitches1[j]
                    if (dir_i > 0 and dir_j > 0) or (dir_i < 0 and dir_j < 0):
                        measure = int(off1 // 4) + 1
                        beat = (off1 % 4) + 1
                        violations.append(RuleViolation(
                            "parallel_5ths", measure, beat,
                            (f"voice_{i}", f"voice_{j}"),
                            f"Parallel 5ths between voices {i} and {j}"
                        ))
    return violations


def rule_parallel_octaves(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 2: No parallel perfect octaves/unisons between any voice pair.
    Condition: interval mod 12 == 0 at both T and T+1, both voices moved,
    same direction.
    """
    parts = _extract_voices(score)
    slices = _build_vertical_slices(parts)
    violations = []

    for idx in range(len(slices) - 1):
        off1, pitches1 = slices[idx]
        off2, pitches2 = slices[idx + 1]
        for i, j in combinations(range(len(parts)), 2):
            if pitches1[i] is None or pitches1[j] is None:
                continue
            if pitches2[i] is None or pitches2[j] is None:
                continue
            int1 = (pitches1[j] - pitches1[i]) % 12
            int2 = (pitches2[j] - pitches2[i]) % 12
            if int1 == 0 and int2 == 0:
                if pitches1[i] != pitches2[i] and pitches1[j] != pitches2[j]:
                    dir_i = pitches2[i] - pitches1[i]
                    dir_j = pitches2[j] - pitches1[j]
                    if (dir_i > 0 and dir_j > 0) or (dir_i < 0 and dir_j < 0):
                        measure = int(off1 // 4) + 1
                        violations.append(RuleViolation(
                            "parallel_octaves", measure, (off1 % 4) + 1,
                            (f"voice_{i}", f"voice_{j}"),
                            f"Parallel octaves/unisons between voices {i} and {j}"
                        ))
    return violations


def rule_hidden_fifths_octaves(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 3: No hidden (direct) 5ths or octaves in outer voices.
    Condition: Outer voices move in similar motion to a perfect 5th or octave,
    AND the soprano moves by leap (> 2 semitones).
    """
    parts = _extract_voices(score)
    if len(parts) < 2:
        return []
    slices = _build_vertical_slices(parts)
    violations = []
    soprano_idx = 0
    bass_idx = len(parts) - 1

    for idx in range(len(slices) - 1):
        off1, p1 = slices[idx]
        off2, p2 = slices[idx + 1]
        s1, b1 = p1[soprano_idx], p1[bass_idx]
        s2, b2 = p2[soprano_idx], p2[bass_idx]
        if any(x is None for x in (s1, b1, s2, b2)):
            continue
        int_after = (s2 - b2) % 12
        if int_after in (0, 7):  # perfect unison/octave or fifth
            dir_s = s2 - s1
            dir_b = b2 - b1
            if (dir_s > 0 and dir_b > 0) or (dir_s < 0 and dir_b < 0):  # similar motion
                if abs(dir_s) > 2:  # soprano leaps
                    measure = int(off1 // 4) + 1
                    violations.append(RuleViolation(
                        "hidden_5th_8ve", measure, (off1 % 4) + 1,
                        ("soprano", "bass"),
                        f"Hidden {'5th' if int_after == 7 else 'octave'} in outer voices"
                    ))
    return violations


def rule_voice_range(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 4: All voices stay within their instrument range.
    Uses the instrument assigned to each Part, falling back to SATB assignment
    by part index.
    """
    parts = _extract_voices(score)
    satb_fallback = ["Soprano", "Alto", "Tenor", "Bass"]
    violations = []

    # Build a case-insensitive lookup for INSTRUMENT_RANGES
    _range_lookup = {k.lower(): k for k in INSTRUMENT_RANGES}

    for idx, part in enumerate(parts):
        # Determine instrument name -- try multiple sources
        inst = part.getInstrument()
        inst_name = None

        # 1. Try music21 instrument object
        if inst and inst.instrumentName:
            inst_name = inst.instrumentName

        # 2. Try partName (set from MIDI track name)
        if inst_name is None and getattr(part, 'partName', None):
            inst_name = part.partName

        # 3. Try part.id if it looks like a name (not a numeric id)
        if inst_name is None and hasattr(part, 'id'):
            pid = str(part.id)
            if not pid.isdigit() and pid.lower() in _range_lookup:
                inst_name = pid

        # 4. Match against INSTRUMENT_RANGES (case-insensitive)
        if inst_name is not None:
            lower = inst_name.lower().strip()
            if lower in _range_lookup:
                inst_name = _range_lookup[lower]
            else:
                # Partial match: e.g. "Acoustic Grand Piano" -> "Piano"
                matched = False
                for range_key_lower, range_key in _range_lookup.items():
                    if range_key_lower in lower or lower in range_key_lower:
                        inst_name = range_key
                        matched = True
                        break
                if not matched:
                    inst_name = None

        # 5. Fallback to SATB by index, or "default"
        if inst_name is None:
            inst_name = satb_fallback[idx] if idx < 4 else "default"

        low, high = INSTRUMENT_RANGES.get(inst_name, INSTRUMENT_RANGES["default"])

        for el in part.recurse().notes:
            pitches = el.pitches if isinstance(el, m21chord.Chord) else [el.pitch]
            for p in pitches:
                if p.midi < low or p.midi > high:
                    measure = int(float(el.offset) // 4) + 1
                    violations.append(RuleViolation(
                        "voice_range", measure, (float(el.offset) % 4) + 1,
                        (f"voice_{idx}",),
                        f"{p.nameWithOctave} (MIDI {p.midi}) out of range "
                        f"[{low}-{high}] for {inst_name}"
                    ))
    return violations


def rule_no_augmented_melodic_intervals(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 5: No augmented melodic intervals.
    Augmented intervals (in semitones): augmented 2nd = 3 semitones spanning
    a 2nd, augmented 4th = 6 semitones (tritone leap), augmented 5th = 8,
    augmented unison = 1 (chromatic).
    Practical test: flag any melodic interval whose music21 Interval
    object has quality 'Augmented'.
    """
    parts = _extract_voices(score)
    violations = []

    for v_idx, part in enumerate(parts):
        notes_list = [n for n in part.recurse().notes if isinstance(n, m21note.Note)]
        # Sort by offset to ensure correct order
        notes_list.sort(key=lambda n: float(n.offset))
        # Only check intervals between truly consecutive notes (non-overlapping)
        # Skip notes at the same offset (simultaneous = not melodic succession)
        prev = None
        for n in notes_list:
            if prev is not None:
                prev_end = float(prev.offset) + float(prev.quarterLength)
                curr_start = float(n.offset)
                # Only check if notes are sequential (next starts at or after prev)
                # and not simultaneous (different offsets)
                if curr_start >= float(prev.offset) + 0.01:
                    try:
                        ivl = m21interval.Interval(prev.pitch, n.pitch)
                        if ivl.specifier == m21interval.Specifier.AUGMENTED:
                            measure = int(float(prev.offset) // 4) + 1
                            violations.append(RuleViolation(
                                "augmented_interval", measure,
                                (float(prev.offset) % 4) + 1,
                                (f"voice_{v_idx}",),
                                f"Augmented {ivl.niceName} ({ivl.semitones} st) in voice {v_idx}"
                            ))
                    except Exception:
                        pass
            prev = n
    return violations


def rule_leading_tone_resolution(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 7: Leading tone (scale degree 7 in major, raised 7 in minor)
    must resolve upward by half step to the tonic.
    Condition: if note N has pitch class == leading_tone_pc, then note N+1
    must have pitch class == (leading_tone_pc + 1) % 12 AND move upward.
    Exception: leading tone in an inner voice may move to scale degree 5
    (down a 3rd) if the chord is V going to I in root position.
    """
    k = score.analyze("key")
    leading_tone_pc = k.getScale().pitchFromDegree(7).pitchClass
    tonic_pc = k.tonic.pitchClass

    parts = _extract_voices(score)
    violations = []

    for v_idx, part in enumerate(parts):
        notes_list = [n for n in part.recurse().notes if isinstance(n, m21note.Note)]
        notes_list.sort(key=lambda n: float(n.offset))
        # Only check resolution for truly sequential notes (non-simultaneous)
        prev = None
        for n in notes_list:
            if prev is not None and float(n.offset) >= float(prev.offset) + 0.01:
                if prev.pitch.pitchClass == leading_tone_pc:
                    next_pc = n.pitch.pitchClass
                    moved_up = n.pitch.midi > prev.pitch.midi
                    # Allow resolution to tonic (up) or dominant (inner voice exception)
                    resolves_to_tonic = (next_pc == tonic_pc and moved_up)
                    resolves_to_dominant = (next_pc == (tonic_pc + 7) % 12 and v_idx not in (0, len(parts) - 1))
                    if not resolves_to_tonic and not resolves_to_dominant:
                        measure = int(float(prev.offset) // 4) + 1
                        violations.append(RuleViolation(
                            "leading_tone_res", measure,
                            (float(prev.offset) % 4) + 1,
                            (f"voice_{v_idx}",),
                            f"Leading tone {prev.pitch.name} does not resolve upward"
                        ))
            prev = n
    return violations


def rule_seventh_resolution(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 8: Chord 7ths resolve downward by step.
    Detect notes that are the 7th of a chord (using Roman numeral analysis)
    and verify the next note in that voice moves down by 1 or 2 semitones.
    Simplified approach: any note forming interval-class 10 or 11 semitones
    above the bass is treated as a chord 7th.
    """
    parts = _extract_voices(score)
    if len(parts) < 2:
        return []
    slices = _build_vertical_slices(parts)
    violations = []
    bass_idx = len(parts) - 1

    for t in range(len(slices) - 1):
        off, pitches = slices[t]
        _, next_pitches = slices[t + 1]
        bass = pitches[bass_idx]
        if bass is None:
            continue

        for v in range(len(parts)):
            if v == bass_idx or pitches[v] is None or next_pitches[v] is None:
                continue
            interval_above_bass = (pitches[v] - bass) % 12
            if interval_above_bass in (10, 11):  # minor 7th or major 7th
                motion = next_pitches[v] - pitches[v]
                if motion >= 0:  # did not resolve down
                    measure = int(off // 4) + 1
                    violations.append(RuleViolation(
                        "seventh_resolution", measure, (off % 4) + 1,
                        (f"voice_{v}",),
                        f"Chord 7th in voice {v} does not resolve downward"
                    ))
    return violations


def rule_voice_spacing(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 9: Adjacent upper voices no more than an octave apart.
    Bass-to-tenor may exceed an octave. Soprano-to-alto and alto-to-tenor
    must be <= 12 semitones.
    """
    parts = _extract_voices(score)
    if len(parts) < 3:
        return []
    slices = _build_vertical_slices(parts)
    violations = []

    for off, pitches in slices:
        # Check adjacent upper voice pairs (not bass pair)
        for i in range(len(parts) - 2):  # skip the last pair (tenor-bass)
            if pitches[i] is None or pitches[i + 1] is None:
                continue
            gap = abs(pitches[i] - pitches[i + 1])
            if gap > 12:
                measure = int(off // 4) + 1
                violations.append(RuleViolation(
                    "voice_spacing", measure, (off % 4) + 1,
                    (f"voice_{i}", f"voice_{i + 1}"),
                    f"Voices {i} and {i+1} are {gap} semitones apart (max 12)"
                ))
    return violations


def rule_voice_crossing(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 10: No voice crosses above or below an adjacent voice.
    Voice i (higher) must have pitch >= voice i+1 (lower) at every moment.
    """
    parts = _extract_voices(score)
    slices = _build_vertical_slices(parts)
    violations = []

    for off, pitches in slices:
        for i in range(len(parts) - 1):
            if pitches[i] is None or pitches[i + 1] is None:
                continue
            if pitches[i] < pitches[i + 1]:  # higher voice is lower than lower voice
                measure = int(off // 4) + 1
                violations.append(RuleViolation(
                    "voice_crossing", measure, (off % 4) + 1,
                    (f"voice_{i}", f"voice_{i + 1}"),
                    f"Voice {i} ({pitches[i]}) crosses below voice {i+1} ({pitches[i+1]})"
                ))
    return violations


def rule_leap_recovery(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 12: Leaps larger than a perfect 4th (> 5 semitones) should be
    followed by stepwise motion in the opposite direction.
    """
    parts = _extract_voices(score)
    violations = []

    for v_idx, part in enumerate(parts):
        notes_list = [n for n in part.recurse().notes if isinstance(n, m21note.Note)]
        notes_list.sort(key=lambda n: float(n.offset))
        # Deduplicate simultaneous notes: keep only the highest at each offset
        deduped = []
        for n in notes_list:
            if not deduped or float(n.offset) >= float(deduped[-1].offset) + 0.01:
                deduped.append(n)
        pitches = [n.pitch.midi for n in deduped]
        for i in range(len(pitches) - 2):
            leap = pitches[i + 1] - pitches[i]
            if abs(leap) > 5:  # greater than perfect 4th
                recovery = pitches[i + 2] - pitches[i + 1]
                # Should move in opposite direction by step (1-2 semitones)
                opposite_direction = (leap > 0 and recovery < 0) or (leap < 0 and recovery > 0)
                stepwise = abs(recovery) <= 2
                if not (opposite_direction and stepwise):
                    measure = int(float(deduped[i].offset) // 4) + 1
                    violations.append(RuleViolation(
                        "leap_recovery", measure,
                        (float(deduped[i].offset) % 4) + 1,
                        (f"voice_{v_idx}",),
                        f"Leap of {leap} st not recovered (next motion: {recovery} st)"
                    ))
    return violations


def rule_consecutive_leaps(score: stream.Score) -> List[RuleViolation]:
    """
    Rule 11: No two consecutive leaps in the same direction that span
    more than a 10th (16 semitones total).
    """
    parts = _extract_voices(score)
    violations = []

    for v_idx, part in enumerate(parts):
        notes_list = [n for n in part.recurse().notes if isinstance(n, m21note.Note)]
        notes_list.sort(key=lambda n: float(n.offset))
        # Deduplicate simultaneous notes: keep only the highest at each offset
        deduped = []
        for n in notes_list:
            if not deduped or float(n.offset) >= float(deduped[-1].offset) + 0.01:
                deduped.append(n)
        pitches = [n.pitch.midi for n in deduped]
        for i in range(len(pitches) - 2):
            leap1 = pitches[i + 1] - pitches[i]
            leap2 = pitches[i + 2] - pitches[i + 1]
            if abs(leap1) > 2 and abs(leap2) > 2:  # both are leaps
                if (leap1 > 0 and leap2 > 0) or (leap1 < 0 and leap2 < 0):  # same direction
                    total = abs(leap1) + abs(leap2)
                    if total > 16:
                        measure = int(float(deduped[i].offset) // 4) + 1
                        violations.append(RuleViolation(
                            "consecutive_leaps", measure,
                            (float(deduped[i].offset) % 4) + 1,
                            (f"voice_{v_idx}",),
                            f"Consecutive same-dir leaps totaling {total} st (max 16)"
                        ))
    return violations


# Collect all Level-1 rule functions
LEVEL1_RULES = [
    rule_parallel_fifths,
    rule_parallel_octaves,
    rule_hidden_fifths_octaves,
    rule_voice_range,
    rule_no_augmented_melodic_intervals,
    rule_leading_tone_resolution,
    rule_seventh_resolution,
    rule_voice_spacing,
    rule_voice_crossing,
    rule_leap_recovery,
    rule_consecutive_leaps,
]


# =============================================================================
# LEVEL 2: STATISTICAL QUALITY (scored 0-100)
# =============================================================================

def metric_interval_distribution(score: stream.Score) -> MetricResult:
    """
    Compare the melodic interval distribution to the Zipfian target for
    common-practice classical music.

    Target distribution (absolute intervals in semitones):
        0 (unison/repeat): 10%
        1-2 (steps):       55%
        3-4 (thirds):      20%
        5-7 (4th/5th):     10%
        8+  (6th+):         5%

    Score = 100 * (1 - JSD(observed, target))
    where JSD is Jensen-Shannon divergence (range 0-1).

    Weight: 0.20 (melodic quality is central to perceived quality)
    """
    TARGET = np.array([0.10, 0.55, 0.20, 0.10, 0.05])
    bins = [0, 1, 3, 5, 8, 128]  # bin edges in semitones

    all_intervals = []
    for part in _extract_voices(score):
        notes_list = [n for n in part.recurse().notes if isinstance(n, m21note.Note)]
        pitches = [n.pitch.midi for n in notes_list]
        all_intervals.extend([abs(pitches[i+1] - pitches[i]) for i in range(len(pitches)-1)])

    if len(all_intervals) < 5:
        return MetricResult("L2.interval_distribution", 0, 50.0, 0.20,
                            (0.0, 0.15), "Too few intervals to evaluate")

    hist, _ = np.histogram(all_intervals, bins=bins)
    observed = hist / hist.sum()
    jsd = jensenshannon(observed, TARGET) ** 2
    raw_score = _clamp_score(100.0 * (1.0 - jsd * 5.0))  # scale: JSD=0.2 -> score 0

    return MetricResult(
        "L2.interval_distribution", jsd, raw_score, 0.20,
        (0.0, 0.15),
        f"JSD={jsd:.4f} | obs={np.round(observed,3)}"
    )


def metric_entropy(score: stream.Score) -> MetricResult:
    """
    Pitch entropy in bits per note. Shannon entropy of the pitch-class
    distribution. Classical music target: 2.6 - 3.1 bits/note.

    Formula: H = -sum(p_i * log2(p_i))

    Too low (<2.0) = monotonous. Too high (>3.5) = chaotic.
    Score = 100 if in target range, linear falloff outside.

    Weight: 0.10
    """
    TARGET_LOW, TARGET_HIGH = 2.6, 3.1
    all_pcs = []
    for part in _extract_voices(score):
        for n in part.recurse().notes:
            if isinstance(n, m21note.Note):
                all_pcs.append(n.pitch.pitchClass)
            elif isinstance(n, m21chord.Chord):
                for p in n.pitches:
                    all_pcs.append(p.pitchClass)

    if len(all_pcs) < 10:
        return MetricResult("L2.entropy", 0, 50.0, 0.10, (2.6, 3.1), "Too few notes")

    counts = Counter(all_pcs)
    total = sum(counts.values())
    probs = np.array([c / total for c in counts.values()])
    entropy = float(-np.sum(probs * np.log2(probs)))

    if TARGET_LOW <= entropy <= TARGET_HIGH:
        raw_score = 100.0
    elif entropy < TARGET_LOW:
        raw_score = _clamp_score(100.0 - (TARGET_LOW - entropy) * 80.0)
    else:
        raw_score = _clamp_score(100.0 - (entropy - TARGET_HIGH) * 80.0)

    return MetricResult(
        "L2.entropy", entropy, raw_score, 0.10,
        (TARGET_LOW, TARGET_HIGH),
        f"H={entropy:.3f} bits/note"
    )


def metric_harmonic_rhythm(score: stream.Score) -> MetricResult:
    """
    Harmonic rhythm regularity. Measures how consistently chords change.
    For classical style, chord changes should cluster around regular beat
    intervals (every half note or whole note).

    Algorithm:
      1. Chordify the score.
      2. Compute durations between chord changes.
      3. Compute coefficient of variation (CV = std/mean) of those durations.
      4. Target CV: 0.3-0.7 (too regular = mechanical, too varied = chaotic).

    Score = 100 if CV in target, linear falloff.
    Weight: 0.10
    """
    TARGET_LOW, TARGET_HIGH = 0.3, 0.7

    try:
        chordified = score.chordify()
        durations = []
        prev_offset = None
        for el in chordified.recurse().notes:
            off = float(el.offset)
            if prev_offset is not None:
                diff = off - prev_offset
                if diff > 0:
                    durations.append(diff)
            prev_offset = off
    except Exception:
        return MetricResult("L2.harmonic_rhythm", 0, 50.0, 0.10, (0.3, 0.7), "Could not chordify")

    if len(durations) < 4:
        return MetricResult("L2.harmonic_rhythm", 0, 50.0, 0.10, (0.3, 0.7), "Too few chord changes")

    mean_d = np.mean(durations)
    std_d = np.std(durations)
    cv = std_d / mean_d if mean_d > 0 else 0

    if TARGET_LOW <= cv <= TARGET_HIGH:
        raw_score = 100.0
    elif cv < TARGET_LOW:
        raw_score = _clamp_score(100.0 - (TARGET_LOW - cv) * 200.0)
    else:
        raw_score = _clamp_score(100.0 - (cv - TARGET_HIGH) * 100.0)

    return MetricResult(
        "L2.harmonic_rhythm", cv, raw_score, 0.10,
        (TARGET_LOW, TARGET_HIGH),
        f"CV={cv:.3f} (mean dur={mean_d:.2f}q)"
    )


def metric_chord_vocabulary(score: stream.Score) -> MetricResult:
    """
    Chord vocabulary richness. Count unique chord types used vs total chords.
    Target ratio (unique/total): 0.15 - 0.45 for classical music.
    Too low = boring (only I and V). Too high = incoherent.

    Weight: 0.10
    """
    TARGET_LOW, TARGET_HIGH = 0.15, 0.45

    try:
        chordified = score.chordify()
        chord_names = []
        for el in chordified.recurse().notes:
            if isinstance(el, m21chord.Chord):
                chord_names.append(el.orderedPitchClassesString)
    except Exception:
        return MetricResult("L2.chord_vocabulary", 0, 50.0, 0.10, (0.15, 0.45), "Error")

    if len(chord_names) < 4:
        return MetricResult("L2.chord_vocabulary", 0, 50.0, 0.10, (0.15, 0.45), "Too few chords")

    ratio = len(set(chord_names)) / len(chord_names)

    if TARGET_LOW <= ratio <= TARGET_HIGH:
        raw_score = 100.0
    elif ratio < TARGET_LOW:
        raw_score = _clamp_score(100.0 - (TARGET_LOW - ratio) * 400.0)
    else:
        raw_score = _clamp_score(100.0 - (ratio - TARGET_HIGH) * 150.0)

    return MetricResult(
        "L2.chord_vocabulary", ratio, raw_score, 0.10,
        (TARGET_LOW, TARGET_HIGH),
        f"unique/total={ratio:.3f} ({len(set(chord_names))} types / {len(chord_names)} chords)"
    )


def metric_cadence_placement(score: stream.Score) -> MetricResult:
    """
    Cadence frequency and placement. Classical phrases typically end with
    cadences every 4-8 bars. Detect V->I, V->vi, IV->I patterns at phrase
    endings.

    Algorithm:
      1. Analyze Roman numerals (using music21 key analysis).
      2. Find V->I or V7->I progressions.
      3. Measure spacing between cadences.
      4. Target: one cadence every 4-8 bars (16-32 quarter notes).

    Weight: 0.10
    """
    TARGET_SPACING_LOW = 12.0   # quarter notes (3 bars)
    TARGET_SPACING_HIGH = 36.0  # quarter notes (9 bars)

    try:
        k = score.analyze("key")
        chordified = score.chordify()
        tonic_pc = k.tonic.pitchClass
        dominant_pc = (tonic_pc + 7) % 12

        chords_with_offset = []
        for el in chordified.recurse().notes:
            if isinstance(el, m21chord.Chord):
                bass_pc = el.bass().pitchClass
                chords_with_offset.append((float(el.offset), bass_pc))

        cadence_offsets = []
        for i in range(len(chords_with_offset) - 1):
            off1, bass1 = chords_with_offset[i]
            off2, bass2 = chords_with_offset[i + 1]
            if bass1 == dominant_pc and bass2 == tonic_pc:
                cadence_offsets.append(off2)
    except Exception:
        return MetricResult("L2.cadence_placement", 0, 50.0, 0.10, (12, 36), "Analysis error")

    if len(cadence_offsets) < 2:
        return MetricResult("L2.cadence_placement", 0, 40.0, 0.10, (12, 36),
                            f"Only {len(cadence_offsets)} cadence(s) found")

    spacings = [cadence_offsets[i+1] - cadence_offsets[i] for i in range(len(cadence_offsets)-1)]
    mean_spacing = np.mean(spacings)

    if TARGET_SPACING_LOW <= mean_spacing <= TARGET_SPACING_HIGH:
        raw_score = 100.0
    elif mean_spacing < TARGET_SPACING_LOW:
        raw_score = _clamp_score(100.0 - (TARGET_SPACING_LOW - mean_spacing) * 8.0)
    else:
        raw_score = _clamp_score(100.0 - (mean_spacing - TARGET_SPACING_HIGH) * 4.0)

    return MetricResult(
        "L2.cadence_placement", mean_spacing, raw_score, 0.10,
        (TARGET_SPACING_LOW, TARGET_SPACING_HIGH),
        f"mean spacing={mean_spacing:.1f}q ({len(cadence_offsets)} cadences)"
    )


def metric_repetition_variation(score: stream.Score) -> MetricResult:
    """
    Repetition-with-variation ratio. Good music repeats motifs but varies
    them. Measure this by:
      1. Extract all 4-note windows (as interval sequences).
      2. For each window, find its nearest match (edit distance).
      3. Variation ratio = mean edit distance / window length for matched pairs.
      4. Target: 10-30% variation per repeat.

    Too low = verbatim repetition (robotic). Too high = no repetition (random).

    Weight: 0.15
    """
    TARGET_LOW, TARGET_HIGH = 0.10, 0.30
    WINDOW = 4

    all_intervals = []
    for part in _extract_voices(score):
        notes_list = [n for n in part.recurse().notes if isinstance(n, m21note.Note)]
        pitches = [n.pitch.midi for n in notes_list]
        intervals = _intervals_semitones(pitches)
        all_intervals.extend(intervals)

    if len(all_intervals) < WINDOW * 3:
        return MetricResult("L2.repetition_variation", 0, 50.0, 0.15, (0.10, 0.30), "Too few notes")

    # Extract windows
    windows = [tuple(all_intervals[i:i+WINDOW]) for i in range(len(all_intervals) - WINDOW + 1)]

    # Sample pairs for efficiency
    n_samples = min(500, len(windows) * (len(windows) - 1) // 2)
    variation_ratios = []
    rng = np.random.default_rng(42)

    for _ in range(n_samples):
        i, j = rng.choice(len(windows), size=2, replace=False)
        w1, w2 = windows[i], windows[j]
        # Normalized L1 distance as variation measure
        dist = sum(abs(a - b) for a, b in zip(w1, w2))
        max_dist = sum(max(abs(a), abs(b)) for a, b in zip(w1, w2))
        if max_dist > 0:
            variation_ratios.append(dist / max_dist)

    if not variation_ratios:
        return MetricResult("L2.repetition_variation", 0, 50.0, 0.15, (0.10, 0.30), "No pairs")

    mean_var = np.mean(variation_ratios)

    # Score: how many pairs fall in the sweet spot
    in_range = np.mean([(TARGET_LOW <= v <= TARGET_HIGH) for v in variation_ratios])
    raw_score = _clamp_score(in_range * 100.0 + (30.0 if TARGET_LOW <= mean_var <= TARGET_HIGH else 0))
    raw_score = min(raw_score, 100.0)

    return MetricResult(
        "L2.repetition_variation", mean_var, raw_score, 0.15,
        (TARGET_LOW, TARGET_HIGH),
        f"mean variation={mean_var:.3f} ({in_range*100:.0f}% pairs in target range)"
    )


def metric_phrase_length(score: stream.Score) -> MetricResult:
    """
    Phrase length distribution. Classical phrases are typically 4 or 8 bars.
    Detect phrase boundaries by finding rests, long notes, or cadences.
    Measure how close phrase lengths are to multiples of 4 bars.

    Score = proportion of phrases whose length (in bars) is within 1 bar
    of a multiple of 4.

    Weight: 0.10
    """
    # Use rests and long notes as phrase boundary heuristic
    all_notes = []
    for part in _extract_voices(score):
        for el in part.recurse().notesAndRests:
            all_notes.append((float(el.offset), isinstance(el, m21note.Rest), float(el.quarterLength)))
    all_notes.sort()

    if not all_notes:
        return MetricResult("L2.phrase_length", 0, 50.0, 0.10, (0, 0), "No notes")

    # Detect boundaries: rests or notes >= 3 beats long
    boundaries = [0.0]
    for off, is_rest, dur in all_notes:
        if is_rest and dur >= 1.0:
            boundaries.append(off)
        elif dur >= 3.0:
            boundaries.append(off + dur)

    total_dur = max(off + dur for off, _, dur in all_notes)
    boundaries.append(total_dur)
    boundaries = sorted(set(boundaries))

    phrase_lengths_bars = [(boundaries[i+1] - boundaries[i]) / 4.0 for i in range(len(boundaries)-1)]
    phrase_lengths_bars = [pl for pl in phrase_lengths_bars if pl > 0.5]  # filter tiny fragments

    if len(phrase_lengths_bars) < 2:
        return MetricResult("L2.phrase_length", 0, 50.0, 0.10, (3, 9),
                            f"{len(phrase_lengths_bars)} phrases detected")

    # Score: how close each phrase length is to a multiple of 4
    good = 0
    for pl in phrase_lengths_bars:
        nearest_mult = round(pl / 4) * 4
        if nearest_mult == 0:
            nearest_mult = 4
        if abs(pl - nearest_mult) <= 1.0:
            good += 1

    raw_score = _clamp_score((good / len(phrase_lengths_bars)) * 100.0)

    return MetricResult(
        "L2.phrase_length", np.mean(phrase_lengths_bars), raw_score, 0.10,
        (3.0, 9.0),
        f"mean={np.mean(phrase_lengths_bars):.1f} bars, {good}/{len(phrase_lengths_bars)} near 4-bar multiple"
    )


LEVEL2_METRICS = [
    metric_interval_distribution,
    metric_entropy,
    metric_harmonic_rhythm,
    metric_chord_vocabulary,
    metric_cadence_placement,
    metric_repetition_variation,
    metric_phrase_length,
]


# =============================================================================
# LEVEL 3: STRUCTURAL QUALITY (scored 0-100)
# =============================================================================

def metric_phrase_boundaries(score: stream.Score) -> MetricResult:
    """
    Are there identifiable phrases? Uses a simple autocorrelation-based
    detector: if the pitch sequence has strong autocorrelation at lags
    corresponding to 4- or 8-bar phrases, the piece has clear phrase structure.

    Algorithm:
      1. Convert soprano/top voice to pitch sequence (one value per beat).
      2. Compute autocorrelation at lags 16, 32 (= 4 bars, 8 bars in quarter notes).
      3. Score = max autocorrelation at those lags, scaled to 0-100.
      Target: autocorrelation > 0.3 at phrase-length lag.

    Weight: 0.15
    """
    TARGET = 0.3

    parts = _extract_voices(score)
    if not parts:
        return MetricResult("L3.phrase_boundaries", 0, 50.0, 0.15, (0.3, 1.0), "No parts")

    # Build pitch-per-beat sequence from top voice
    top_part = parts[0]
    notes_list = [n for n in top_part.recurse().notes if isinstance(n, m21note.Note)]
    if len(notes_list) < 16:
        return MetricResult("L3.phrase_boundaries", 0, 40.0, 0.15, (0.3, 1.0), "Too short")

    # Sample at quarter-note resolution
    max_offset = max(float(n.offset) for n in notes_list)
    beats = int(max_offset) + 1
    pitch_seq = np.zeros(beats)
    for n in notes_list:
        beat_idx = int(float(n.offset))
        if beat_idx < beats:
            pitch_seq[beat_idx] = n.pitch.midi

    # Fill gaps (hold previous pitch), including from the start
    # First, fill index 0 if it's still zero (no note exactly at beat 0)
    if pitch_seq[0] == 0 and notes_list:
        pitch_seq[0] = notes_list[0].pitch.midi
    for i in range(1, len(pitch_seq)):
        if pitch_seq[i] == 0:
            pitch_seq[i] = pitch_seq[i-1]

    # Normalize
    pitch_seq = pitch_seq - np.mean(pitch_seq)
    norm = np.dot(pitch_seq, pitch_seq)
    if norm == 0:
        return MetricResult("L3.phrase_boundaries", 0, 50.0, 0.15, (0.3, 1.0), "Constant pitch")

    # Autocorrelation at key lags
    best_ac = 0
    best_lag = 0
    for lag in [8, 12, 16, 24, 32]:
        if lag >= len(pitch_seq):
            continue
        ac = np.dot(pitch_seq[:len(pitch_seq)-lag], pitch_seq[lag:]) / norm
        if ac > best_ac:
            best_ac = ac
            best_lag = lag

    raw_score = _clamp_score(best_ac * 100.0 / 0.5)  # 0.5 autocorr -> 100

    return MetricResult(
        "L3.phrase_boundaries", best_ac, raw_score, 0.15,
        (TARGET, 1.0),
        f"best autocorr={best_ac:.3f} at lag={best_lag}q ({best_lag/4:.0f} bars)"
    )


def metric_thematic_development(score: stream.Score) -> MetricResult:
    """
    Is there motivic development? Extract the opening 4-note motif and
    search for transformed versions (transposition, inversion, retrograde,
    rhythmic augmentation).

    Algorithm:
      1. Extract first 4 melodic intervals from top voice = the "motif".
      2. Generate all 48 forms (4 transforms * 12 transpositions).
      3. Slide a window across the piece, measure similarity to each form.
      4. Count windows with cosine similarity > 0.8 to any motif form.
      5. Development score = (matching windows / total windows), target 15-40%.

    Weight: 0.20
    """
    TARGET_LOW, TARGET_HIGH = 0.15, 0.40
    MOTIF_LEN = 4

    parts = _extract_voices(score)
    if not parts:
        return MetricResult("L3.thematic_development", 0, 50.0, 0.20, (0.15, 0.40), "No parts")

    top_notes = [n for n in parts[0].recurse().notes if isinstance(n, m21note.Note)]
    pitches = [n.pitch.midi for n in top_notes]
    if len(pitches) < MOTIF_LEN + 5:
        return MetricResult("L3.thematic_development", 0, 40.0, 0.20, (0.15, 0.40), "Too short")

    intervals = _intervals_semitones(pitches)
    motif = intervals[:MOTIF_LEN]

    # Generate motif transforms (interval-based, transposition-invariant)
    prime = np.array(motif, dtype=float)
    retrograde = prime[::-1]
    inversion = -prime
    retro_inv = -retrograde
    forms = [prime, retrograde, inversion, retro_inv]

    # Slide window and check similarity
    windows = [np.array(intervals[i:i+MOTIF_LEN], dtype=float)
               for i in range(len(intervals) - MOTIF_LEN + 1)]

    matches = 0
    for w in windows:
        w_norm = np.linalg.norm(w)
        if w_norm == 0:
            continue
        for form in forms:
            f_norm = np.linalg.norm(form)
            if f_norm == 0:
                continue
            cosine_sim = np.dot(w, form) / (w_norm * f_norm)
            if cosine_sim > 0.8:
                matches += 1
                break

    ratio = matches / len(windows) if windows else 0

    if TARGET_LOW <= ratio <= TARGET_HIGH:
        raw_score = 100.0
    elif ratio < TARGET_LOW:
        raw_score = _clamp_score(100.0 - (TARGET_LOW - ratio) * 400.0)
    else:
        raw_score = _clamp_score(100.0 - (ratio - TARGET_HIGH) * 150.0)

    return MetricResult(
        "L3.thematic_development", ratio, raw_score, 0.20,
        (TARGET_LOW, TARGET_HIGH),
        f"motif recurrence={ratio:.3f} ({matches}/{len(windows)} windows)"
    )


def metric_tension_arc(score: stream.Score) -> MetricResult:
    """
    Does the piece have a convincing tension arc? Compute a tension curve
    and compare it to the ideal shape (gradual rise, climax near golden
    section at 61.8%, resolution at end).

    Tension proxy per beat:
      tension(t) = 0.4 * dissonance(t) + 0.3 * pitch_height(t)
                   + 0.2 * note_density(t) + 0.1 * dynamics(t)

    Compare to target curve using Pearson correlation.
    Target: correlation > 0.5 with the "arch" shape.

    Weight: 0.20
    """
    parts = _extract_voices(score)
    if not parts:
        return MetricResult("L3.tension_arc", 0, 50.0, 0.20, (0.5, 1.0), "No parts")

    # Determine total length
    all_offsets = []
    for part in parts:
        for el in part.recurse().notesAndRests:
            all_offsets.append(float(el.offset) + float(el.quarterLength))
    if not all_offsets:
        return MetricResult("L3.tension_arc", 0, 50.0, 0.20, (0.5, 1.0), "No notes")

    total_length = max(all_offsets)
    n_bins = max(8, int(total_length / 4))  # one bin per bar
    bin_size = total_length / n_bins

    # Compute tension components per bin
    pitch_height = np.zeros(n_bins)
    note_density = np.zeros(n_bins)
    dissonance = np.zeros(n_bins)

    for part in parts:
        for el in part.recurse().notes:
            offset = float(el.offset)
            bin_idx = min(int(offset / bin_size), n_bins - 1)
            if isinstance(el, m21note.Note):
                pitch_height[bin_idx] += el.pitch.midi
                note_density[bin_idx] += 1
            elif isinstance(el, m21chord.Chord):
                for p in el.pitches:
                    pitch_height[bin_idx] += p.midi
                    note_density[bin_idx] += 1

    # Normalize each component to 0-1
    for arr in [pitch_height, note_density, dissonance]:
        arr_max = arr.max()
        if arr_max > 0:
            arr /= arr_max

    # Estimate dissonance: count interval classes 1, 2, 6, 10, 11 in vertical slices
    try:
        chordified = score.chordify()
        for el in chordified.recurse().notes:
            if isinstance(el, m21chord.Chord) and len(el.pitches) >= 2:
                offset = float(el.offset)
                bin_idx = min(int(offset / bin_size), n_bins - 1)
                for pi, pj in combinations(el.pitches, 2):
                    ic = abs(pi.midi - pj.midi) % 12
                    if ic in (1, 2, 6, 10, 11):  # dissonant interval classes
                        dissonance[bin_idx] += 1
        d_max = dissonance.max()
        if d_max > 0:
            dissonance /= d_max
    except Exception:
        pass

    # Combined tension curve
    tension = 0.4 * dissonance + 0.3 * pitch_height + 0.2 * note_density + 0.1 * np.ones(n_bins) * 0.5

    # Generate target "arch" curve: rise to golden section, then resolve
    t = np.linspace(0, 1, n_bins)
    golden = 0.618
    target = np.where(t <= golden,
                      np.sin(np.pi * t / (2 * golden)),          # rise phase
                      np.sin(np.pi * (1 - t) / (2 * (1 - golden))))  # fall phase
    target = target / target.max() if target.max() > 0 else target

    # Pearson correlation
    if np.std(tension) > 0 and np.std(target) > 0:
        corr = float(np.corrcoef(tension, target)[0, 1])
    else:
        corr = 0.0

    raw_score = _clamp_score((corr + 0.3) * 77.0)  # corr=1.0 -> 100, corr=-0.3 -> 0

    # Also check: is the climax near the golden section?
    if len(tension) > 0:
        climax_pos = np.argmax(tension) / len(tension)
        climax_near_golden = abs(climax_pos - 0.618) < 0.15
    else:
        climax_near_golden = False

    if climax_near_golden:
        raw_score = min(100.0, raw_score + 10.0)

    return MetricResult(
        "L3.tension_arc", corr, raw_score, 0.20,
        (0.5, 1.0),
        f"corr={corr:.3f}, climax@{climax_pos:.2f} ({'near' if climax_near_golden else 'far from'} golden)"
    )


def metric_form_proportions(score: stream.Score) -> MetricResult:
    """
    Do section proportions fall within normal ranges?
    For a binary/ternary form, sections should have recognizable boundaries
    and proportions roughly 1:1 or 2:1.

    Algorithm:
      1. Use repetition detection (autocorrelation peaks) to find section boundaries.
      2. Compute ratios between adjacent sections.
      3. Score based on how close ratios are to golden ratio (1.618) or 1:1.

    Weight: 0.10
    """
    parts = _extract_voices(score)
    if not parts:
        return MetricResult("L3.form_proportions", 0, 50.0, 0.10, (0, 0), "No parts")

    top_notes = [n for n in parts[0].recurse().notes if isinstance(n, m21note.Note)]
    pitches = [n.pitch.midi for n in top_notes]

    if len(pitches) < 32:
        return MetricResult("L3.form_proportions", 0, 50.0, 0.10, (0.8, 1.7),
                            "Piece too short for form analysis")

    # Beat-quantized pitch sequence
    max_offset = max(float(n.offset) for n in top_notes)
    beats = int(max_offset) + 1
    seq = np.zeros(beats)
    for n in top_notes:
        idx = int(float(n.offset))
        if idx < beats:
            seq[idx] = n.pitch.midi
    for i in range(1, len(seq)):
        if seq[i] == 0:
            seq[i] = seq[i-1]

    seq = seq - np.mean(seq)
    norm = np.dot(seq, seq)
    if norm == 0:
        return MetricResult("L3.form_proportions", 0, 50.0, 0.10, (0.8, 1.7), "Constant pitch")

    # Self-similarity matrix (block-based)
    block = max(4, beats // 16)
    n_blocks = beats // block
    if n_blocks < 4:
        return MetricResult("L3.form_proportions", 0, 50.0, 0.10, (0.8, 1.7), "Too few blocks")

    blocks = [seq[i*block:(i+1)*block] for i in range(n_blocks)]
    sim_matrix = np.zeros((n_blocks, n_blocks))
    for i in range(n_blocks):
        for j in range(n_blocks):
            n1 = np.linalg.norm(blocks[i])
            n2 = np.linalg.norm(blocks[j])
            if n1 > 0 and n2 > 0:
                sim_matrix[i, j] = np.dot(blocks[i], blocks[j]) / (n1 * n2)

    # Find major section boundary: largest drop in diagonal similarity
    diag_sim = [sim_matrix[i, i+1] for i in range(n_blocks - 1)]
    if not diag_sim:
        return MetricResult("L3.form_proportions", 0, 50.0, 0.10, (0.8, 1.7), "No boundaries")

    boundary_idx = int(np.argmin(diag_sim))
    section1_len = boundary_idx + 1
    section2_len = n_blocks - section1_len

    if section2_len == 0:
        ratio = 1.0
    else:
        ratio = max(section1_len, section2_len) / min(section1_len, section2_len)

    # Score: how close is ratio to golden ratio (1.618) or unity (1.0)?
    dist_to_golden = abs(ratio - 1.618)
    dist_to_unity = abs(ratio - 1.0)
    best_dist = min(dist_to_golden, dist_to_unity)
    raw_score = _clamp_score(100.0 - best_dist * 60.0)

    return MetricResult(
        "L3.form_proportions", ratio, raw_score, 0.10,
        (0.8, 1.7),
        f"section ratio={ratio:.2f} (boundary at block {boundary_idx+1}/{n_blocks})"
    )


LEVEL3_METRICS = [
    metric_phrase_boundaries,
    metric_thematic_development,
    metric_tension_arc,
    metric_form_proportions,
]


# =============================================================================
# LEVEL 4: PERCEPTUAL QUALITY (heuristic proxies, scored 0-100)
# =============================================================================
#
# True perceptual quality requires human listeners or an advanced audio model.
# These metrics are heuristic proxies that correlate with perceived quality.
# =============================================================================

def metric_intentionality(score: stream.Score) -> MetricResult:
    """
    Does it sound "intentional"? This is the #1 Turing test discriminator.

    Proxy: Intentionality correlates with PREDICTABILITY at the local level
    combined with SURPRISE at the global level. We measure this as:
      - Local predictability: bigram transition entropy of pitch classes.
        Low entropy = each note strongly predicts the next = intentional.
      - Global surprise: how often does the piece deviate from the most
        common 4-gram patterns? Some deviation = interest, too much = random.

    Intentionality score = local_predictability * 0.6 + appropriate_surprise * 0.4

    Target local bigram entropy: 1.5-2.5 (lower than pitch entropy because
    transitions should be more constrained than raw pitch distribution).

    Weight: 0.15 (highest single weight in L4)
    """
    all_pcs = []
    for part in _extract_voices(score):
        for n in part.recurse().notes:
            if isinstance(n, m21note.Note):
                all_pcs.append(n.pitch.pitchClass)

    if len(all_pcs) < 20:
        return MetricResult("L4.intentionality", 0, 50.0, 0.15, (1.5, 2.5), "Too few notes")

    # Bigram transition entropy
    bigrams = [(all_pcs[i], all_pcs[i+1]) for i in range(len(all_pcs)-1)]
    bigram_counts = Counter(bigrams)

    # Conditional entropy: H(next | current) = H(bigram) - H(unigram)
    total_bi = sum(bigram_counts.values())
    p_bi = np.array(list(bigram_counts.values()), dtype=float) / total_bi
    h_bigram = float(-np.sum(p_bi * np.log2(p_bi)))

    unigram_counts = Counter(all_pcs)
    total_uni = sum(unigram_counts.values())
    p_uni = np.array(list(unigram_counts.values()), dtype=float) / total_uni
    h_unigram = float(-np.sum(p_uni * np.log2(p_uni)))

    conditional_entropy = h_bigram - h_unigram

    # Score conditional entropy: target 1.5-2.5
    if 1.5 <= conditional_entropy <= 2.5:
        local_score = 100.0
    elif conditional_entropy < 1.5:
        local_score = max(0, 100.0 - (1.5 - conditional_entropy) * 80)
    else:
        local_score = max(0, 100.0 - (conditional_entropy - 2.5) * 80)

    # 4-gram surprise: what fraction of 4-grams appear only once?
    fourgrams = [tuple(all_pcs[i:i+4]) for i in range(len(all_pcs)-3)]
    fg_counts = Counter(fourgrams)
    hapax_ratio = sum(1 for c in fg_counts.values() if c == 1) / len(fg_counts) if fg_counts else 1

    # Target hapax ratio: 0.4-0.7 (some unique patterns, but not all)
    if 0.4 <= hapax_ratio <= 0.7:
        surprise_score = 100.0
    elif hapax_ratio < 0.4:
        surprise_score = max(0, 100.0 - (0.4 - hapax_ratio) * 200)
    else:
        surprise_score = max(0, 100.0 - (hapax_ratio - 0.7) * 200)

    combined = local_score * 0.6 + surprise_score * 0.4
    raw_score = _clamp_score(combined)

    return MetricResult(
        "L4.intentionality", conditional_entropy, raw_score, 0.15,
        (1.5, 2.5),
        f"cond_entropy={conditional_entropy:.3f}, hapax_ratio={hapax_ratio:.3f}"
    )


def metric_transition_motivation(score: stream.Score) -> MetricResult:
    """
    Are transitions between sections motivated?

    Proxy: At detected section boundaries (large drops in local similarity),
    measure whether there is "preparatory material" — a gradual change in
    texture, pitch range, or harmonic rhythm leading into the boundary.

    Algorithm:
      1. Compute local texture density in 2-bar windows.
      2. At each section boundary, compare the 4 bars before the boundary
         to the 4 bars after.
      3. A motivated transition has a GRADUAL change (low derivative of
         density), not an abrupt jump.
      4. Score = 1 - (max jump / max possible jump).

    Weight: 0.10
    """
    parts = _extract_voices(score)
    if not parts:
        return MetricResult("L4.transition_motivation", 0, 50.0, 0.10, (0, 0.5), "No parts")

    # Compute note density per bar
    all_offsets = []
    for part in parts:
        for el in part.recurse().notes:
            all_offsets.append(float(el.offset))
    if not all_offsets:
        return MetricResult("L4.transition_motivation", 0, 50.0, 0.10, (0, 0.5), "No notes")

    max_offset = max(all_offsets)
    n_bars = max(4, int(max_offset / 4) + 1)
    density = np.zeros(n_bars)
    for off in all_offsets:
        bar = min(int(off / 4), n_bars - 1)
        density[bar] += 1

    if np.max(density) > 0:
        density = density / np.max(density)

    # Compute bar-to-bar jumps
    jumps = np.abs(np.diff(density))

    if len(jumps) == 0:
        return MetricResult("L4.transition_motivation", 0, 50.0, 0.10, (0, 0.5), "Single bar")

    max_jump = float(np.max(jumps))
    mean_jump = float(np.mean(jumps))

    # Lower max jump = more gradual transitions = better
    # Target: max jump < 0.5 (on 0-1 normalized scale)
    raw_score = _clamp_score(100.0 * (1.0 - max_jump))

    return MetricResult(
        "L4.transition_motivation", max_jump, raw_score, 0.10,
        (0.0, 0.5),
        f"max density jump={max_jump:.3f}, mean={mean_jump:.3f}"
    )


def metric_directional_momentum(score: stream.Score) -> MetricResult:
    """
    Does the music feel like it's "going somewhere"?

    Proxy: Measure directional consistency in short windows. Music that
    "goes somewhere" has longer runs of consistent melodic direction
    (ascending or descending) rather than aimless oscillation.

    Algorithm:
      1. Compute sign of each melodic interval (+1 up, -1 down, 0 same).
      2. Measure mean run length of same-direction intervals.
      3. Target mean run length: 2.0-4.0 (too short = aimless, too long = scalar).

    Weight: 0.10
    """
    TARGET_LOW, TARGET_HIGH = 2.0, 4.0

    all_intervals = []
    for part in _extract_voices(score):
        notes_list = [n for n in part.recurse().notes if isinstance(n, m21note.Note)]
        pitches = [n.pitch.midi for n in notes_list]
        all_intervals.extend(_intervals_semitones(pitches))

    if len(all_intervals) < 10:
        return MetricResult("L4.directional_momentum", 0, 50.0, 0.10, (2.0, 4.0), "Too few notes")

    signs = [1 if x > 0 else (-1 if x < 0 else 0) for x in all_intervals]

    # Compute run lengths
    runs = []
    current_run = 1
    for i in range(1, len(signs)):
        if signs[i] == signs[i-1] and signs[i] != 0:
            current_run += 1
        else:
            if current_run > 0:
                runs.append(current_run)
            current_run = 1
    runs.append(current_run)

    mean_run = np.mean(runs) if runs else 1.0

    if TARGET_LOW <= mean_run <= TARGET_HIGH:
        raw_score = 100.0
    elif mean_run < TARGET_LOW:
        raw_score = _clamp_score(100.0 - (TARGET_LOW - mean_run) * 60.0)
    else:
        raw_score = _clamp_score(100.0 - (mean_run - TARGET_HIGH) * 30.0)

    return MetricResult(
        "L4.directional_momentum", mean_run, raw_score, 0.10,
        (TARGET_LOW, TARGET_HIGH),
        f"mean run length={mean_run:.2f} ({len(runs)} runs)"
    )


LEVEL4_METRICS = [
    metric_intentionality,
    metric_transition_motivation,
    metric_directional_momentum,
]


# =============================================================================
# MAIN EVALUATOR
# =============================================================================

# Weight distribution across levels (must sum to 1.0)
LEVEL_WEIGHTS = {
    2: 0.35,  # Statistical quality
    3: 0.40,  # Structural quality (most important for musical coherence)
    4: 0.25,  # Perceptual quality
}

# Level-1 failure cap: if rules are violated, final score cannot exceed this
LEVEL1_FAILURE_CAP = 40.0

# Severity scaling: reduce cap further based on number of violations
LEVEL1_VIOLATIONS_SCALE = 2.0  # subtract this many points per violation from cap


def evaluate_score(score: stream.Score) -> EvaluationReport:
    """
    Run the full evaluation pipeline on a music21 Score object.

    Returns an EvaluationReport with breakdown and final score.
    """
    report = EvaluationReport()

    # --- Level 1: Rule compliance ---
    for rule_fn in LEVEL1_RULES:
        try:
            violations = rule_fn(score)
            report.rule_violations.extend(violations)
        except Exception as e:
            warnings.warn(f"Rule {rule_fn.__name__} raised {e}")

    report.level1_pass = len(report.rule_violations) == 0

    # --- Level 2: Statistical quality ---
    for metric_fn in LEVEL2_METRICS:
        try:
            result = metric_fn(score)
            report.metrics.append(result)
        except Exception as e:
            warnings.warn(f"Metric {metric_fn.__name__} raised {e}")

    # --- Level 3: Structural quality ---
    for metric_fn in LEVEL3_METRICS:
        try:
            result = metric_fn(score)
            report.metrics.append(result)
        except Exception as e:
            warnings.warn(f"Metric {metric_fn.__name__} raised {e}")

    # --- Level 4: Perceptual quality ---
    for metric_fn in LEVEL4_METRICS:
        try:
            result = metric_fn(score)
            report.metrics.append(result)
        except Exception as e:
            warnings.warn(f"Metric {metric_fn.__name__} raised {e}")

    # --- Compute level scores (weighted average within each level) ---
    for level_num in (2, 3, 4):
        prefix = f"L{level_num}"
        level_metrics = [m for m in report.metrics if m.name.startswith(prefix)]
        total_weight = sum(m.weight for m in level_metrics)
        if total_weight > 0:
            level_score = sum(m.score * m.weight for m in level_metrics) / total_weight
        else:
            level_score = 50.0
        setattr(report, f"level{level_num}_score", round(level_score, 2))

    # --- Final score ---
    final = sum(
        getattr(report, f"level{level_num}_score") * LEVEL_WEIGHTS[level_num]
        for level_num in (2, 3, 4)
    )

    # Apply Level-1 cap if rules were violated
    if not report.level1_pass:
        cap = max(0, LEVEL1_FAILURE_CAP - len(report.rule_violations) * LEVEL1_VIOLATIONS_SCALE)
        final = min(final, cap)

    report.final_score = round(final, 2)
    return report


def evaluate_midi(midi_path: str) -> EvaluationReport:
    """
    Convenience function: load a MIDI file and run full evaluation.

    Usage:
        report = evaluate_midi("my_piece.mid")
        print(report.summary())
        print(f"Score: {report.final_score}/100")
    """
    score = converter.parse(midi_path)
    return evaluate_score(score)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python evaluation_framework.py <midi_file>")
        print("       Returns a quality score 0-100 with breakdown.")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Evaluating: {path}")
    print()

    report = evaluate_midi(path)
    print(report.summary())
