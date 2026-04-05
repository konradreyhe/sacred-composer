"""Fugue form plan builder and fugue-specific data structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from music21 import key as m21key

from SYSTEM_ARCHITECTURE import (
    SectionIR, SubsectionIR, SectionType, SubsectionType,
    KeyToken, CharacterToken, TextureToken, CadenceType,
)
from composer._rng import rng
from composer.parser import (
    SeedMotif, _key_is_minor, _relative_major, _dominant_key, _KEY_TO_M21,
)


@dataclass
class FugueSubject:
    """Holds the fugue subject, answer, and countersubject as SeedMotif objects."""
    subject: SeedMotif
    answer: SeedMotif           # tonal answer (transposed to dominant)
    countersubject: SeedMotif   # complementary line
    subject_bars: int           # how many bars the subject spans


def _build_fugue_plan(home_key: KeyToken, total_bars: int,
                      character: CharacterToken,
                      num_voices: int = 3) -> List[SectionIR]:
    """
    Build a 3-voice fugue plan with:
      - Exposition: Subject(I) -> Answer(V) -> Subject(I) with countersubject
      - Episode 1: Sequential passage modulating to relative major/dominant
      - Middle Entry: Subject in a related key
      - Episode 2: Sequential passage modulating back
      - Final Entry: Subject in tonic, possibly with stretto
      - Coda: Dominant pedal -> tonic cadence

    Bar distribution roughly:
      Exposition ~35%, Episode1 ~15%, Middle ~15%, Episode2 ~15%, Final ~12%, Coda ~8%
    """
    is_minor = _key_is_minor(home_key)
    related_key = _relative_major(home_key) if is_minor else _dominant_key(home_key)

    # Bar distribution
    expo_bars = max(6, round(total_bars * 0.35))
    ep1_bars = max(3, round(total_bars * 0.15))
    mid_bars = max(3, round(total_bars * 0.15))
    ep2_bars = max(3, round(total_bars * 0.15))
    final_bars = max(3, round(total_bars * 0.12))
    coda_bars = max(2, total_bars - expo_bars - ep1_bars - mid_bars - ep2_bars - final_bars)

    # Subject length in bars (2-4, must fit in exposition with answer+subject)
    subject_bars = max(2, min(4, expo_bars // num_voices))

    exposition = SectionIR(
        type=SectionType.FUGUE_EXPOSITION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.SUBJECT_ENTRY, key=home_key,
                bars=subject_bars, character=character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=None,
                notes=f"voice_0_subject",
            ),
            SubsectionIR(
                type=SubsectionType.ANSWER_ENTRY, key=home_key,
                bars=subject_bars, character=character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=None,
                notes=f"voice_1_answer",
            ),
            SubsectionIR(
                type=SubsectionType.SUBJECT_ENTRY, key=home_key,
                bars=max(2, expo_bars - 2 * subject_bars), character=character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.HC,
                notes=f"voice_2_subject",
            ),
        ],
        key_path=[home_key, home_key, home_key],
    )

    episode_1 = SectionIR(
        type=SectionType.EPISODE, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.TR, key=home_key,
                bars=ep1_bars, character=CharacterToken.AGITATED,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.HC,
                notes="episode_sequential",
            ),
        ],
        key_path=[home_key, related_key],
    )

    middle_entry = SectionIR(
        type=SectionType.MIDDLE_ENTRY, key=related_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.SUBJECT_ENTRY, key=related_key,
                bars=mid_bars, character=character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.PAC,
                notes="middle_subject",
            ),
        ],
        key_path=[related_key],
    )

    episode_2 = SectionIR(
        type=SectionType.EPISODE, key=related_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.TR, key=related_key,
                bars=ep2_bars, character=CharacterToken.MYSTERIOUS,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.HC,
                notes="episode_sequential",
            ),
        ],
        key_path=[related_key, home_key],
    )

    final_entry = SectionIR(
        type=SectionType.STRETTO, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.SUBJECT_ENTRY, key=home_key,
                bars=final_bars, character=character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.PAC,
                notes="stretto_subject",
            ),
        ],
        key_path=[home_key],
    )

    coda = SectionIR(
        type=SectionType.CODA, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.PEDAL_POINT, key=home_key,
                bars=coda_bars, character=character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.PAC,
                notes="dominant_pedal_to_tonic",
            ),
        ],
        key_path=[home_key],
    )

    return [exposition, episode_1, middle_entry, episode_2, final_entry, coda]


# -- Fugue subject/answer/countersubject generators --

def _generate_fugue_subject(seed_motif: SeedMotif, home_key: KeyToken,
                            subject_bars: int = 2) -> FugueSubject:
    """
    Build the fugue subject from the seed motif, then derive the answer
    (tonal answer at the dominant) and a countersubject.

    The subject IS the seed motif extended to fill subject_bars.
    The tonal answer transposes by +7 semitones (perfect fifth) but mutates
    scale degree 5->1 at the start (the hallmark of a tonal answer).
    The countersubject uses contrary motion (inversion) with complementary rhythm.
    """
    # --- Subject: extend seed motif to fill subject_bars ---
    target_beats = subject_bars * 4.0
    subj_ivls = list(seed_motif.intervals)
    subj_rhy = list(seed_motif.rhythm)

    # Extend or trim to fill the bar count
    current_beats = sum(subj_rhy)
    while current_beats < target_beats - 0.5:
        # Append more notes from the motif cyclically
        idx = len(subj_ivls) % len(seed_motif.intervals) if seed_motif.intervals else 0
        if seed_motif.intervals:
            subj_ivls.append(seed_motif.intervals[idx])
        else:
            subj_ivls.append(rng().choice([1, 2, -1, -2]))
        r_idx = (len(subj_rhy)) % len(seed_motif.rhythm)
        subj_rhy.append(seed_motif.rhythm[r_idx])
        current_beats = sum(subj_rhy)

    # Trim if we overshot
    while sum(subj_rhy) > target_beats + 0.5 and len(subj_rhy) > 2:
        subj_rhy.pop()
        if len(subj_ivls) >= len(subj_rhy):
            subj_ivls.pop()

    subject = SeedMotif(intervals=subj_ivls, rhythm=subj_rhy)

    # --- Tonal Answer: transpose intervals up a 5th (7 semitones) ---
    ans_ivls = list(subj_ivls)
    if ans_ivls:
        original_first = ans_ivls[0]
        mutation = -1 if original_first > 0 else 1
        ans_ivls[0] = original_first + mutation

    answer = SeedMotif(intervals=ans_ivls, rhythm=list(subj_rhy))

    # --- Countersubject: inverted motion, offset rhythms ---
    cs_ivls = [-iv for iv in subj_ivls]  # inversion
    cs_rhy = list(subj_rhy)
    if len(cs_rhy) >= 2:
        for idx in range(0, len(cs_rhy) - 1, 2):
            cs_rhy[idx], cs_rhy[idx + 1] = cs_rhy[idx + 1], cs_rhy[idx]

    countersubject = SeedMotif(intervals=cs_ivls, rhythm=cs_rhy)

    return FugueSubject(
        subject=subject,
        answer=answer,
        countersubject=countersubject,
        subject_bars=subject_bars,
    )


def _build_fugue_episode_sequence(subject: SeedMotif,
                                  bars: int,
                                  direction: int = -1) -> SeedMotif:
    """
    Build a sequential passage for a fugue episode.
    Takes the first 3-4 notes of the subject and sequences them
    (repeats transposed by step in the given direction).

    Args:
        subject: The fugue subject motif
        bars: Number of bars for the episode
        direction: -1 for descending sequence, +1 for ascending
    """
    # Fragment: first 3-4 intervals of subject
    frag_len = min(3, len(subject.intervals))
    frag_ivls = subject.intervals[:frag_len]
    frag_rhy = subject.rhythm[:frag_len + 1]

    # How many times to repeat the fragment
    target_beats = bars * 4.0
    frag_beats = sum(frag_rhy)
    if frag_beats <= 0:
        frag_beats = 2.0
    repetitions = max(2, int(target_beats / frag_beats))

    # Build the sequence: fragment, step, fragment, step, ...
    seq_ivls: List[int] = []
    seq_rhy: List[float] = list(frag_rhy)  # first statement rhythm

    step_interval = direction * 2  # step down/up by a whole tone between repeats

    for rep in range(1, repetitions):
        seq_ivls.extend(frag_ivls)
        seq_ivls.append(step_interval)  # bridge interval between repetitions
        seq_rhy.extend(frag_rhy)

    # Final statement
    seq_ivls.extend(frag_ivls)

    # Trim to target length
    total = sum(seq_rhy)
    while total > target_beats + 0.5 and len(seq_rhy) > 2:
        seq_rhy.pop()
        if len(seq_ivls) >= len(seq_rhy):
            seq_ivls.pop()
        total = sum(seq_rhy)

    return SeedMotif(intervals=seq_ivls, rhythm=seq_rhy)


def _get_fugue_voice_ranges() -> Dict[str, Tuple[int, int]]:
    """Return MIDI pitch ranges for the three fugue voices (piano)."""
    return {
        "soprano": (60, 84),   # C4-C6
        "alto": (53, 74),      # F3-D5
        "bass": (36, 60),      # C2-C4
    }


def _fugue_start_pitch(voice: str, home_key: KeyToken) -> int:
    """Get a good starting pitch for each fugue voice in the given key."""
    m21_str = _KEY_TO_M21.get(home_key, "C")
    k = m21key.Key(m21_str)
    tonic_pc = k.tonic.pitchClass

    ranges = _get_fugue_voice_ranges()
    lo, hi = ranges.get(voice, (48, 72))
    mid = (lo + hi) // 2

    # Find the tonic pitch class nearest to the middle of the range
    for candidate in range(mid - 6, mid + 7):
        if candidate % 12 == tonic_pc and lo <= candidate <= hi:
            return candidate
    return mid
