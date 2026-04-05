"""
CLASSICAL MUSIC COMPOSITION SYSTEM — CONCRETE SYSTEM ARCHITECTURE
=================================================================

This module defines the complete architecture for an AI classical music
composition system: the Intermediate Representation (IR), token vocabulary,
compiler passes, and schema realizer. Every class and function here is
designed to be directly implementable.

Grounded in the 32-part knowledge base: counterpoint rules (Part 3),
form templates (Part 4), orchestration ranges (Part 5), emotion engine
(Part 6), neuroscience parameters (Part 10), galant schemata, advanced
harmony (Part 17), and humanization (Part 18).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Set, Union
import json


# =============================================================================
# SECTION 1: TOKEN VOCABULARY — Complete Enumerated Types
# =============================================================================

# --- Form Tokens ---
class FormType(Enum):
    SONATA = "sonata"
    RONDO = "rondo"
    TERNARY = "ternary"          # ABA
    BINARY = "binary"            # AB
    THEME_AND_VARIATIONS = "theme_and_variations"
    FUGUE = "fugue"
    MINUET_AND_TRIO = "minuet_and_trio"
    THROUGH_COMPOSED = "through_composed"

class SectionType(Enum):
    # Sonata
    EXPOSITION = "exposition"
    DEVELOPMENT = "development"
    RECAPITULATION = "recapitulation"
    CODA = "coda"
    INTRODUCTION = "introduction"
    # Rondo / Ternary
    A_SECTION = "A_section"
    B_SECTION = "B_section"
    C_SECTION = "C_section"
    # Fugue
    FUGUE_EXPOSITION = "fugue_exposition"
    EPISODE = "episode"
    MIDDLE_ENTRY = "middle_entry"
    STRETTO = "stretto"
    # Generic
    TRANSITION = "transition"
    CLOSING = "closing"

class SubsectionType(Enum):
    P_THEME = "P_theme"           # Primary theme (sonata)
    S_THEME = "S_theme"           # Secondary theme (sonata)
    CLOSING_THEME = "closing_theme"
    TR = "transition"
    CORE = "core"                 # Development core
    RETRANSITION = "retransition"
    STANDING_ON_DOMINANT = "standing_on_dominant"
    # Fugue subsections
    SUBJECT_ENTRY = "subject_entry"
    ANSWER_ENTRY = "answer_entry"
    COUNTERSUBJECT = "countersubject"
    PEDAL_POINT = "pedal_point"


# --- Galant Schema Tokens (Gjerdingen, Music in the Galant Style) ---
class SchemaToken(Enum):
    # Melodic-bass schemata
    DO_RE_MI = "do_re_mi"         # 1-2-3 over 1-7-1
    PRINNER = "prinner"           # 6-5-4-3 over 4-3-2-1 (riposte)
    MONTE = "monte"               # Rising sequence: step up, step up
    FONTE = "fonte"               # Falling sequence: step down, step down
    PONTE = "ponte"               # Pedal bridge on 5
    ROMANESCA = "romanesca"       # 3-2-1-7 over 1-5-6-3 (descending)
    QUIESCENZA = "quiescenza"     # Pedal 1 with upper neighbor motion
    SOL_FA_MI = "sol_fa_mi"       # 5-4-sharp4-5 over 1-x-sharp4-5 (half cad)
    INDUGIO = "indugio"           # Lingering on V
    FENAROLI = "fenaroli"         # 4-3-7-1 over 1-2-3-1
    COMMA = "comma"               # Brief V-I at end of schema chain
    CUDWORTH = "cudworth"         # Opening gambit: 1-1-7-1 over 1-2-7-1
    JUPITER = "jupiter"           # 1-2-3-4 rising (Mozart Jupiter finale)
    MEYER = "meyer"               # 1-7-4-3 over 1-2-7-1
    PASTORELLA = "pastorella"     # 1-7-1-1 over 5-5-3-1 (drone-based)
    PASSO_INDIETRO = "passo_indietro"  # Step back: V back to I


# --- Cadence Tokens ---
class CadenceType(Enum):
    PAC = "PAC"                   # Perfect Authentic: V->I, soprano on 1
    IAC = "IAC"                   # Imperfect Authentic: V->I, soprano NOT on 1
    HC = "HC"                     # Half Cadence: ?->V
    DC = "DC"                     # Deceptive: V->vi
    PLAGAL = "plagal"             # IV->I
    PHRYGIAN_HC = "phrygian_HC"  # iv6->V (minor mode)
    EVADED = "evaded"             # V-> vi/IV6 (interrupted)
    ABANDONED = "abandoned"       # Cadential approach dissolves


# --- Key Tokens (all 24 major/minor keys) ---
class KeyToken(Enum):
    C_MAJOR = "C_major";   C_MINOR = "C_minor"
    Db_MAJOR = "Db_major"; Cs_MINOR = "Cs_minor"
    D_MAJOR = "D_major";   D_MINOR = "D_minor"
    Eb_MAJOR = "Eb_major"; Eb_MINOR = "Eb_minor"
    E_MAJOR = "E_major";   E_MINOR = "E_minor"
    F_MAJOR = "F_major";   F_MINOR = "F_minor"
    Fs_MAJOR = "Fs_major"; Fs_MINOR = "Fs_minor"
    G_MAJOR = "G_major";   G_MINOR = "G_minor"
    Ab_MAJOR = "Ab_major"; Gs_MINOR = "Gs_minor"
    A_MAJOR = "A_major";   A_MINOR = "A_minor"
    Bb_MAJOR = "Bb_major"; Bb_MINOR = "Bb_minor"
    B_MAJOR = "B_major";   B_MINOR = "B_minor"


# --- Key Relationship Tokens ---
class KeyRelationship(Enum):
    TO_DOMINANT = "to_dominant"                 # C -> G
    TO_SUBDOMINANT = "to_subdominant"           # C -> F
    TO_RELATIVE_MAJOR = "to_relative_major"     # C minor -> Eb major
    TO_RELATIVE_MINOR = "to_relative_minor"     # C major -> A minor
    TO_PARALLEL_MAJOR = "to_parallel_major"     # C minor -> C major
    TO_PARALLEL_MINOR = "to_parallel_minor"     # C major -> C minor
    TO_MEDIANT = "to_mediant"                   # C -> E (chromatic mediant)
    TO_FLAT_MEDIANT = "to_flat_mediant"         # C -> Ab
    TO_FLAT_SUBMEDIANT = "to_flat_submediant"   # C -> Ab major
    TO_SUPERTONIC = "to_supertonic"             # C -> D
    TO_NEAPOLITAN = "to_neapolitan"             # C -> Db
    TO_TRITONE = "to_tritone"                   # C -> F#/Gb
    ENHARMONIC_PIVOT = "enharmonic_pivot"       # dim7 or Ger+6 respelling


# --- Texture Tokens ---
class TextureToken(Enum):
    MELODY_ACCOMP = "melody_accomp"        # Melody + accompaniment (Alberti, etc.)
    HOMOPHONIC = "homophonic"              # All voices same rhythm
    POLYPHONIC = "polyphonic"              # Independent voices (fugal)
    UNISON = "unison"                      # All voices on same line
    ANTIPHONAL = "antiphonal"              # Call and response between groups
    HOMORHYTHMIC = "homorhythmic"          # Same rhythm, different pitches
    CHORALE = "chorale"                    # SATB block chords
    TREMOLO = "tremolo"
    OSTINATO = "ostinato"
    ALBERTI_BASS = "alberti_bass"
    MURKY_BASS = "murky_bass"
    ARPEGGIO = "arpeggio"


# --- Character / Affect Tokens ---
class CharacterToken(Enum):
    HEROIC = "heroic"
    LYRICAL = "lyrical"
    MYSTERIOUS = "mysterious"
    AGITATED = "agitated"
    SERENE = "serene"
    TRIUMPHANT = "triumphant"
    TRAGIC = "tragic"
    PASTORAL = "pastoral"
    STORMY = "stormy"
    NOBLE = "noble"
    PLAYFUL = "playful"
    TENDER = "tender"
    ANGUISHED = "anguished"
    MAJESTIC = "majestic"


# --- Dynamic Tokens ---
class DynamicToken(Enum):
    PPP = "ppp"
    PP = "pp"
    P = "p"
    MP = "mp"
    MF = "mf"
    F = "f"
    FF = "ff"
    FFF = "fff"
    CRESCENDO = "crescendo"
    DIMINUENDO = "diminuendo"
    SUBITO_P = "subito_p"
    SUBITO_F = "subito_f"
    SFZ = "sfz"
    FP = "fp"


# --- Articulation Tokens ---
class ArticulationToken(Enum):
    LEGATO = "legato"
    STACCATO = "staccato"
    STACCATISSIMO = "staccatissimo"
    MARCATO = "marcato"
    TENUTO = "tenuto"
    PORTATO = "portato"
    ACCENT = "accent"
    TRILL = "trill"
    MORDENT = "mordent"
    TURN = "turn"
    APPOGGIATURA = "appoggiatura"
    ACCIACCATURA = "acciaccatura"


# =============================================================================
# SECTION 2: INTERMEDIATE REPRESENTATION — Four-Level IR
# =============================================================================

# ---------- Level 1: FORM ----------

@dataclass
class SubsectionIR:
    """One subsection within a formal section (e.g., P-theme within Exposition)."""
    type: SubsectionType
    key: KeyToken
    bars: int
    character: CharacterToken
    texture: TextureToken = TextureToken.MELODY_ACCOMP
    tempo_bpm: Optional[int] = None
    time_signature: str = "4/4"
    cadence_at_end: Optional[CadenceType] = None
    notes: str = ""  # Free-text annotation from the Plan Pass

@dataclass
class SectionIR:
    """One major formal section (e.g., Exposition, Development)."""
    type: SectionType
    subsections: List[SubsectionIR] = field(default_factory=list)
    key: Optional[KeyToken] = None          # home key of section
    key_path: List[KeyToken] = field(default_factory=list)  # keys traversed

@dataclass
class FormIR:
    """Level 1: Top-level form. Output of the Plan Pass."""
    form: FormType
    home_key: KeyToken
    tempo_bpm: int
    time_signature: str
    sections: List[SectionIR] = field(default_factory=list)
    total_bars: int = 0
    title: str = ""
    character: CharacterToken = CharacterToken.HEROIC
    instrumentation: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to JSON for inspection and debugging."""
        import dataclasses
        def _convert(obj):
            if isinstance(obj, Enum):
                return obj.value
            if dataclasses.is_dataclass(obj):
                return {k: _convert(v) for k, v in dataclasses.asdict(obj).items()}
            if isinstance(obj, list):
                return [_convert(i) for i in obj]
            return obj
        return json.dumps(_convert(self), indent=2)


# ---------- Level 2: SCHEMA SEQUENCE ----------

@dataclass
class SchemaSlot:
    """One schema or cadence event within a subsection."""
    schema: Union[SchemaToken, CadenceType]
    bars: int                             # how many bars this schema spans
    local_key: KeyToken                   # the key in which this schema operates
    modulates_to: Optional[KeyToken] = None  # if this schema modulates
    variant: str = "standard"             # e.g., "chromaticized", "minor_mode"

@dataclass
class SubsectionSchemaIR:
    """Level 2 overlay: a subsection filled with schema slots."""
    subsection_ref: SubsectionIR          # pointer to Level 1 subsection
    schema_sequence: List[SchemaSlot] = field(default_factory=list)

@dataclass
class SchemaIR:
    """Level 2: The entire piece as a sequence of schemata."""
    form_ref: FormIR
    schema_plan: List[SubsectionSchemaIR] = field(default_factory=list)


# ---------- Level 3: VOICE LEADING ----------

@dataclass
class ChordEvent:
    """One chord at a specific metric position."""
    bar: int
    beat: float                           # 1.0, 1.5, 2.0, etc.
    roman_numeral: str                    # e.g., "V7", "It+6", "bVI"
    key: KeyToken
    soprano: int                          # MIDI note numbers
    alto: int
    tenor: int
    bass: int
    duration_beats: float = 1.0
    inversion: int = 0                    # 0=root, 1=first, 2=second, 3=third
    is_cadential: bool = False
    source_schema: Optional[SchemaToken] = None

@dataclass
class MelodicNote:
    """One note in a melodic line."""
    midi: int
    bar: int
    beat: float
    duration_beats: float
    is_chord_tone: bool = True
    ornament_type: Optional[str] = None   # "passing", "neighbor", "appoggiatura", etc.

@dataclass
class VoiceLeadingIR:
    """Level 3: All chord events and melodic notes."""
    chords: List[ChordEvent] = field(default_factory=list)
    melody: List[MelodicNote] = field(default_factory=list)
    bass_line: List[MelodicNote] = field(default_factory=list)
    inner_voices: Dict[str, List[MelodicNote]] = field(default_factory=dict)


# ---------- Level 4: PERFORMANCE ----------

@dataclass
class PerformanceNote:
    """A single note with full performance data, ready for MIDI output."""
    midi_pitch: int
    start_time_sec: float                 # absolute time in seconds
    duration_sec: float
    velocity: int                         # 1-127
    channel: int = 0
    instrument: str = "piano"
    # Humanization offsets (applied during Humanization Pass)
    timing_offset_ms: float = 0.0
    velocity_offset: int = 0
    # Expression
    articulation: ArticulationToken = ArticulationToken.LEGATO
    dynamic: DynamicToken = DynamicToken.MF
    # Pedaling (piano only)
    pedal_on: bool = False
    pedal_off_time_sec: Optional[float] = None

@dataclass
class PerformanceIR:
    """Level 4: Complete performance-ready representation."""
    notes: List[PerformanceNote] = field(default_factory=list)
    tempo_map: List[Tuple[float, float]] = field(default_factory=list)  # (time_sec, bpm)
    cc_events: List[Tuple[float, int, int, int]] = field(default_factory=list)  # (time, ch, cc#, val)
    total_duration_sec: float = 0.0


# =============================================================================
# SECTION 3: SCHEMA REALIZER — Concrete Realizations
# =============================================================================

@dataclass
class SchemaRealization:
    """The concrete pitch realization of one galant schema in a given key."""
    soprano_degrees: List[int]    # scale degrees (1-7)
    bass_degrees: List[int]       # scale degrees (1-7)
    harmony: List[str]            # Roman numerals
    bars: int                     # typical bar count

# The master dictionary: every schema token -> its realization template.
# Scale degrees use 1-7. Chromatic alterations use sharps: #4, b6, b7, etc.
# Negative degrees mean descending from previous (for contour guidance).

SCHEMA_REALIZATIONS: Dict[SchemaToken, SchemaRealization] = {

    SchemaToken.DO_RE_MI: SchemaRealization(
        soprano_degrees=[1, 2, 3],
        bass_degrees=[1, 7, 1],
        harmony=["I", "V6", "I"],
        bars=2,
    ),

    SchemaToken.PRINNER: SchemaRealization(
        soprano_degrees=[6, 5, 4, 3],
        bass_degrees=[4, 3, 2, 1],
        harmony=["IV", "I6", "viio6", "I"],
        bars=4,
    ),

    SchemaToken.MONTE: SchemaRealization(
        # Rising sequence: ii-V in the key, then iii-VI one step up
        soprano_degrees=[1, 7, 2, 1],   # first half-step-up pair
        bass_degrees=[4, 5, 5, 6],
        harmony=["ii", "V", "iii", "vi"],
        bars=4,
    ),

    SchemaToken.FONTE: SchemaRealization(
        # Falling sequence: starts a step above tonic, descends
        soprano_degrees=[6, 5, 5, 4],
        bass_degrees=[4, 3, 3, 2],
        harmony=["ii", "V/V", "I6", "V"],
        bars=4,
    ),

    SchemaToken.PONTE: SchemaRealization(
        # Pedal bridge on dominant
        soprano_degrees=[2, 2, 2, 2],
        bass_degrees=[5, 5, 5, 5],
        harmony=["V", "V", "V", "V"],
        bars=4,
    ),

    SchemaToken.ROMANESCA: SchemaRealization(
        soprano_degrees=[3, 2, 1, 7],
        bass_degrees=[1, 5, 6, 3],
        harmony=["I", "V", "vi", "iii"],
        bars=4,
    ),

    SchemaToken.QUIESCENZA: SchemaRealization(
        soprano_degrees=[1, 2, 7, 1],
        bass_degrees=[1, 1, 1, 1],     # tonic pedal
        harmony=["I", "IV64", "V7", "I"],
        bars=4,
    ),

    SchemaToken.SOL_FA_MI: SchemaRealization(
        soprano_degrees=[5, 4, 4, 5],   # 4 becomes #4 in realization
        bass_degrees=[1, 1, 7, 1],
        harmony=["I", "IV", "V/V", "V"],
        bars=2,
    ),

    SchemaToken.INDUGIO: SchemaRealization(
        soprano_degrees=[2, 4, 2, 2],
        bass_degrees=[5, 5, 5, 5],
        harmony=["V", "V42", "V65", "V"],
        bars=4,
    ),

    SchemaToken.FENAROLI: SchemaRealization(
        soprano_degrees=[4, 3, 7, 1],
        bass_degrees=[1, 2, 3, 1],
        harmony=["I", "V6", "I6", "I"],
        bars=4,
    ),

    SchemaToken.COMMA: SchemaRealization(
        soprano_degrees=[7, 1],
        bass_degrees=[5, 1],
        harmony=["V", "I"],
        bars=1,
    ),

    SchemaToken.CUDWORTH: SchemaRealization(
        soprano_degrees=[1, 1, 7, 1],
        bass_degrees=[1, 2, 7, 1],
        harmony=["I", "V6", "V", "I"],
        bars=2,
    ),

    SchemaToken.JUPITER: SchemaRealization(
        soprano_degrees=[1, 2, 3, 4],
        bass_degrees=[1, 7, 1, 2],
        harmony=["I", "V6", "I", "ii6"],
        bars=4,
    ),

    SchemaToken.MEYER: SchemaRealization(
        soprano_degrees=[1, 7, 4, 3],
        bass_degrees=[1, 2, 7, 1],
        harmony=["I", "V6", "viio6", "I"],
        bars=4,
    ),

    SchemaToken.PASTORELLA: SchemaRealization(
        soprano_degrees=[1, 7, 1, 1],
        bass_degrees=[5, 5, 3, 1],
        harmony=["I64", "V", "I6", "I"],
        bars=2,
    ),

    SchemaToken.PASSO_INDIETRO: SchemaRealization(
        soprano_degrees=[2, 1],
        bass_degrees=[5, 1],
        harmony=["V", "I"],
        bars=1,
    ),
}


def realize_schema_in_key(
    schema: SchemaToken,
    key_name: str,
    octave: int = 4,
) -> Dict[str, List[int]]:
    """
    Convert a schema token to concrete MIDI note numbers in a given key.

    Parameters:
        schema: Which galant schema to realize.
        key_name: music21-compatible key string, e.g., "C", "c" (minor), "Eb", "f#".
        octave: Base octave for soprano (bass is one octave below).

    Returns:
        Dict with keys "soprano", "bass", "harmony" (Roman numeral strings),
        each a list with one entry per event.

    Example:
        >>> realize_schema_in_key(SchemaToken.PRINNER, "C", octave=5)
        {'soprano': [76, 74, 72, 71], 'bass': [53, 52, 50, 48],
         'harmony': ['IV', 'I6', 'viio6', 'I']}
    """
    from music21 import key as m21key, scale as m21scale

    template = SCHEMA_REALIZATIONS[schema]
    key_obj = m21key.Key(key_name)
    sc = key_obj.getScale()

    # Map scale degree (1-indexed) to pitch class
    scale_pitches = sc.getPitches(f"C1", f"C8")
    degree_to_midi = {}
    for deg in range(1, 8):
        p = sc.pitchFromDegree(deg)
        degree_to_midi[deg] = p.pitchClass  # 0-11

    soprano_midi = []
    for deg in template.soprano_degrees:
        pc = degree_to_midi[deg]
        midi = octave * 12 + pc
        # Ensure we stay near the target octave
        if midi < (octave * 12 - 6):
            midi += 12
        soprano_midi.append(midi)

    bass_octave = octave - 1
    bass_midi = []
    for deg in template.bass_degrees:
        pc = degree_to_midi[deg]
        midi = bass_octave * 12 + pc
        if midi < (bass_octave * 12 - 6):
            midi += 12
        bass_midi.append(midi)

    return {
        "soprano": soprano_midi,
        "bass": bass_midi,
        "harmony": list(template.harmony),
    }


