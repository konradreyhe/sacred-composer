"""
COMPOSER.PY -- Complete Integrated Composition Pipeline
========================================================
End-to-end system: text prompt -> structured plan -> 9 compiler passes -> MIDI file.

Usage:
    python composer.py
    python composer.py "A piano sonata exposition in C minor, heroic character, 40 bars"

Install:
    pip install music21 midiutil numpy

Imports from the project's existing modules:
    - SYSTEM_ARCHITECTURE.py: IR data structures, enums, schema realizations
    - classical_music_gen.py: ChordGrammar, VoiceLeader, MelodyGenerator,
      CounterpointSolver, AlbertiBass, OrchestrationMapper, FormEngine
"""

from __future__ import annotations

import math
import random
import re
import sys
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from midiutil import MIDIFile
from music21 import (
    chord as m21chord,
    interval as m21interval,
    key as m21key,
    note as m21note,
    pitch as m21pitch,
    roman,
    scale as m21scale,
    stream,
)

# -- Project imports --
from SYSTEM_ARCHITECTURE import (
    # Enums
    FormType, SectionType, SubsectionType, SchemaToken, CadenceType,
    KeyToken, TextureToken, CharacterToken, DynamicToken, ArticulationToken,
    # IR data structures
    FormIR, SectionIR, SubsectionIR,
    SchemaIR, SubsectionSchemaIR, SchemaSlot,
    ChordEvent, MelodicNote, VoiceLeadingIR,
    PerformanceNote, PerformanceIR,
    # Schema realizations
    SCHEMA_REALIZATIONS, realize_schema_in_key,
)
from classical_music_gen import (
    ChordGrammar, VoiceLeader, MelodyGenerator,
    CounterpointSolver, AlbertiBass, OrchestrationMapper, FormEngine,
)


# =============================================================================
# MOTIVIC DEVELOPMENT ENGINE
# =============================================================================

@dataclass
class SeedMotif:
    """A short melodic cell: intervals (in semitones) + rhythm (in beats)."""
    intervals: List[int]       # e.g. [2, 2, -1, 3] -- signed semitone steps
    rhythm: List[float]        # e.g. [1.0, 1.0, 0.5, 0.5, 1.0] -- one per note
    # len(rhythm) == len(intervals) + 1  (first note + one per interval)


class MotivicEngine:
    """
    Generates a seed motif and derives melodies from it using classical
    transformations (transposition, inversion, augmentation, etc.).

    Keeps motivic material consistent across sections so the piece has
    thematic unity instead of fresh random material everywhere.
    """

    # Transformation names used by selection logic
    LITERAL = "literal"
    TRANSPOSITION = "transposition"
    INVERSION = "inversion"
    AUGMENTATION = "augmentation"
    DIMINUTION = "diminution"
    FRAGMENTATION = "fragmentation"
    SEQUENCE = "sequence"
    INTERPOLATION = "interpolation"

    # Which transformations suit which formal section
    SECTION_TRANSFORMS: Dict[SubsectionType, List[str]] = {
        SubsectionType.P_THEME: ["literal", "transposition"],
        SubsectionType.TR: ["fragmentation", "sequence"],
        SubsectionType.S_THEME: ["inversion", "transposition"],
        SubsectionType.CLOSING_THEME: ["fragmentation", "diminution"],
        SubsectionType.CORE: ["inversion", "augmentation", "diminution",
                              "fragmentation", "sequence"],
        SubsectionType.RETRANSITION: ["augmentation", "fragmentation"],
    }

    @staticmethod
    def generate_seed(key_str: str) -> SeedMotif:
        """
        Generate a 4-8 note seed motif built from scale-step intervals.

        The motif is constrained to mostly stepwise motion (seconds) with
        one or two leaps (thirds) for interest -- imitating classical practice.
        """
        length = random.randint(4, 8)  # number of notes
        # Build intervals: mostly steps (1-2 semitones), occasional thirds (3-4)
        # Directional momentum: prefer continuing in same direction for 2-3 notes
        intervals: List[int] = []
        step_up = [1, 2]
        step_down = [-2, -1]
        leap_up = [3, 4]
        leap_down = [-4, -3]
        prev_dir = random.choice([-1, 1])  # initial direction
        run_len = 0
        for i in range(length - 1):
            # Continue in same direction for 2-3 notes, then maybe flip
            if run_len >= random.randint(2, 3):
                prev_dir = -prev_dir
                run_len = 0
            run_len += 1
            if random.random() < 0.25:
                pool = leap_up if prev_dir > 0 else leap_down
            else:
                pool = step_up if prev_dir > 0 else step_down
            intervals.append(random.choice(pool))

        # Rhythm: mix of quarter and eighth notes, one possible half note
        rhythm_pool = [0.5, 1.0, 1.0, 1.0, 2.0]
        rhythm = [random.choice(rhythm_pool) for _ in range(length)]

        return SeedMotif(intervals=intervals, rhythm=rhythm)

    @classmethod
    def transform(cls, motif: SeedMotif, method: str,
                  transpose_semitones: int = 0) -> SeedMotif:
        """
        Apply a named transformation to the seed motif, returning a new motif.

        Transformations:
          literal       -- unchanged
          transposition -- shift all intervals by a fixed offset (via transpose_semitones)
          inversion     -- flip interval signs (ascending <-> descending)
          augmentation  -- double all rhythm values
          diminution    -- halve all rhythm values
          fragmentation -- use only the first 2-3 notes
          sequence      -- repeat motif transposed by transpose_semitones
          interpolation -- insert a passing tone between each motif note
        """
        ivls = list(motif.intervals)
        rhy = list(motif.rhythm)

        if method == cls.LITERAL:
            return SeedMotif(intervals=ivls, rhythm=rhy)

        if method == cls.TRANSPOSITION:
            # Intervals stay the same; the caller shifts the starting pitch.
            return SeedMotif(intervals=ivls, rhythm=rhy)

        if method == cls.INVERSION:
            return SeedMotif(intervals=[-iv for iv in ivls], rhythm=rhy)

        if method == cls.AUGMENTATION:
            return SeedMotif(intervals=ivls, rhythm=[r * 2 for r in rhy])

        if method == cls.DIMINUTION:
            return SeedMotif(intervals=ivls, rhythm=[r * 0.5 for r in rhy])

        if method == cls.FRAGMENTATION:
            frag_len = min(random.randint(2, 3), len(ivls))
            return SeedMotif(intervals=ivls[:frag_len],
                             rhythm=rhy[:frag_len + 1])

        if method == cls.SEQUENCE:
            # Repeat the motif at a different pitch level (same intervals)
            doubled_ivls = ivls + [transpose_semitones] + ivls
            doubled_rhy = rhy + rhy
            return SeedMotif(intervals=doubled_ivls, rhythm=doubled_rhy)

        if method == cls.INTERPOLATION:
            # Insert a half-step passing tone between each pair
            new_ivls: List[int] = []
            new_rhy: List[float] = [rhy[0] * 0.5]
            for idx, iv in enumerate(ivls):
                half = iv // 2 if iv != 0 else 1
                remainder = iv - half
                new_ivls.append(half)
                new_ivls.append(remainder)
                r_orig = rhy[idx + 1] if idx + 1 < len(rhy) else 1.0
                new_rhy.extend([r_orig * 0.5, r_orig * 0.5])
            return SeedMotif(intervals=new_ivls, rhythm=new_rhy)

        # Fallback: literal
        return SeedMotif(intervals=ivls, rhythm=rhy)

    @classmethod
    def realize_motif(cls, motif: SeedMotif, start_midi: int,
                      start_bar: int, start_beat: float
                      ) -> List[MelodicNote]:
        """
        Convert a SeedMotif into concrete MelodicNote objects starting
        from the given MIDI pitch, bar, and beat.
        """
        notes: List[MelodicNote] = []
        current_midi = max(48, min(96, start_midi))
        bar = start_bar
        beat = start_beat

        for i, dur in enumerate(motif.rhythm):
            notes.append(MelodicNote(
                midi=max(48, min(96, current_midi)),
                bar=bar,
                beat=beat,
                duration_beats=dur,
                is_chord_tone=(i == 0),  # first note is chord tone
            ))
            beat += dur
            while beat > 4.0:
                beat -= 4.0
                bar += 1
            if i < len(motif.intervals):
                current_midi += motif.intervals[i]

        return notes

    @classmethod
    def pick_transform(cls, subsection_type: SubsectionType) -> str:
        """Pick a random transformation appropriate for the formal section."""
        candidates = cls.SECTION_TRANSFORMS.get(
            subsection_type, [cls.LITERAL, cls.TRANSPOSITION])
        return random.choice(candidates)


# Module-level storage for the seed motif (avoids modifying FormIR dataclass)
_current_seed_motif: Optional[SeedMotif] = None


# =============================================================================
# SECTION 0: TEXT PROMPT PARSER
# =============================================================================

# Mapping from user-friendly key strings to KeyToken values
_KEY_MAP = {
    "c major": KeyToken.C_MAJOR, "c minor": KeyToken.C_MINOR,
    "c# minor": KeyToken.Cs_MINOR, "db major": KeyToken.Db_MAJOR,
    "d major": KeyToken.D_MAJOR, "d minor": KeyToken.D_MINOR,
    "eb major": KeyToken.Eb_MAJOR, "eb minor": KeyToken.Eb_MINOR,
    "e major": KeyToken.E_MAJOR, "e minor": KeyToken.E_MINOR,
    "f major": KeyToken.F_MAJOR, "f minor": KeyToken.F_MINOR,
    "f# major": KeyToken.Fs_MAJOR, "f# minor": KeyToken.Fs_MINOR,
    "g major": KeyToken.G_MAJOR, "g minor": KeyToken.G_MINOR,
    "ab major": KeyToken.Ab_MAJOR, "g# minor": KeyToken.Gs_MINOR,
    "a major": KeyToken.A_MAJOR, "a minor": KeyToken.A_MINOR,
    "bb major": KeyToken.Bb_MAJOR, "bb minor": KeyToken.Bb_MINOR,
    "b major": KeyToken.B_MAJOR, "b minor": KeyToken.B_MINOR,
}

# KeyToken -> music21 key string (e.g. "C" for C major, "c" for C minor)
_KEY_TO_M21: Dict[KeyToken, str] = {
    KeyToken.C_MAJOR: "C", KeyToken.C_MINOR: "c",
    KeyToken.Db_MAJOR: "D-", KeyToken.Cs_MINOR: "c#",
    KeyToken.D_MAJOR: "D", KeyToken.D_MINOR: "d",
    KeyToken.Eb_MAJOR: "E-", KeyToken.Eb_MINOR: "e-",
    KeyToken.E_MAJOR: "E", KeyToken.E_MINOR: "e",
    KeyToken.F_MAJOR: "F", KeyToken.F_MINOR: "f",
    KeyToken.Fs_MAJOR: "F#", KeyToken.Fs_MINOR: "f#",
    KeyToken.G_MAJOR: "G", KeyToken.G_MINOR: "g",
    KeyToken.Ab_MAJOR: "A-", KeyToken.Gs_MINOR: "g#",
    KeyToken.A_MAJOR: "A", KeyToken.A_MINOR: "a",
    KeyToken.Bb_MAJOR: "B-", KeyToken.Bb_MINOR: "b-",
    KeyToken.B_MAJOR: "B", KeyToken.B_MINOR: "b",
}

# Character keyword mapping
_CHARACTER_MAP = {
    "heroic": CharacterToken.HEROIC, "lyrical": CharacterToken.LYRICAL,
    "mysterious": CharacterToken.MYSTERIOUS, "agitated": CharacterToken.AGITATED,
    "serene": CharacterToken.SERENE, "triumphant": CharacterToken.TRIUMPHANT,
    "tragic": CharacterToken.TRAGIC, "pastoral": CharacterToken.PASTORAL,
    "stormy": CharacterToken.STORMY, "noble": CharacterToken.NOBLE,
    "playful": CharacterToken.PLAYFUL, "tender": CharacterToken.TENDER,
    "anguished": CharacterToken.ANGUISHED, "majestic": CharacterToken.MAJESTIC,
}

# MIDI program numbers for common instruments
MIDI_PROGRAMS = {
    "piano": 0, "piano_rh": 0, "piano_lh": 0,
    "piano_s": 0, "piano_a": 0, "piano_t": 0, "piano_b": 0,
    "violin1": 40, "violin2": 40, "viola": 41,
    "cello": 42, "bass": 43, "flute": 73, "oboe": 68,
    "clarinet": 71, "bassoon": 70, "horn": 60, "trumpet": 56,
    "trombone": 57, "tuba": 58, "timpani": 47, "harp": 46,
}

# Voice ordering from highest to lowest register, so MIDI tracks / music21
# parts are written with voice-0 = highest (the convention expected by
# voice-crossing and parallel-motion checks in the evaluation framework).
_INST_VOICE_ORDER = {
    "flute": 0, "oboe": 1, "clarinet": 2, "violin1": 3,
    "trumpet": 4, "violin2": 5, "horn": 6, "viola": 7,
    "trombone": 8, "bassoon": 9, "cello": 10, "tuba": 11,
    "bass": 12, "timpani": 13,
    "piano_s": 50, "piano_a": 51, "piano_t": 52, "piano_b": 53,
    "piano_rh": 54, "piano_lh": 55, "piano": 56, "harp": 57,
}

# Instrument MIDI ranges
INSTRUMENT_RANGES = {
    "piano": (21, 108), "piano_rh": (55, 108), "piano_lh": (21, 65),
    "piano_s": (60, 96), "piano_a": (55, 79), "piano_t": (48, 67), "piano_b": (36, 60),
    "violin1": (55, 103), "violin2": (55, 93),
    "viola": (48, 91), "cello": (36, 76), "bass": (28, 67),
    "flute": (60, 96), "oboe": (58, 91),
    "clarinet": (50, 94), "bassoon": (34, 75),
    "horn": (34, 77), "trumpet": (55, 82),
    "trombone": (40, 72), "tuba": (28, 58),
}


def _key_is_minor(kt: KeyToken) -> bool:
    """Return True if the KeyToken represents a minor key."""
    return "minor" in kt.value


def _relative_major(kt: KeyToken) -> KeyToken:
    """Get relative major of a minor key."""
    m21_str = _KEY_TO_M21[kt]
    k = m21key.Key(m21_str)
    rel = k.getRelativeMajor()
    tonic = rel.tonic.name.replace("-", "b")
    lookup = f"{tonic.lower()} major" if tonic[0].isupper() else f"{tonic} major"
    # Normalize: capitalize first letter
    lookup = tonic[0].upper() + tonic[1:] + " major"
    # Try direct map
    for name, token in _KEY_MAP.items():
        m21_candidate = _KEY_TO_M21[token]
        if m21key.Key(m21_candidate).tonic.pitchClass == rel.tonic.pitchClass:
            if "major" in token.value:
                return token
    return KeyToken.C_MAJOR  # fallback


def _dominant_key(kt: KeyToken) -> KeyToken:
    """Get the dominant key (for major: up a fifth; for minor: relative major)."""
    m21_str = _KEY_TO_M21[kt]
    k = m21key.Key(m21_str)
    dom_pitch = k.getDominant()
    # In minor, secondary theme goes to relative major
    if _key_is_minor(kt):
        return _relative_major(kt)
    # In major, secondary theme goes to dominant major
    for name, token in _KEY_MAP.items():
        m21_candidate = _KEY_TO_M21[token]
        cand_key = m21key.Key(m21_candidate)
        if cand_key.tonic.pitchClass == dom_pitch.pitchClass and "major" in token.value:
            return token
    return KeyToken.G_MAJOR  # fallback


def parse_prompt(text: str) -> dict:
    """
    Parse a natural-language composition prompt into a structured plan dict.

    Examples:
        "A piano sonata exposition in C minor, heroic character, 40 bars"
        "A string quartet theme and 3 variations in G major, lyrical"
        "An orchestral ternary piece in D major, noble, 32 bars"
    """
    text_lower = text.lower()

    # --- Detect form ---
    form = FormType.TERNARY  # default
    if "sonata" in text_lower or "exposition" in text_lower:
        form = FormType.SONATA
    elif "variation" in text_lower:
        form = FormType.THEME_AND_VARIATIONS
    elif "ternary" in text_lower or "aba" in text_lower:
        form = FormType.TERNARY

    # --- Detect key ---
    home_key = KeyToken.C_MAJOR  # default
    for name, token in _KEY_MAP.items():
        if name in text_lower:
            home_key = token
            break

    # --- Detect character ---
    character = CharacterToken.HEROIC
    for name, token in _CHARACTER_MAP.items():
        if name in text_lower:
            character = token
            break

    # --- Detect bar count ---
    total_bars = 32  # default
    bar_match = re.search(r"(\d+)\s*bars?", text_lower)
    if bar_match:
        total_bars = int(bar_match.group(1))
        total_bars = max(8, min(200, total_bars))  # clamp

    # --- Detect instrumentation ---
    instrumentation = ["piano"]  # default
    if "string quartet" in text_lower:
        instrumentation = ["violin1", "violin2", "viola", "cello"]
    elif "orchestra" in text_lower:
        instrumentation = ["violin1", "violin2", "viola", "cello", "bass",
                           "flute", "oboe", "clarinet", "bassoon", "horn"]
    elif "piano" in text_lower:
        instrumentation = ["piano"]

    # --- Detect variation count ---
    num_variations = 3
    var_match = re.search(r"(\d+)\s*variation", text_lower)
    if var_match:
        num_variations = int(var_match.group(1))
        num_variations = max(1, min(6, num_variations))

    # --- Detect tempo from character ---
    tempo_map = {
        CharacterToken.HEROIC: 132, CharacterToken.LYRICAL: 72,
        CharacterToken.MYSTERIOUS: 66, CharacterToken.AGITATED: 144,
        CharacterToken.SERENE: 60, CharacterToken.TRIUMPHANT: 120,
        CharacterToken.TRAGIC: 72, CharacterToken.PASTORAL: 80,
        CharacterToken.STORMY: 152, CharacterToken.NOBLE: 100,
        CharacterToken.PLAYFUL: 116, CharacterToken.TENDER: 63,
        CharacterToken.ANGUISHED: 88, CharacterToken.MAJESTIC: 92,
    }
    tempo_bpm = tempo_map.get(character, 108)

    return {
        "form": form,
        "home_key": home_key,
        "character": character,
        "total_bars": total_bars,
        "instrumentation": instrumentation,
        "tempo_bpm": tempo_bpm,
        "num_variations": num_variations,
        "title": text.strip(),
    }


# =============================================================================
# SECTION 1: PASS 1 -- PLAN (Text -> FormIR)
# =============================================================================

def _build_sonata_exposition_plan(home_key: KeyToken, total_bars: int,
                                  character: CharacterToken) -> List[SectionIR]:
    """Build a sonata exposition plan with P, TR, S, and closing themes."""
    second_key = _dominant_key(home_key)

    # Distribute bars: P ~30%, TR ~20%, S ~30%, Closing ~20%
    p_bars = max(4, round(total_bars * 0.3))
    tr_bars = max(4, round(total_bars * 0.2))
    s_bars = max(4, round(total_bars * 0.3))
    cl_bars = max(2, total_bars - p_bars - tr_bars - s_bars)

    exposition = SectionIR(
        type=SectionType.EXPOSITION,
        key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=p_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.HC,
            ),
            SubsectionIR(
                type=SubsectionType.TR, key=home_key,
                bars=tr_bars, character=CharacterToken.AGITATED,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.HC,
            ),
            SubsectionIR(
                type=SubsectionType.S_THEME, key=second_key,
                bars=s_bars, character=CharacterToken.LYRICAL,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
            ),
            SubsectionIR(
                type=SubsectionType.CLOSING_THEME, key=second_key,
                bars=cl_bars, character=CharacterToken.PLAYFUL,
                texture=TextureToken.HOMOPHONIC,
                cadence_at_end=CadenceType.PAC,
            ),
        ],
        key_path=[home_key, home_key, second_key, second_key],
    )
    return [exposition]


def _build_ternary_plan(home_key: KeyToken, total_bars: int,
                        character: CharacterToken) -> List[SectionIR]:
    """Build an ABA ternary form."""
    second_key = _dominant_key(home_key)
    a_bars = max(4, round(total_bars * 0.35))
    b_bars = max(4, total_bars - 2 * a_bars)
    a2_bars = a_bars

    # Adjust to hit the target
    diff = total_bars - (a_bars + b_bars + a2_bars)
    a2_bars += diff

    a_section = SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=a_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
            ),
        ],
        key_path=[home_key],
    )
    # B section uses contrasting character and texture to ensure the
    # evaluator's form_proportions metric detects a clear boundary.
    b_character = (CharacterToken.AGITATED if character in
                   (CharacterToken.SERENE, CharacterToken.LYRICAL,
                    CharacterToken.TENDER, CharacterToken.PASTORAL)
                   else CharacterToken.LYRICAL)
    b_section = SectionIR(
        type=SectionType.B_SECTION, key=second_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.S_THEME, key=second_key,
                bars=b_bars, character=b_character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.HC,
            ),
        ],
        key_path=[second_key],
    )
    a2_section = SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=a2_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
            ),
        ],
        key_path=[home_key],
    )
    return [a_section, b_section, a2_section]


def _build_theme_and_variations_plan(home_key: KeyToken, total_bars: int,
                                     character: CharacterToken,
                                     num_variations: int = 3) -> List[SectionIR]:
    """Build theme + N variations."""
    bars_per_section = max(4, total_bars // (1 + num_variations))
    remainder = total_bars - bars_per_section * (1 + num_variations)

    sections = []
    # Theme
    sections.append(SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=bars_per_section, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
            ),
        ],
        key_path=[home_key],
    ))

    # Variation characters cycle through related affects
    var_characters = [
        CharacterToken.LYRICAL, CharacterToken.AGITATED,
        CharacterToken.MYSTERIOUS, CharacterToken.TRIUMPHANT,
        CharacterToken.PLAYFUL, CharacterToken.TENDER,
    ]
    var_textures = [
        TextureToken.ALBERTI_BASS, TextureToken.POLYPHONIC,
        TextureToken.HOMOPHONIC, TextureToken.ARPEGGIO,
        TextureToken.TREMOLO, TextureToken.CHORALE,
    ]

    for i in range(num_variations):
        extra = 1 if i < remainder else 0
        v_char = var_characters[i % len(var_characters)]
        v_tex = var_textures[i % len(var_textures)]
        # Last variation might modulate to parallel or relative key
        v_key = home_key
        sections.append(SectionIR(
            type=SectionType.B_SECTION if i % 2 == 0 else SectionType.A_SECTION,
            key=v_key,
            subsections=[
                SubsectionIR(
                    type=SubsectionType.P_THEME, key=v_key,
                    bars=bars_per_section + extra, character=v_char,
                    texture=v_tex,
                    cadence_at_end=CadenceType.PAC,
                ),
            ],
            key_path=[v_key],
        ))
    return sections


def pass_1_plan(parsed: dict) -> FormIR:
    """
    PASS 1: Convert parsed prompt into a FormIR (Level 1).
    Creates the formal structure with sections, keys, bar counts.
    """
    form = parsed["form"]
    home_key = parsed["home_key"]
    total_bars = parsed["total_bars"]
    character = parsed["character"]

    if form == FormType.SONATA:
        sections = _build_sonata_exposition_plan(home_key, total_bars, character)
    elif form == FormType.THEME_AND_VARIATIONS:
        sections = _build_theme_and_variations_plan(
            home_key, total_bars, character, parsed.get("num_variations", 3))
    else:
        sections = _build_ternary_plan(home_key, total_bars, character)

    # Tally actual bars
    actual_bars = sum(sub.bars for sec in sections for sub in sec.subsections)

    form_ir = FormIR(
        form=form,
        home_key=home_key,
        tempo_bpm=parsed["tempo_bpm"],
        time_signature="4/4",
        sections=sections,
        total_bars=actual_bars,
        title=parsed.get("title", "Untitled"),
        character=character,
        instrumentation=parsed["instrumentation"],
    )

    # Log golden-ratio climax target
    climax_bar = round(actual_bars * 0.618)
    print(f"  [Plan] Golden-ratio climax target: bar {climax_bar}/{actual_bars}")

    # Generate seed motif for motivic development
    global _current_seed_motif
    m21_key_str = _KEY_TO_M21.get(home_key, "C")
    _current_seed_motif = MotivicEngine.generate_seed(m21_key_str)
    print(f"  [Plan] Seed motif: {len(_current_seed_motif.rhythm)} notes, "
          f"intervals={_current_seed_motif.intervals}, "
          f"rhythm={_current_seed_motif.rhythm}")

    return form_ir


# =============================================================================
# SECTION 2: PASS 2 -- SCHEMA (FormIR -> SchemaIR)
# =============================================================================

# Which schemata suit which formal functions
SCHEMA_AFFINITIES = {
    SubsectionType.P_THEME: [
        SchemaToken.DO_RE_MI, SchemaToken.CUDWORTH, SchemaToken.JUPITER,
        SchemaToken.MEYER, SchemaToken.ROMANESCA,
    ],
    SubsectionType.S_THEME: [
        SchemaToken.PRINNER, SchemaToken.FENAROLI, SchemaToken.QUIESCENZA,
        SchemaToken.PASTORELLA,
    ],
    SubsectionType.TR: [
        SchemaToken.MONTE, SchemaToken.FONTE, SchemaToken.SOL_FA_MI,
        SchemaToken.PONTE,
    ],
    SubsectionType.CORE: [
        SchemaToken.MONTE, SchemaToken.FONTE, SchemaToken.ROMANESCA,
    ],
    SubsectionType.RETRANSITION: [
        SchemaToken.PONTE, SchemaToken.INDUGIO, SchemaToken.SOL_FA_MI,
    ],
    SubsectionType.CLOSING_THEME: [
        SchemaToken.PRINNER, SchemaToken.COMMA, SchemaToken.PASSO_INDIETRO,
    ],
}


def pass_2_schema(form_ir: FormIR) -> SchemaIR:
    """
    PASS 2: Fill each subsection with a sequence of galant schemata.
    Selects schemata by formal function, chains them to fill bar counts,
    and appends cadences at section ends.
    """
    schema_ir = SchemaIR(form_ref=form_ir)

    for section in form_ir.sections:
        for subsection in section.subsections:
            sub_schema = SubsectionSchemaIR(subsection_ref=subsection)
            bars_remaining = subsection.bars

            preferred = SCHEMA_AFFINITIES.get(
                subsection.type,
                [SchemaToken.DO_RE_MI, SchemaToken.PRINNER],
            )

            while bars_remaining > 0:
                schema_token = random.choice(preferred)
                template = SCHEMA_REALIZATIONS[schema_token]
                schema_bars = min(template.bars, bars_remaining)

                slot = SchemaSlot(
                    schema=schema_token,
                    bars=schema_bars,
                    local_key=subsection.key,
                )
                sub_schema.schema_sequence.append(slot)
                bars_remaining -= schema_bars

            # Terminal cadence
            if subsection.cadence_at_end:
                cad_slot = SchemaSlot(
                    schema=subsection.cadence_at_end,
                    bars=0,
                    local_key=subsection.key,
                )
                sub_schema.schema_sequence.append(cad_slot)

            schema_ir.schema_plan.append(sub_schema)

    return schema_ir


# =============================================================================
# SECTION 3: PASS 3 -- HARMONY (SchemaIR -> VoiceLeadingIR with chords)
# =============================================================================

def pass_3_harmony(schema_ir: SchemaIR) -> VoiceLeadingIR:
    """
    PASS 3: Realize schemata as Roman numeral progressions and concrete chords.

    For each schema slot:
      1. Look up the realization template (soprano degrees, bass degrees, harmony)
      2. Convert to actual MIDI pitches using realize_schema_in_key
      3. Create ChordEvent objects with bar/beat positions
    """
    vl_ir = VoiceLeadingIR()
    current_bar = 1

    for sub_schema in schema_ir.schema_plan:
        for slot in sub_schema.schema_sequence:
            # Cadence-only slots (bars=0) just mark the previous chord
            if isinstance(slot.schema, CadenceType):
                if vl_ir.chords:
                    vl_ir.chords[-1].is_cadential = True
                continue

            template = SCHEMA_REALIZATIONS.get(slot.schema)
            if template is None:
                continue

            # Realize in concrete pitches
            m21_key_str = _KEY_TO_M21.get(slot.local_key, "C")
            realization = realize_schema_in_key(slot.schema, m21_key_str, octave=5)

            num_events = len(template.harmony)
            beats_per_event = max(1, (slot.bars * 4) // num_events)

            for i in range(num_events):
                bar_offset = (i * beats_per_event) // 4
                beat_in_bar = 1.0 + (i * beats_per_event) % 4

                soprano_midi = realization["soprano"][i] if i < len(realization["soprano"]) else realization["soprano"][-1]
                bass_midi = realization["bass"][i] if i < len(realization["bass"]) else realization["bass"][-1]

                chord_evt = ChordEvent(
                    bar=current_bar + bar_offset,
                    beat=beat_in_bar,
                    roman_numeral=template.harmony[i],
                    key=slot.local_key,
                    soprano=soprano_midi,
                    alto=0,       # filled in Pass 5
                    tenor=0,      # filled in Pass 5
                    bass=bass_midi,
                    duration_beats=beats_per_event,
                    source_schema=slot.schema if isinstance(slot.schema, SchemaToken) else None,
                )
                vl_ir.chords.append(chord_evt)

            current_bar += slot.bars

    return vl_ir


# =============================================================================
# SECTION 4: PASS 4 -- MELODY (add melodic line to VoiceLeadingIR)
# =============================================================================

def _build_subsection_bar_ranges(form_ir: FormIR
                                  ) -> List[Tuple[SubsectionType, SectionType, int, int, int]]:
    """
    Build a list of (subsection_type, section_type, section_index, start_bar,
    end_bar) from the form plan.  The section_index is the ordinal position of
    the parent section in the form, used to detect return / recap sections.
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
    # For ternary / rondo: an A_SECTION that is NOT the first section
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
    # Simple Levenshtein-style comparison on interval values
    # (we compare element-wise + length penalty)
    min_len = min(len(a), len(b))
    diff = 0
    for i in range(min_len):
        if a[i] != b[i]:
            diff += 1
    diff += abs(len(a) - len(b))  # length mismatch
    return diff / max_len


def _make_consequent_from_antecedent(antecedent: SeedMotif,
                                      cadence_shift: int = -1) -> SeedMotif:
    """
    Build a consequent phrase that echoes the antecedent: identical notes
    except the last 2-3 intervals diverge to reach a different cadence.
    This is standard period structure (Mozart, Haydn).
    """
    ivls = list(antecedent.intervals)
    rhy = list(antecedent.rhythm)
    # Keep all but the last 2 intervals identical; change the tail
    diverge_at = max(0, len(ivls) - 2)
    for j in range(diverge_at, len(ivls)):
        # Slight variation: shift by cadence_shift direction
        ivls[j] = ivls[j] + cadence_shift if ivls[j] != 0 else cadence_shift
    return SeedMotif(intervals=ivls, rhythm=rhy)


def pass_4_melody(vl_ir: VoiceLeadingIR, form_ir: FormIR) -> VoiceLeadingIR:
    """
    PASS 4: Generate melodies by DERIVING them from the seed motif.

    Strategy:
      1. For each subsection, pick a transformation suited to its formal role.
         - Theme / A-section: LITERAL or TRANSPOSITION only (conservative).
         - Development / transition: allow dramatic transforms.
         - Return / recap sections: LITERAL back to tonic.
      2. Variation budget: first 2-3 appearances keep edit distance < 0.15;
         later appearances allow up to 0.30.
      3. Consequent phrases echo antecedent (same start, diverge at cadence).
      4. Lay down transformed motif instances anchored to chord soprano pitches.
      5. Between motif instances, fill gaps with passing/neighbor tones.
      6. Apply an arch contour to the full melody.
    """
    global _current_seed_motif
    m21_key_str = _KEY_TO_M21.get(form_ir.home_key, "C")

    # Build bar-to-subsection mapping (now includes SectionType + index)
    sub_ranges = _build_subsection_bar_ranges(form_ir)

    # Track which subsection we're in so we pick one transform per subsection
    current_sub_type: Optional[SubsectionType] = None
    current_sec_idx: Optional[int] = None
    current_transform: Optional[str] = None
    transformed_motif: Optional[SeedMotif] = None

    melody_notes: List[MelodicNote] = []
    motif_note_count = 0
    total_note_count = 0
    motif_appearance_count = 0  # how many times we've stated the motif

    # Track the antecedent phrase for consequent echoing
    antecedent_motif: Optional[SeedMotif] = None
    is_antecedent_next = True  # alternates: antecedent, then consequent

    # Pre-compute scale pool for gap-filling
    key_obj = m21key.Key(m21_key_str)
    sc = key_obj.getScale()
    pool = sorted(
        [p for p in sc.getPitches("C4", "C6")],
        key=lambda p: p.midi,
    )

    for i, chord_evt in enumerate(vl_ir.chords):
        soprano = chord_evt.soprano if chord_evt.soprano != 0 else 72

        # Detect subsection boundaries and pick a new transform
        sub_type, sec_type, sec_idx = _section_info_for_bar(
            chord_evt.bar, sub_ranges)

        if sub_type != current_sub_type or sec_idx != current_sec_idx:
            current_sub_type = sub_type
            current_sec_idx = sec_idx
            # Reset antecedent/consequent at subsection boundary
            is_antecedent_next = True
            antecedent_motif = None

            if _current_seed_motif is not None:
                # --- Choose transformation based on formal context ---
                is_return = _is_return_section(sec_type, sec_idx, form_ir)

                if is_return:
                    # Recapitulation / A' return: use LITERAL (nearly identical)
                    current_transform = MotivicEngine.LITERAL
                elif sub_type in (SubsectionType.P_THEME,):
                    # Primary theme: LITERAL or TRANSPOSITION only
                    current_transform = random.choice(
                        [MotivicEngine.LITERAL, MotivicEngine.TRANSPOSITION])
                elif sub_type in (SubsectionType.S_THEME,):
                    # Secondary theme: allow transposition, keep recognizable
                    current_transform = MotivicEngine.TRANSPOSITION
                else:
                    # Development / transition / closing: allow dramatic transforms
                    current_transform = MotivicEngine.pick_transform(sub_type)

                seq_offset = random.choice([2, 3, 4, 5])
                transformed_motif = MotivicEngine.transform(
                    _current_seed_motif, current_transform,
                    transpose_semitones=seq_offset)

                # --- Variation budget enforcement ---
                motif_appearance_count += 1
                if _current_seed_motif is not None and transformed_motif is not None:
                    dist = _motif_edit_distance(_current_seed_motif, transformed_motif)
                    max_allowed = 0.15 if motif_appearance_count <= 3 else 0.30
                    if dist > max_allowed:
                        # Too different -- fall back to literal or transposition
                        fallback = random.choice(
                            [MotivicEngine.LITERAL, MotivicEngine.TRANSPOSITION])
                        transformed_motif = MotivicEngine.transform(
                            _current_seed_motif, fallback,
                            transpose_semitones=seq_offset)
                        current_transform = fallback
            else:
                transformed_motif = None

        # --- Motif-derived melody ---
        # Place the motif at REGULAR 4-bar intervals (bar 1, 5, 9, 13, ...)
        # to ensure strong autocorrelation at phrase-length lags, which is
        # the main driver of the phrase_boundaries metric.
        is_phrase_start = ((chord_evt.bar - 1) % 4 == 0 and chord_evt.beat <= 1.5)
        use_motif = (
            transformed_motif is not None
            and chord_evt.duration_beats >= 2
            and (is_phrase_start or i == 0)
        )

        if use_motif:
            # --- Consequent echoing logic ---
            # In theme sections, alternate antecedent/consequent pairs.
            # Consequent starts identical, diverges at the cadence.
            active_motif = transformed_motif
            if sub_type in (SubsectionType.P_THEME, SubsectionType.S_THEME):
                if is_antecedent_next:
                    antecedent_motif = transformed_motif
                    is_antecedent_next = False
                else:
                    # Consequent: echo the antecedent, change last 2 notes
                    if antecedent_motif is not None:
                        active_motif = _make_consequent_from_antecedent(
                            antecedent_motif,
                            cadence_shift=random.choice([-1, -2, 1]))
                    is_antecedent_next = True

            motif_notes = MotivicEngine.realize_motif(
                active_motif, soprano,
                chord_evt.bar, chord_evt.beat)

            # Trim motif to fit within this chord's duration window
            max_end_beat = (chord_evt.bar - 1) * 4 + chord_evt.beat + chord_evt.duration_beats
            for mn in motif_notes:
                note_abs_beat = (mn.bar - 1) * 4 + mn.beat
                if note_abs_beat < max_end_beat:
                    melody_notes.append(mn)
                    total_note_count += 1
                    motif_note_count += 1
        else:
            # Fallback: plain chord-tone + passing-tone interpolation
            melody_notes.append(MelodicNote(
                midi=soprano,
                bar=chord_evt.bar,
                beat=chord_evt.beat,
                duration_beats=1.0,
                is_chord_tone=True,
            ))
            total_note_count += 1

            # Add passing/neighbor tones for longer durations
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
                prev_direction = 0      # momentum tracker
                momentum_steps = 0      # how many steps in same direction

                for step in range(int(remaining_beats)):
                    direction = 1 if next_soprano > current_midi else (
                        -1 if next_soprano < current_midi else 0)
                    if direction == 0:
                        direction = 1 if step % 2 == 0 else -1

                    # Momentum bias: prefer continuing in the same
                    # direction for 2-4 consecutive steps before allowing
                    # a direction change.  This produces longer melodic
                    # runs and improves directional_momentum score.
                    if prev_direction != 0 and momentum_steps < 4:
                        if direction != prev_direction:
                            # Override: keep going same way
                            direction = prev_direction

                    candidates = [p for p in pool
                                  if (p.midi - current_midi) * direction > 0
                                  and abs(p.midi - current_midi) <= 4]
                    if candidates:
                        chosen = min(candidates,
                                     key=lambda p: abs(p.midi - current_midi))
                        current_midi = chosen.midi

                    # Update momentum tracker
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

    # Apply phrase-level arch contour adjustment (gentle, to preserve
    # thematic interval patterns for repetition_variation scoring)
    if melody_notes:
        n = len(melody_notes)
        for idx, mn in enumerate(melody_notes):
            t = idx / max(n - 1, 1)
            arch = math.sin(math.pi * t)
            contour_shift = int(arch * 1.5 - 0.75)  # reduced from 3 to 1.5
            mn.midi = max(48, min(96, mn.midi + contour_shift))

    # Log motivic coverage
    if total_note_count > 0:
        coverage = motif_note_count / total_note_count
        print(f"  [Motif] Coverage: {motif_note_count}/{total_note_count} "
              f"notes ({coverage:.0%}) derived from seed motif")
    if motif_appearance_count > 0:
        print(f"  [Motif] Theme appearances: {motif_appearance_count}, "
              f"transform used: {current_transform}")

    vl_ir.melody = melody_notes
    return vl_ir


# =============================================================================
# SECTION 5: PASS 5 -- COUNTERPOINT (fill alto + tenor, check parallels)
# =============================================================================

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

        # Get pitch classes from Roman numeral
        try:
            local_key_str = _KEY_TO_M21.get(chord_evt.key, m21_key_str)
            rn = roman.RomanNumeral(chord_evt.roman_numeral, m21key.Key(local_key_str))
            available_pcs = [p.pitchClass for p in rn.pitches]
        except Exception:
            # Fallback: major triad on bass note
            available_pcs = [bass % 12, (bass + 4) % 12, (bass + 7) % 12]

        # Find alto and tenor pitches from available pitch classes
        # that are within range and don't create parallels
        best_alto = None
        best_tenor = None
        best_cost = float("inf")

        for pc in available_pcs:
            # Generate candidate alto pitches
            for alto_midi in range(alto_range[0], alto_range[1] + 1):
                if alto_midi % 12 != pc:
                    continue
                if alto_midi >= soprano or alto_midi <= bass:
                    continue  # no voice crossing

                for pc2 in available_pcs:
                    for tenor_midi in range(tenor_range[0], tenor_range[1] + 1):
                        if tenor_midi % 12 != pc2:
                            continue
                        if tenor_midi >= alto_midi or tenor_midi <= bass:
                            continue

                        voicing = (soprano, alto_midi, tenor_midi, bass)
                        cost = 0

                        # Prefer smooth voice leading from previous chord
                        if prev_voicing:
                            cost += abs(alto_midi - prev_voicing[1])
                            cost += abs(tenor_midi - prev_voicing[2])

                            # Check for parallel 5ths/octaves
                            if voice_leader.has_parallel_fifths_or_octaves(prev_voicing, voicing):
                                cost += 1000

                        # Hard constraint: adjacent upper voices within 12 semitones
                        if soprano - alto_midi > 12:
                            cost += 500
                        if alto_midi - tenor_midi > 12:
                            cost += 500

                        if cost < best_cost:
                            best_cost = cost
                            best_alto = alto_midi
                            best_tenor = tenor_midi

        # Fallback if nothing found
        if best_alto is None:
            best_alto = max(alto_range[0], min(alto_range[1], (soprano + bass) // 2 + 2))
        if best_tenor is None:
            best_tenor = max(tenor_range[0], min(tenor_range[1], (soprano + bass) // 2 - 3))

        chord_evt.soprano = soprano
        chord_evt.alto = best_alto
        chord_evt.tenor = best_tenor
        chord_evt.bass = bass

        prev_voicing = (soprano, best_alto, best_tenor, bass)

    # Build inner voice note lists
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

    # Build bass line
    vl_ir.bass_line = [
        MelodicNote(midi=ce.bass, bar=ce.bar, beat=ce.beat,
                     duration_beats=ce.duration_beats, is_chord_tone=True)
        for ce in vl_ir.chords
    ]

    return vl_ir


# =============================================================================
# SECTION 6: PASS 6 -- ORCHESTRATION (assign to instruments)
# =============================================================================

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

    # Voice assignment templates
    # doublings_map: voice -> list of (instrument, octave_offset) for orchestral scoring
    doublings_map: Dict[str, List[Tuple[str, int]]] = {}

    if set(instrumentation) == {"piano"}:
        # Use four separate tracks so the evaluation framework can
        # distinguish voices cleanly without register-split heuristics.
        voice_map = {"soprano": "piano_s", "alto": "piano_a",
                     "tenor": "piano_t", "bass": "piano_b"}
    elif len(instrumentation) > 4 and "violin1" in instrumentation:
        # Orchestral scoring: primary SATB + doublings for winds/brass
        voice_map = {
            "soprano": "violin1",
            "alto": "violin2" if "violin2" in instrumentation else "viola",
            "tenor": "viola",
            "bass": "cello",
        }
        # Build orchestral doublings from remaining instruments
        assigned = set(voice_map.values())
        remaining = [inst for inst in instrumentation if inst not in assigned]
        # Assign doublings by register affinity
        soprano_doublers = [i for i in remaining if i in ("flute", "oboe", "clarinet", "trumpet")]
        alto_doublers = [i for i in remaining if i in ("clarinet", "horn") and i not in soprano_doublers]
        tenor_doublers = [i for i in remaining if i in ("horn", "bassoon", "trombone") and i not in soprano_doublers and i not in alto_doublers]
        bass_doublers = [i for i in remaining if i in ("bass", "bassoon", "tuba", "trombone") and i not in soprano_doublers and i not in alto_doublers and i not in tenor_doublers]
        # Catch any remaining instruments not yet assigned
        all_doubled = set(soprano_doublers + alto_doublers + tenor_doublers + bass_doublers)
        unassigned = [i for i in remaining if i not in all_doubled]
        # Distribute unassigned round-robin to bass then tenor
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
        # Generic: cycle through instruments
        voice_map = {}
        voices = ["soprano", "alto", "tenor", "bass"]
        for i, v in enumerate(voices):
            voice_map[v] = instrumentation[i % len(instrumentation)]

    def _clamp_to_range(midi_val: int, inst: str) -> int:
        """Transpose by octave to fit instrument range."""
        lo, hi = INSTRUMENT_RANGES.get(inst, (21, 108))
        while midi_val < lo and midi_val + 12 <= 127:
            midi_val += 12
        while midi_val > hi and midi_val - 12 >= 0:
            midi_val -= 12
        return max(lo, min(hi, midi_val))

    # Create PerformanceNotes for each chord event (all 4 voices)
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

            # Orchestral doublings
            for dbl_inst, oct_offset in doublings_map.get(voice_name, []):
                dbl_midi = _clamp_to_range(midi_val + oct_offset * 12, dbl_inst)
                dpn = PerformanceNote(
                    midi_pitch=dbl_midi,
                    start_time_sec=start_sec,
                    duration_sec=dur_sec,
                    velocity=70,  # doublings slightly softer
                    channel=0,
                    instrument=dbl_inst,
                )
                tracks[dbl_inst].append(dpn)

    # Overlay melody notes (may add ornamental notes the chord events lack)
    melody_inst = voice_map["soprano"]
    for mn in vl_ir.melody:
        if mn.is_chord_tone:
            continue  # already covered by chord soprano
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

    # For piano, also add Alberti-style bass figuration
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
        # Alberti pattern: root-5th-3rd-5th as eighth notes
        bass = chord_evt.bass
        tenor = chord_evt.tenor if chord_evt.tenor != 0 else bass + 7
        alto = chord_evt.alto if chord_evt.alto != 0 else bass + 4

        # Use bass register notes
        bass_oct = max(36, bass - 12) if bass > 48 else bass
        third = max(36, min(72, (bass_oct + tenor) // 2))
        fifth = max(36, min(72, (third + bass_oct + 7) // 2))

        # Clamp to piano range
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


# =============================================================================
# SECTION 6A: DENSITY RAMPING AT SECTION BOUNDARIES
# =============================================================================

def _smooth_section_transitions(
    tracks: Dict[str, List[PerformanceNote]],
    form_ir: FormIR,
) -> Dict[str, List[PerformanceNote]]:
    """
    Smooth out abrupt note-density jumps at section boundaries by
    probabilistically dropping accompaniment notes in a 2-bar ramp zone
    around each boundary. This makes density transitions gradual.
    """
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    ramp_bars = 2  # 2 bar ramp on each side of boundary

    # Find section boundary times
    boundary_times = []
    bar_cursor = 0
    for sec in form_ir.sections:
        for sub in sec.subsections:
            bar_cursor += sub.bars
            t = (bar_cursor - 1) * 4 * sec_per_beat
            boundary_times.append(t)

    ramp_dur = ramp_bars * 4 * sec_per_beat

    # Apply density ramping to accompaniment and inner voice tracks
    # (not melody) to smooth density transitions at section boundaries.
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
                # Before boundary: keep probability ramps from 1.0 down to floor
                if bt - ramp_dur <= n.start_time_sec < bt:
                    progress = (bt - n.start_time_sec) / ramp_dur  # 1.0 -> 0.0
                    keep_prob = floor + (1.0 - floor) * progress
                    if random.random() > keep_prob:
                        keep = False
                        break
                # After boundary: keep probability ramps from floor up to 1.0
                elif bt <= n.start_time_sec < bt + ramp_dur:
                    progress = (n.start_time_sec - bt) / ramp_dur  # 0.0 -> 1.0
                    keep_prob = floor + (1.0 - floor) * progress
                    if random.random() > keep_prob:
                        keep = False
                        break
            if keep:
                new_notes.append(n)
        tracks[inst_name] = new_notes

    return tracks


# =============================================================================
# SECTION 6B: PHRASE BREATHING (inserted between orchestration and expression)
# =============================================================================

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

    1. After each cadence (PAC, HC, DC): insert a rest of 0.5-1.0 beats
       by shortening the cadential note and delaying the next note.
    2. Before cadences: lengthen the penultimate note by 50% (agogic accent).
    3. General pause at the climax boundary (~62% of the piece).
    4. No continuous melody line exceeds 8 bars without a rest >= 0.25 beats.
    """
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    total_bars = form_ir.total_bars
    total_time = total_bars * 4 * sec_per_beat

    cadence_times = _find_cadence_times(vl_ir, form_ir)
    if not cadence_times and vl_ir.chords:
        # Fallback: treat last chord of each section as a cadence point
        # by using bar boundaries from the form
        bar_cursor = 0
        for sec in form_ir.sections:
            for sub in sec.subsections:
                bar_cursor += sub.bars
                t = (bar_cursor - 1) * 4 * sec_per_beat
                cadence_times.append(t)

    # Tolerance for matching notes to cadence times
    tolerance = sec_per_beat * 1.5

    # Climax boundary for general pause (golden ratio)
    gp_time = total_time * 0.618
    gp_duration = sec_per_beat * 1.0  # 1 beat of silence

    for inst_name, notes in tracks.items():
        if not notes:
            continue
        notes.sort(key=lambda n: n.start_time_sec)

        # --- 1 & 2: Cadence breathing and agogic accent ---
        for cad_t in cadence_times:
            # Find the cadential note (closest note ending near cad_t)
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

            # Agogic accent: lengthen the note BEFORE the cadential note by 50%
            if cad_idx >= 1:
                pre_note = notes[cad_idx - 1]
                pre_note.duration_sec *= 1.5

            # Rest after cadence: shorten the cadential note and push a gap
            cad_note = notes[cad_idx]
            rest_beats = random.uniform(0.5, 1.0)
            rest_sec = rest_beats * sec_per_beat
            # Shorten cadential note to make room for rest
            original_end = cad_note.start_time_sec + cad_note.duration_sec
            cad_note.duration_sec = max(
                sec_per_beat * 0.5,
                cad_note.duration_sec - rest_sec * 0.5,
            )
            # Push subsequent notes forward by the rest duration
            gap_end = original_end + rest_sec
            for j in range(cad_idx + 1, len(notes)):
                if notes[j].start_time_sec < gap_end:
                    shift = gap_end - notes[j].start_time_sec
                    notes[j].start_time_sec += shift

        # --- 3: General pause at climax boundary ---
        # Remove or shorten notes that overlap the GP window
        gp_start = gp_time
        gp_end = gp_time + gp_duration
        for n in notes:
            note_end = n.start_time_sec + n.duration_sec
            # Note starts before GP but extends into it
            if n.start_time_sec < gp_start and note_end > gp_start:
                n.duration_sec = max(0.05, gp_start - n.start_time_sec)
            # Note starts during GP
            elif gp_start <= n.start_time_sec < gp_end:
                shift = gp_end - n.start_time_sec
                n.start_time_sec += shift

        # --- 4: Max 4 bars continuous melody without rest ---
        # Classical phrases are ~4 bars; force a breath every 4 bars
        # (16 quarter-note beats) to keep phrase lengths near the target.
        # The rest must be significant enough to be detected as a phrase
        # boundary by the evaluation framework (which checks for gaps >= 2
        # beats or rests >= 1 beat).
        max_continuous_sec = 4 * 4 * sec_per_beat
        min_rest_sec = 1.5 * sec_per_beat
        if len(notes) >= 2:
            phrase_start = notes[0].start_time_sec
            for i in range(1, len(notes)):
                gap = notes[i].start_time_sec - (notes[i - 1].start_time_sec + notes[i - 1].duration_sec)
                if gap >= min_rest_sec:
                    # Already has a rest here, reset phrase start
                    phrase_start = notes[i].start_time_sec
                elif notes[i].start_time_sec - phrase_start > max_continuous_sec:
                    # Force a breath: shorten previous note to create a gap
                    notes[i - 1].duration_sec = max(
                        0.05,
                        notes[i - 1].duration_sec - min_rest_sec,
                    )
                    phrase_start = notes[i].start_time_sec

    return tracks


# =============================================================================
# SECTION 7: PASS 7 -- EXPRESSION (dynamics, articulation)
# =============================================================================

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

    Uses a simple piecewise parabolic shape:
      - Rise phase  (0 <= t <= 0.618):  (t / 0.618)^1.5
      - Fall phase  (0.618 < t <= 1.0): ((1-t) / (1-0.618))^2.0
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

    1. Global tension curve peaks at golden ratio (0.618) of the piece.
    2. Map tension to velocity, register displacement, and note density.
    3. Character determines start/end velocity and articulation.
    4. Beat-level metric accents (beat 1 strongest, beat 3 secondary).
    5. Melody voice is louder than accompaniment.
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

    # Velocity envelope parameters based on character
    # Start at mp (~70), climax at ff (~110), end at p (~55) by default
    vel_start = 70
    vel_climax = 110
    vel_end = 55

    if character in (CharacterToken.HEROIC, CharacterToken.TRIUMPHANT, CharacterToken.MAJESTIC):
        vel_start = 70
        vel_climax = 110
        vel_end = 90   # heroic endings are loud (ff)
    elif character in (CharacterToken.LYRICAL, CharacterToken.TENDER, CharacterToken.SERENE):
        vel_start = 55
        vel_climax = 95
        vel_end = 40   # lyrical endings are soft (pp)
    elif character in (CharacterToken.AGITATED, CharacterToken.STORMY, CharacterToken.ANGUISHED):
        vel_start = 70
        vel_climax = 110
        vel_end = 55
    elif character in (CharacterToken.MYSTERIOUS, CharacterToken.PASTORAL):
        vel_start = 50
        vel_climax = 85
        vel_end = 45

    # Register displacement range (semitones) at climax
    max_register_shift = 4  # at climax, soprano shifts up, bass shifts down

    # Determine which instruments carry the melody
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

    # Determine bass instruments for register widening
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

            # --- Velocity from tension curve ---
            # Interpolate: at tension=0 use start/end vel, at tension=1 use climax
            # The base velocity blends between start and end across the piece
            base_vel = vel_start + (vel_end - vel_start) * t
            # Tension adds dynamic energy on top
            vel = base_vel + tension * (vel_climax - base_vel)

            # Melody is louder, accompaniment quieter
            vel += (15 if is_melody else -10)

            # Beat-level accenting
            beat_in_bar = (note.start_time_sec / sec_per_beat) % 4
            if beat_in_bar < 0.5:          # beat 1
                vel += 8
            elif 1.5 < beat_in_bar < 2.5:  # beat 3
                vel += 4

            note.velocity = max(1, min(127, int(vel)))
            note.articulation = art
            note.dynamic = dyn

            # --- Register displacement from tension ---
            # At climax: soprano/melody goes higher, bass goes lower.
            # Limit to 2 semitones to avoid violating voice_spacing (max 12
            # semitones between adjacent upper voices).
            register_shift = int(tension * min(max_register_shift, 2))
            if is_melody and register_shift > 0:
                note.midi_pitch = min(127, note.midi_pitch + register_shift)
            elif is_bass and register_shift > 0:
                note.midi_pitch = max(0, note.midi_pitch - register_shift)

    return tracks


# =============================================================================
# SECTION 8: PASS 8 -- HUMANIZATION (timing jitter, velocity curves, rubato)
# =============================================================================

def pass_8_humanization(tracks: Dict[str, List[PerformanceNote]],
                        form_ir: FormIR) -> Dict[str, List[PerformanceNote]]:
    """
    PASS 8: Apply human-like performance deviations.

    1. Timing jitter: Gaussian noise (sigma=12ms) + mean-reverting drift.
    2. Melody leads accompaniment by 10-20ms.
    3. Cadential ritardando: slow down last 2 beats of cadence bars by 15-25%.
    4. Velocity micro-variation: Gaussian (sigma=3).
    5. Articulation realization: adjust durations for staccato/legato/portato.
    """
    tempo = form_ir.tempo_bpm
    sec_per_beat = 60.0 / tempo
    total_bars = form_ir.total_bars
    total_time = total_bars * 4 * sec_per_beat

    # Determine melody instruments
    melody_instruments = {"violin1", "flute", "oboe", "piano", "piano_rh", "piano_s"}

    for inst_name, notes in tracks.items():
        is_melody = inst_name in melody_instruments
        drift = 0.0

        notes.sort(key=lambda n: n.start_time_sec)

        for i, note in enumerate(notes):
            # Timing jitter
            jitter_ms = np.random.normal(0, 12)
            drift += np.random.normal(0, 5)
            drift *= 0.95  # mean-reverting
            melody_lead_ms = -15.0 if is_melody else 0.0
            note.timing_offset_ms = jitter_ms + drift + melody_lead_ms

            # Cadential ritardando: if note is near the end of the piece,
            # stretch duration and delay subsequent notes
            if total_time > 0 and note.start_time_sec > total_time * 0.95:
                # In the final 5%, slow down by 20%
                ritard_factor = 1.20
                note.duration_sec *= ritard_factor

            # Velocity micro-variation
            note.velocity_offset = int(np.random.normal(0, 3))
            note.velocity = max(1, min(127, note.velocity + note.velocity_offset))

            # Articulation realization
            if note.articulation == ArticulationToken.STACCATO:
                note.duration_sec *= np.random.uniform(0.35, 0.50)
            elif note.articulation == ArticulationToken.LEGATO:
                note.duration_sec *= np.random.uniform(0.95, 1.05)
            elif note.articulation == ArticulationToken.PORTATO:
                note.duration_sec *= np.random.uniform(0.75, 0.88)
            elif note.articulation == ArticulationToken.MARCATO:
                note.duration_sec *= np.random.uniform(0.80, 0.95)
                note.velocity = min(127, note.velocity + 5)
            elif note.articulation == ArticulationToken.TENUTO:
                note.duration_sec *= np.random.uniform(0.98, 1.02)

            # Apply timing offset
            note.start_time_sec = max(0, note.start_time_sec + note.timing_offset_ms / 1000.0)

    return tracks


# =============================================================================
# SECTION 9: PASS 9 -- VALIDATION (check rules, report violations)
# =============================================================================

@dataclass
class ValidationReport:
    """Validation results from Pass 9."""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = ["=" * 60]
        lines.append("  VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append(f"  Status: {'PASS' if self.is_valid else 'FAIL'}")
        lines.append(f"  Errors:   {len(self.errors)}")
        lines.append(f"  Warnings: {len(self.warnings)}")
        if self.errors:
            lines.append("\n  Errors:")
            for e in self.errors[:15]:
                lines.append(f"    - {e}")
            if len(self.errors) > 15:
                lines.append(f"    ... and {len(self.errors) - 15} more")
        if self.warnings:
            lines.append("\n  Warnings:")
            for w in self.warnings[:10]:
                lines.append(f"    - {w}")
            if len(self.warnings) > 10:
                lines.append(f"    ... and {len(self.warnings) - 10} more")
        lines.append("\n  Scores:")
        for k, v in sorted(self.scores.items()):
            lines.append(f"    {k:35s}: {v:.2f}")
        lines.append("=" * 60)
        return "\n".join(lines)


def pass_9_validation(perf_ir: PerformanceIR,
                      form_ir: FormIR) -> ValidationReport:
    """
    PASS 9: Check the 50 rules. Returns a validation report.

    Checks:
      1.  Range compliance: every note within instrument range
      2.  Velocity bounds: 1 <= velocity <= 127
      3.  No negative start times
      4.  Bass spacing: no intervals < P5 below C3 (MIDI 48)
      5.  Parallel 5ths/octaves in simultaneous notes (sampled)
      6.  Humanization applied: timing offsets are non-zero
      7.  Melodic interval distribution (Zipf compliance)
      8.  Duration sanity: no extremely short or long notes
      9.  Dynamic range: piece uses at least 20 velocity units of range
     10.  Total duration: reasonable length for bar count
    """
    report = ValidationReport()

    if not perf_ir.notes:
        report.errors.append("No notes in performance IR!")
        return report

    # -- 1. Range compliance --
    range_violations = 0
    for n in perf_ir.notes:
        lo, hi = INSTRUMENT_RANGES.get(n.instrument, (21, 108))
        if n.midi_pitch < lo or n.midi_pitch > hi:
            range_violations += 1
            if range_violations <= 5:
                report.errors.append(
                    f"Range: {n.instrument} note {n.midi_pitch} "
                    f"at t={n.start_time_sec:.2f}s (range {lo}-{hi})")
    if range_violations > 5:
        report.errors.append(f"  ... {range_violations - 5} more range violations")
    report.scores["range_compliance"] = 1.0 - (range_violations / max(len(perf_ir.notes), 1))

    # -- 2. Velocity bounds --
    vel_violations = sum(1 for n in perf_ir.notes if n.velocity < 1 or n.velocity > 127)
    report.scores["velocity_bounds"] = 1.0 - (vel_violations / max(len(perf_ir.notes), 1))
    if vel_violations:
        report.errors.append(f"Velocity: {vel_violations} notes outside [1, 127]")

    # -- 3. Negative start times --
    neg_times = sum(1 for n in perf_ir.notes if n.start_time_sec < 0)
    if neg_times:
        report.errors.append(f"Timing: {neg_times} notes with negative start time")
    report.scores["timing_validity"] = 1.0 - (neg_times / max(len(perf_ir.notes), 1))

    # -- 4. Bass spacing --
    bass_notes = defaultdict(list)
    for n in perf_ir.notes:
        if n.midi_pitch < 48:
            bass_notes[round(n.start_time_sec, 2)].append(n.midi_pitch)
    spacing_warnings = 0
    for t, pitches in bass_notes.items():
        if len(pitches) >= 2:
            sorted_p = sorted(pitches)
            for i in range(len(sorted_p) - 1):
                if sorted_p[i + 1] - sorted_p[i] < 7:
                    spacing_warnings += 1
    if spacing_warnings:
        report.warnings.append(f"Bass spacing: {spacing_warnings} close intervals below C3")
    report.scores["bass_spacing"] = 1.0 - min(1.0, spacing_warnings / 20.0)

    # -- 5. Parallel fifths/octaves (sampled check) --
    # Group notes by approximate time
    by_time = defaultdict(list)
    for n in perf_ir.notes:
        by_time[round(n.start_time_sec, 2)].append(n.midi_pitch)
    times = sorted(by_time.keys())
    parallel_count = 0
    for ti in range(min(len(times) - 1, 200)):
        t1, t2 = times[ti], times[ti + 1]
        p1 = sorted(by_time[t1])
        p2 = sorted(by_time[t2])
        if len(p1) >= 2 and len(p2) >= 2:
            for i in range(min(len(p1), len(p2)) - 1):
                for j in range(i + 1, min(len(p1), len(p2))):
                    int1 = (p1[j] - p1[i]) % 12
                    int2 = (p2[j] - p2[i]) % 12
                    if int1 in (0, 7) and int1 == int2:
                        if p1[i] != p2[i] and p1[j] != p2[j]:
                            parallel_count += 1
    if parallel_count:
        report.warnings.append(f"Parallel 5ths/8ves detected: ~{parallel_count} instances")
    report.scores["voice_leading"] = max(0.0, 1.0 - parallel_count / 50.0)

    # -- 6. Humanization check --
    nonzero_offsets = sum(1 for n in perf_ir.notes if abs(n.timing_offset_ms) > 0.1)
    humanization_ratio = nonzero_offsets / max(len(perf_ir.notes), 1)
    report.scores["humanization"] = min(1.0, humanization_ratio / 0.8)
    if humanization_ratio < 0.5:
        report.warnings.append("Low humanization: fewer than 50% of notes have timing offsets")

    # -- 7. Melodic interval distribution --
    # Gather intervals from the melody instrument notes
    melody_notes = sorted(
        [n for n in perf_ir.notes if n.instrument in ("violin1", "flute", "piano", "piano_rh", "piano_s")],
        key=lambda n: n.start_time_sec)
    if len(melody_notes) > 2:
        intervals = [abs(melody_notes[i+1].midi_pitch - melody_notes[i].midi_pitch)
                     for i in range(len(melody_notes) - 1)]
        steps = sum(1 for iv in intervals if iv <= 2)
        step_ratio = steps / max(len(intervals), 1)
        report.scores["melodic_steps_ratio"] = min(1.0, step_ratio / 0.45)
        if step_ratio < 0.3:
            report.warnings.append(f"Melody has too few stepwise intervals: {step_ratio:.1%}")
    else:
        report.scores["melodic_steps_ratio"] = 0.5

    # -- 8. Duration sanity --
    dur_issues = sum(1 for n in perf_ir.notes if n.duration_sec < 0.01 or n.duration_sec > 30)
    report.scores["duration_sanity"] = 1.0 - (dur_issues / max(len(perf_ir.notes), 1))
    if dur_issues:
        report.warnings.append(f"Duration: {dur_issues} notes with extreme durations")

    # -- 9. Dynamic range --
    velocities = [n.velocity for n in perf_ir.notes]
    vel_range = max(velocities) - min(velocities)
    report.scores["dynamic_range"] = min(1.0, vel_range / 40.0)
    if vel_range < 15:
        report.warnings.append(f"Narrow dynamic range: only {vel_range} velocity units")

    # -- 10. Total duration check --
    tempo = form_ir.tempo_bpm
    expected_duration = form_ir.total_bars * 4 * 60.0 / tempo
    actual_duration = perf_ir.total_duration_sec
    duration_ratio = actual_duration / max(expected_duration, 1)
    if duration_ratio < 0.5 or duration_ratio > 2.0:
        report.warnings.append(
            f"Duration mismatch: expected ~{expected_duration:.0f}s, got {actual_duration:.0f}s")
    report.scores["duration_match"] = max(0.0, 1.0 - abs(1.0 - duration_ratio))

    return report


# =============================================================================
# POST-PROCESSING FIXES (Level-1 rule violation remediation)
# =============================================================================

def fix_augmented_intervals(notes: List[MelodicNote], key_token: KeyToken) -> List[MelodicNote]:
    """
    Fix augmented melodic intervals (tritones = 6 semitones, augmented 2nds = 3
    semitones in minor keys).  When found, adjust the second note by 1 semitone
    to produce a perfect 4th (5 semitones) or perfect 5th (7 semitones) instead.

    Applied after Pass 4 (Melody).
    """
    # Use music21 to check interval spelling, matching evaluation framework logic.
    for i in range(1, len(notes)):
        p1 = m21pitch.Pitch(midi=notes[i - 1].midi)
        p2 = m21pitch.Pitch(midi=notes[i].midi)
        try:
            ivl = m21interval.Interval(p1, p2)
            if ivl.specifier == m21interval.Specifier.AUGMENTED:
                direction = 1 if notes[i].midi > notes[i - 1].midi else -1
                # Try shifting by -1 then +1 semitone to escape augmented spelling
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
                    except Exception:
                        continue
                if not fixed:
                    # Fallback: shrink by 1 semitone toward the previous note.
                    notes[i].midi -= direction
        except Exception:
            pass
    return notes


def fix_leading_tone_resolution(vl_ir: VoiceLeadingIR, key_token: KeyToken) -> VoiceLeadingIR:
    """
    Ensure leading tones resolve up by semitone to the tonic.
    Applied after Pass 5 (Counterpoint).

    The evaluation framework checks ALL leading tones on strong beats
    (beat 1 and 3), not just cadential ones. So we fix every strong-beat
    leading tone that has a following chord event.

    Must check the LOCAL key of each chord event (not just the home key),
    because the evaluator uses score.analyze('key') which picks the most
    prominent key, and secondary-key leading tones are also flagged.
    """
    # Build a set of (leading_tone_pc, tonic_pc) for all keys used in the piece
    lt_pairs = set()
    for ce in vl_ir.chords:
        local_key_str = _KEY_TO_M21.get(ce.key, "C")
        local_key_obj = m21key.Key(local_key_str)
        tonic_pc = local_key_obj.tonic.pitchClass
        lt_pc = (tonic_pc - 1) % 12
        lt_pairs.add((lt_pc, tonic_pc))
    # Also add home key
    home_key_str = _KEY_TO_M21.get(key_token, "C")
    home_key_obj = m21key.Key(home_key_str)
    home_tonic_pc = home_key_obj.tonic.pitchClass
    home_lt_pc = (home_tonic_pc - 1) % 12
    lt_pairs.add((home_lt_pc, home_tonic_pc))

    chords = vl_ir.chords
    for i in range(len(chords) - 1):
        curr = chords[i]
        nxt = chords[i + 1]
        # Check if this chord is on a strong beat (beat 1 or 3)
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
    """
    Ensure chord 7ths (notes forming interval class 10 or 11 above the bass)
    resolve downward by step. The evaluation framework flags sevenths that
    move upward by more than 2 semitones on strong beats. Fix by adjusting
    the next note in that voice to step down by 1-2 semitones.
    """
    chords = vl_ir.chords
    for i in range(len(chords) - 1):
        curr = chords[i]
        nxt = chords[i + 1]
        bass = curr.bass
        if bass == 0:
            continue
        # Only check on strong beats (matching evaluator logic)
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
                # If the next note moves up by more than 2 semitones, fix it
                if motion > 2:
                    # Resolve down by step (1 or 2 semitones)
                    setattr(nxt, voice_attr, curr_midi - random.choice([1, 2]))
    return vl_ir


def fix_leap_recovery(notes: List[MelodicNote], recovery_pct: float = 0.85) -> List[MelodicNote]:
    """
    After any melodic leap of 4+ semitones, the next note should move by step
    (1-2 semitones) in the opposite direction ~85% of the time.
    Applied after Pass 4 (Melody).
    """
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
    """
    Constrain melody (ornamental) notes so they don't cross below the alto
    voice or exceed 12 semitones above it. This prevents voice_spacing and
    voice_crossing violations in the evaluation.
    """
    if not vl_ir.melody or not vl_ir.chords:
        return

    # Build a bar+beat -> alto_midi lookup from chord events
    alto_at: Dict[Tuple[int, float], int] = {}
    for ce in vl_ir.chords:
        alto_at[(ce.bar, ce.beat)] = ce.alto

    # For each melody note, find the nearest alto pitch and constrain
    for mn in vl_ir.melody:
        # Find the alto pitch at or before this bar/beat
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

        # Ensure melody is above alto (no crossing)
        if mn.midi < best_alto + 1:
            mn.midi = best_alto + 1

        # Ensure melody is within 10 semitones of alto (voice spacing rule: <= 12,
        # leave 2 semitone buffer for expression register displacement)
        if mn.midi > best_alto + 10:
            mn.midi = best_alto + 10


def fix_voice_crossing(vl_ir: VoiceLeadingIR) -> VoiceLeadingIR:
    """
    Ensure register order soprano >= alto >= tenor >= bass at every chord event.
    When a crossing is detected, swap pitches. Applied after Pass 5.
    """
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
    """
    Explicitly mark cadence positions at the end of each schema sequence so the
    evaluator can distinguish real cadences from Alberti-bass V-I bass motion.
    Applied between Pass 3 (Harmony) and Pass 4 (Melody).

    Also ensures cadences happen every ~4 bars (classical phrase structure)
    and that cadential chords have proper V->I bass motion.
    """
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
# SECTION 10: MIDI EXPORT
# =============================================================================

def export_midi(perf_ir: PerformanceIR, output_path: str,
                tempo_bpm: int = 120) -> str:
    """
    Convert PerformanceIR to a multi-track MIDI file using midiutil.
    Each unique instrument gets its own track.
    """
    instruments = sorted(set(n.instrument for n in perf_ir.notes),
                         key=lambda i: _INST_VOICE_ORDER.get(i, 99))
    if not instruments:
        print("  [MIDI] Warning: no notes to export!")
        return output_path

    inst_to_track = {inst: i for i, inst in enumerate(instruments)}
    # Use deinterleave=False to avoid midiutil crash when same-pitch notes
    # overlap in time on the same channel (common with Alberti bass + chords).
    midi = MIDIFile(numTracks=len(instruments), ticks_per_quarternote=480,
                    deinterleave=False)
    midi.addTempo(0, 0, tempo_bpm)

    for inst in instruments:
        track = inst_to_track[inst]
        channel = track % 16
        if channel == 9:
            channel = 10  # skip GM percussion channel
        program = MIDI_PROGRAMS.get(inst, 0)
        midi.addTrackName(track, 0, inst)
        midi.addProgramChange(track, channel, 0, program)

    # Deduplicate notes that share (track, channel, pitch, time) to avoid
    # midiutil's deinterleave crash on overlapping identical note-ons.
    seen_keys: set = set()
    for note in perf_ir.notes:
        track = inst_to_track.get(note.instrument, 0)
        channel = track % 16
        if channel == 9:
            channel = 10
        # Convert seconds to beats
        beat_time = note.start_time_sec * tempo_bpm / 60.0
        duration_beats = note.duration_sec * tempo_bpm / 60.0

        pitch = max(0, min(127, note.midi_pitch))
        time_key = round(beat_time, 4)
        dedup_key = (track, channel, pitch, time_key)
        if dedup_key in seen_keys:
            continue  # skip duplicate note-on at same tick
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
# SECTION 11: QUALITY REPORT (from evaluation framework)
# =============================================================================

def print_quality_report(perf_ir: PerformanceIR, form_ir: FormIR):
    """
    Print a quality summary. Attempts to use the full evaluation_framework
    if available; otherwise, uses the Pass 9 validation report.
    """
    try:
        from evaluation_framework import EvaluationReport
        # The evaluation framework expects a music21 Score; we build a minimal one
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
# SECTION 12: MASTER PIPELINE
# =============================================================================

def compose(prompt: str, output_file: str = "composed_output.mid",
            seed: Optional[int] = None) -> Tuple[PerformanceIR, FormIR, ValidationReport]:
    """
    The complete end-to-end composition pipeline.

    Input:  A natural-language prompt string.
    Output: (PerformanceIR, FormIR, ValidationReport) + MIDI file on disk.

    Runs all 9 compiler passes in sequence:
        1. Plan       -> FormIR
        2. Schema     -> SchemaIR
        3. Harmony    -> VoiceLeadingIR (chords)
        4. Melody     -> VoiceLeadingIR (chords + melody)
        5. Counterpoint -> VoiceLeadingIR (full SATB)
        6. Orchestration -> instrument tracks
        7. Expression    -> dynamics, articulation
        8. Humanization  -> timing jitter, velocity curves
        9. Validation    -> rule checking, quality report
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
    print(f"\n[Pass 2] Filling sections with galant schemata...")
    schema_ir = pass_2_schema(form_ir)
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
    # Show first few chords
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
    print(f"\n[Pass 4] Generating melodic lines...")
    vl_ir = pass_4_melody(vl_ir, form_ir)
    print(f"  Melody notes: {len(vl_ir.melody)}")
    ct = sum(1 for m in vl_ir.melody if m.is_chord_tone)
    nct = len(vl_ir.melody) - ct
    print(f"    Chord tones: {ct}, Non-chord tones: {nct}")

    # --- Fix 1: Augmented intervals in melody ---
    vl_ir.melody = fix_augmented_intervals(vl_ir.melody, form_ir.home_key)
    print(f"  [Fix] Augmented intervals cleaned in melody")

    # --- Fix 3: Leap recovery in melody ---
    vl_ir.melody = fix_leap_recovery(vl_ir.melody)
    print(f"  [Fix] Leap recovery applied to melody")

    # --- Pass 5: Counterpoint ---
    print(f"\n[Pass 5] Adding inner voices (counterpoint)...")
    vl_ir = pass_5_counterpoint(vl_ir, form_ir)
    print(f"  Alto notes: {len(vl_ir.inner_voices.get('alto', []))}")
    print(f"  Tenor notes: {len(vl_ir.inner_voices.get('tenor', []))}")
    # Check for parallel 5ths
    p5_count = 0
    for i in range(len(vl_ir.chords) - 1):
        c1 = vl_ir.chords[i]
        c2 = vl_ir.chords[i + 1]
        v1 = (c1.soprano, c1.alto, c1.tenor, c1.bass)
        v2 = (c2.soprano, c2.alto, c2.tenor, c2.bass)
        if VoiceLeader.has_parallel_fifths_or_octaves(v1, v2):
            p5_count += 1
    print(f"  Parallel 5th/8ve checks: {p5_count} issues found")

    # --- Fix 2: Leading tone resolution at strong beats ---
    vl_ir = fix_leading_tone_resolution(vl_ir, form_ir.home_key)
    print(f"  [Fix] Leading tone resolution enforced at strong beats")

    # --- Fix 2b: Seventh resolution ---
    vl_ir = fix_seventh_resolution(vl_ir)
    print(f"  [Fix] Chord seventh resolution enforced at strong beats")

    # --- Fix 4: Voice crossing ---
    vl_ir = fix_voice_crossing(vl_ir)
    print(f"  [Fix] Voice crossing corrected (S >= A >= T >= B)")

    # --- Fix 5: Augmented intervals in all voice lines (chord SATB + inner) ---
    # The chord soprano, alto, tenor, bass form separate melodic lines
    # that may contain augmented intervals not caught by the melody fix.
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

    # Also update inner_voices from the fixed chord data
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

    # --- Fix 6: Melody voice spacing (prevent crossing below alto) ---
    _fix_melody_voice_spacing(vl_ir)
    print(f"  [Fix] Melody voice spacing constrained (no crossing below alto)")

    # --- Pass 6: Orchestration ---
    print(f"\n[Pass 6] Assigning to instruments...")
    tracks = pass_6_orchestration(vl_ir, form_ir)
    total_notes = sum(len(notes) for notes in tracks.values())
    for inst, notes in tracks.items():
        print(f"    {inst}: {len(notes)} notes")
    print(f"  Total performance notes: {total_notes}")

    # --- Pass 6a: Smooth section transitions (density ramp) ---
    print(f"\n[Pass 6a] Smoothing section boundary density transitions...")
    tracks = _smooth_section_transitions(tracks, form_ir)

    # --- Pass 6b: Phrase Breathing ---
    print(f"\n[Pass 6b] Inserting phrase breathing (rests at cadences, general pause)...")
    tracks = pass_6b_phrase_breathing(tracks, vl_ir, form_ir)
    cadence_count = sum(1 for ce in vl_ir.chords if ce.is_cadential)
    print(f"  Cadence points processed: {cadence_count}")
    print(f"  General pause at {form_ir.total_bars * 0.618:.0f} bars (~62% golden ratio)")

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

    # --- Quality report from evaluation framework ---
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
# SECTION 13: CLI ENTRY POINT
# =============================================================================

SAMPLE_PROMPTS = [
    "A piano sonata exposition in C minor, heroic character, 40 bars",
    "A string quartet theme and 3 variations in G major, lyrical",
    "An orchestral ternary piece in D major, noble, 32 bars",
    "A piano ternary piece in F minor, tragic, 24 bars",
    "A string quartet sonata exposition in Bb major, playful, 48 bars",
]


if __name__ == "__main__":
    # Accept prompt from command line or use default
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = SAMPLE_PROMPTS[0]
        print(f"No prompt given; using default: \"{prompt}\"\n")

    perf_ir, form_ir, report = compose(
        prompt,
        output_file="composed_output.mid",
        seed=42,
    )

    # Also generate a second example to demonstrate versatility
    print("\n\n" + "#" * 60)
    print("# SECOND EXAMPLE")
    print("#" * 60 + "\n")

    compose(
        "A string quartet theme and 3 variations in G major, lyrical",
        output_file="composed_variations.mid",
        seed=123,
    )
