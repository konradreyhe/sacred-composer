"""
SECTION 0: TEXT PROMPT PARSER
==============================
parse_prompt() + validation, key utilities, instrument data, and shared constants.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from music21 import key as m21key

from SYSTEM_ARCHITECTURE import (
    FormType, SubsectionType, KeyToken, CharacterToken,
)
from composer._rng import rng


# ============================================================================
# Mapping tables
# ============================================================================

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

# Voice ordering from highest to lowest register
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


# ============================================================================
# Key utility functions
# ============================================================================

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


def _subdominant_key(kt: KeyToken) -> KeyToken:
    """Get the subdominant key (IV) -- same mode as home key."""
    m21_str = _KEY_TO_M21[kt]
    k = m21key.Key(m21_str)
    sub_pitch = k.pitchFromDegree(4)
    is_minor = _key_is_minor(kt)
    for name, token in _KEY_MAP.items():
        m21_candidate = _KEY_TO_M21[token]
        cand_key = m21key.Key(m21_candidate)
        if (cand_key.tonic.pitchClass == sub_pitch.pitchClass
                and ("minor" in token.value) == is_minor):
            return token
    return KeyToken.F_MAJOR  # fallback


def _submediant_key(kt: KeyToken) -> KeyToken:
    """Get the submediant key (vi in major, VI in minor)."""
    m21_str = _KEY_TO_M21[kt]
    k = m21key.Key(m21_str)
    sub_pitch = k.pitchFromDegree(6)
    # In major -> minor submediant; in minor -> major submediant
    target_minor = not _key_is_minor(kt)
    for name, token in _KEY_MAP.items():
        m21_candidate = _KEY_TO_M21[token]
        cand_key = m21key.Key(m21_candidate)
        if (cand_key.tonic.pitchClass == sub_pitch.pitchClass
                and ("minor" in token.value) == target_minor):
            return token
    # Fallback: try any mode
    for name, token in _KEY_MAP.items():
        m21_candidate = _KEY_TO_M21[token]
        cand_key = m21key.Key(m21_candidate)
        if cand_key.tonic.pitchClass == sub_pitch.pitchClass:
            return token
    return KeyToken.A_MINOR  # fallback


def _snap_to_scale(midi_val: int, scale_pitches: List[int]) -> int:
    """Snap a MIDI pitch to the nearest pitch in *scale_pitches*."""
    if not scale_pitches:
        return midi_val
    return min(scale_pitches, key=lambda p: abs(p - midi_val))


# ============================================================================
# Motivic development engine
# ============================================================================

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
        SubsectionType.SUBJECT_ENTRY: ["literal", "transposition"],
        SubsectionType.ANSWER_ENTRY: ["transposition"],
        SubsectionType.COUNTERSUBJECT: ["inversion", "transposition"],
        SubsectionType.PEDAL_POINT: ["augmentation", "fragmentation"],
    }

    @staticmethod
    def generate_seed(key_str: str) -> SeedMotif:
        """
        Generate a 4-8 note seed motif built from scale-step intervals.

        The motif is constrained to mostly stepwise motion (seconds) with
        one or two leaps (thirds) for interest -- imitating classical practice.
        """
        r = rng()
        length = r.randint(4, 8)  # number of notes
        # Build intervals: mostly steps (1-2 semitones), occasional thirds (3-4)
        # Directional momentum: prefer continuing in same direction for 2-3 notes
        intervals: List[int] = []
        step_up = [1, 2]
        step_down = [-2, -1]
        leap_up = [3, 4]
        leap_down = [-4, -3]
        prev_dir = r.choice([-1, 1])  # initial direction
        run_len = 0
        for i in range(length - 1):
            # Continue in same direction for 2-3 notes, then maybe flip
            if run_len >= r.randint(2, 3):
                prev_dir = -prev_dir
                run_len = 0
            run_len += 1
            if r.random() < 0.25:
                pool = leap_up if prev_dir > 0 else leap_down
            else:
                pool = step_up if prev_dir > 0 else step_down
            intervals.append(r.choice(pool))

        # Rhythm: mix of quarter and eighth notes, one possible half note
        rhythm_pool = [0.5, 1.0, 1.0, 1.0, 2.0]
        rhythm = [r.choice(rhythm_pool) for _ in range(length)]

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
            frag_len = min(rng().randint(2, 3), len(ivls))
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
                      ) -> List['MelodicNote']:
        """
        Convert a SeedMotif into concrete MelodicNote objects starting
        from the given MIDI pitch, bar, and beat.
        """
        from SYSTEM_ARCHITECTURE import MelodicNote

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
        return rng().choice(candidates)


# ============================================================================
# Module-level state
# ============================================================================

# Module-level storage for the seed motif (avoids modifying FormIR dataclass)
_current_seed_motif: Optional[SeedMotif] = None

# Rondo refrain cache: stores the melody + harmony of the first A section
# so subsequent A sections can be replayed identically.
_rondo_refrain_melody: Optional[list] = None
_rondo_refrain_chords: Optional[list] = None

# Module-level fugue state
_current_fugue: Optional[object] = None


# ============================================================================
# parse_prompt
# ============================================================================

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
    if "fugue" in text_lower or "fugal" in text_lower:
        form = FormType.FUGUE
    elif "sonata" in text_lower or "exposition" in text_lower:
        form = FormType.SONATA
    elif "rondo" in text_lower or "abaca" in text_lower:
        form = FormType.RONDO
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

    # --- Detect fugue voice count ---
    fugue_voices = 3
    voice_match = re.search(r"(\d+)\s*voice", text_lower)
    if voice_match:
        fugue_voices = max(2, min(4, int(voice_match.group(1))))

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

    # Fugue default: moderate tempo (Bach-style), default 24-32 bars
    if form == FormType.FUGUE:
        if not bar_match:
            total_bars = rng().choice([24, 28, 32])
        if "bach" in text_lower:
            tempo_bpm = 76

    # Rondo default: at least 32 bars (ABACA needs space)
    if form == FormType.RONDO:
        if not bar_match:
            total_bars = rng().choice([32, 40, 48])
        # Rondo is typically lively unless otherwise specified
        if "lively" in text_lower or "spirited" in text_lower:
            tempo_bpm = max(tempo_bpm, 120)

    return {
        "form": form,
        "home_key": home_key,
        "character": character,
        "total_bars": total_bars,
        "instrumentation": instrumentation,
        "tempo_bpm": tempo_bpm,
        "num_variations": num_variations,
        "fugue_voices": fugue_voices,
        "title": text.strip(),
    }


# Sample prompts for CLI
SAMPLE_PROMPTS = [
    "A piano sonata exposition in C minor, heroic character, 40 bars",
    "A string quartet theme and 3 variations in G major, lyrical",
    "An orchestral ternary piece in D major, noble, 32 bars",
    "A piano ternary piece in F minor, tragic, 24 bars",
    "A string quartet sonata exposition in Bb major, playful, 48 bars",
    "A Bach-style fugue in C minor, 24 bars, for piano",
    "A lively rondo in A major, 40 bars, for piano",
    "A Bach-style fugue in D minor, 28 bars, for piano",
]
