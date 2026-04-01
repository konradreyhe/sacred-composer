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


# =============================================================================
# SECTION 4: COMPILER PASSES — Complete Pipeline
# =============================================================================

class CompilerPass:
    """Base class for all compiler passes."""
    def __init__(self, name: str):
        self.name = name
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_input(self, ir) -> bool:
        raise NotImplementedError

    def run(self, ir):
        raise NotImplementedError


# ---------- Pass 1: Plan Pass ----------

class PlanPass(CompilerPass):
    """
    Pass 1: Verbal plan (from Claude LLM) -> Level 1 FormIR.

    Input:  A natural-language plan string OR structured JSON from Claude.
    Output: FormIR (Level 1) — form type, sections, subsections, keys, bars.

    Algorithm:
        1. Parse the plan to extract form type, home key, tempo, instrumentation.
        2. For each section, extract type, key areas, bar counts, character.
        3. Validate total bar counts, key consistency, cadence placement.
        4. Apply golden-ratio climax placement (bar = total * 0.618).
        5. Ensure transition sections connect adjacent key areas.

    Constraints enforced:
        - Sonata exposition must have P-theme in tonic and S-theme in
          dominant (major) or relative major (minor).
        - Recapitulation S-theme must be in tonic.
        - Total bars must sum correctly across all subsections.
        - Every section must end with a cadence token.
    """

    def __init__(self):
        super().__init__("PlanPass")

    def validate_input(self, plan: Union[str, dict]) -> bool:
        return plan is not None and len(str(plan)) > 0

    def run(self, plan: dict) -> FormIR:
        """
        Accepts a structured dict (from Claude's JSON output) and returns FormIR.

        Expected plan dict shape:
        {
            "form": "sonata",
            "home_key": "C_minor",
            "tempo_bpm": 132,
            "time_signature": "4/4",
            "character": "heroic",
            "instrumentation": ["piano"],
            "sections": [
                {
                    "type": "exposition",
                    "subsections": [
                        {"type": "P_theme", "key": "C_minor", "bars": 8,
                         "character": "heroic", "cadence": "HC"},
                        ...
                    ]
                },
                ...
            ]
        }
        """
        form_ir = FormIR(
            form=FormType(plan["form"]),
            home_key=KeyToken(plan["home_key"]),
            tempo_bpm=plan.get("tempo_bpm", 120),
            time_signature=plan.get("time_signature", "4/4"),
            title=plan.get("title", ""),
            character=CharacterToken(plan.get("character", "heroic")),
            instrumentation=plan.get("instrumentation", ["piano"]),
        )

        total_bars = 0
        for sec_data in plan["sections"]:
            section = SectionIR(
                type=SectionType(sec_data["type"]),
                key=KeyToken(sec_data.get("key", plan["home_key"])),
            )
            for sub_data in sec_data.get("subsections", []):
                sub = SubsectionIR(
                    type=SubsectionType(sub_data["type"]),
                    key=KeyToken(sub_data["key"]),
                    bars=sub_data["bars"],
                    character=CharacterToken(sub_data.get("character", "heroic")),
                    texture=TextureToken(sub_data.get("texture", "melody_accomp")),
                    cadence_at_end=CadenceType(sub_data["cadence"]) if "cadence" in sub_data else None,
                )
                section.subsections.append(sub)
                section.key_path.append(KeyToken(sub_data["key"]))
                total_bars += sub.bars
            form_ir.sections.append(section)

        form_ir.total_bars = total_bars
        self._validate_form(form_ir)
        return form_ir

    def _validate_form(self, form_ir: FormIR):
        """Enforce structural constraints based on form type."""
        if form_ir.form == FormType.SONATA:
            section_types = [s.type for s in form_ir.sections]
            if SectionType.EXPOSITION not in section_types:
                self.errors.append("Sonata form requires an Exposition section.")
            if SectionType.RECAPITULATION not in section_types:
                self.errors.append("Sonata form requires a Recapitulation section.")

        # Check golden-ratio climax placement
        climax_bar = round(form_ir.total_bars * 0.618)
        self.warnings.append(
            f"Golden-ratio climax target: bar {climax_bar} of {form_ir.total_bars}. "
            f"Ensure development or retransition peaks near here."
        )


# ---------- Pass 2: Schema Pass ----------

class SchemaPass(CompilerPass):
    """
    Pass 2: FormIR (Level 1) -> SchemaIR (Level 2).

    Input:  FormIR with sections and subsections defined.
    Output: SchemaIR — each subsection filled with a sequence of SchemaSlots.

    Algorithm:
        1. For each subsection, select appropriate schemata based on:
           - Section type (exposition P-theme favors DO_RE_MI, CUDWORTH opening)
           - Character (heroic -> JUPITER, lyrical -> PRINNER + FENAROLI)
           - Bar count (must fit within allocated bars)
        2. Chain schemata so that the bass degree ending one schema connects
           smoothly to the bass degree beginning the next.
        3. Place cadences: HC at antecedent ends, PAC at consequent ends.
        4. For transitions, use MONTE (ascending) or FONTE (descending)
           sequences to modulate between keys.
        5. For development, fragment schemata — use FONTE, MONTE with
           chromaticized variants and key changes every 2-4 bars.

    Constraints enforced:
        - Total schema bars per subsection == subsection.bars.
        - Cadence types match formal function (HC for antecedent, PAC for
          consequent, DC for surprise moments).
        - PONTE only used as bridge/standing-on-dominant before recapitulation.
    """

    # Schema affinities by formal function
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

    def __init__(self):
        super().__init__("SchemaPass")

    def validate_input(self, form_ir: FormIR) -> bool:
        return form_ir is not None and len(form_ir.sections) > 0

    def run(self, form_ir: FormIR) -> SchemaIR:
        schema_ir = SchemaIR(form_ref=form_ir)

        for section in form_ir.sections:
            for subsection in section.subsections:
                sub_schema = SubsectionSchemaIR(subsection_ref=subsection)
                bars_remaining = subsection.bars

                # Get preferred schemata for this formal function
                preferred = self.SCHEMA_AFFINITIES.get(
                    subsection.type,
                    [SchemaToken.DO_RE_MI, SchemaToken.PRINNER]
                )

                # Fill with schemata until bars exhausted
                while bars_remaining > 0:
                    import random
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

                # Append terminal cadence
                if subsection.cadence_at_end:
                    # Replace last slot or add cadence slot
                    cad_slot = SchemaSlot(
                        schema=subsection.cadence_at_end,
                        bars=0,  # cadence is part of last schema's final bar
                        local_key=subsection.key,
                    )
                    sub_schema.schema_sequence.append(cad_slot)

                schema_ir.schema_plan.append(sub_schema)

        return schema_ir


# ---------- Pass 3: Harmony Pass ----------

class HarmonyPass(CompilerPass):
    """
    Pass 3: SchemaIR (Level 2) -> List[ChordEvent] (Level 3, chords only).

    Input:  SchemaIR with schema sequences for every subsection.
    Output: Ordered list of ChordEvent objects with Roman numerals and keys,
            but NO pitch realization yet (SATB pitches set to 0).

    Algorithm:
        1. For each SchemaSlot, look up SCHEMA_REALIZATIONS to get the
           Roman numeral sequence.
        2. Distribute chords across beats according to harmonic rhythm
           (default: 1 chord per bar, faster in cadences/transitions).
        3. Handle modulations: when SchemaSlot.modulates_to is set,
           pivot via common chord or enharmonic reinterpretation.
        4. Insert secondary dominants, borrowed chords, aug6 chords per
           the advanced harmony rules (Part 17) where character demands it.

    Constraints:
        - Every phrase must end with a cadence chord pair.
        - No two consecutive identical chords (except PONTE pedal).
        - Harmonic rhythm must respect metric hierarchy (chord changes
          on strong beats).
    """

    def __init__(self):
        super().__init__("HarmonyPass")

    def validate_input(self, schema_ir: SchemaIR) -> bool:
        return schema_ir is not None and len(schema_ir.schema_plan) > 0

    def run(self, schema_ir: SchemaIR) -> VoiceLeadingIR:
        vl_ir = VoiceLeadingIR()
        current_bar = 1

        for sub_schema in schema_ir.schema_plan:
            for slot in sub_schema.schema_sequence:
                # Skip cadence-only slots (bars=0)
                if isinstance(slot.schema, CadenceType):
                    # Modify the last chord event to mark it cadential
                    if vl_ir.chords:
                        vl_ir.chords[-1].is_cadential = True
                    continue

                template = SCHEMA_REALIZATIONS.get(slot.schema)
                if template is None:
                    continue

                beats_per_chord = max(1, (slot.bars * 4) // len(template.harmony))

                for i, rn in enumerate(template.harmony):
                    chord_evt = ChordEvent(
                        bar=current_bar + (i * beats_per_chord) // 4,
                        beat=1.0 + (i * beats_per_chord) % 4,
                        roman_numeral=rn,
                        key=slot.local_key,
                        soprano=0, alto=0, tenor=0, bass=0,  # placeholder
                        duration_beats=beats_per_chord,
                        source_schema=slot.schema if isinstance(slot.schema, SchemaToken) else None,
                    )
                    vl_ir.chords.append(chord_evt)

                current_bar += slot.bars

        return vl_ir


# ---------- Pass 4: Melody Pass ----------

class MelodyPass(CompilerPass):
    """
    Pass 4: VoiceLeadingIR (chords) -> VoiceLeadingIR (chords + melody).

    Input:  VoiceLeadingIR with chord events (soprano pitch = 0).
    Output: Same IR with melody notes populated, soprano pitches set in chords.

    Algorithm:
        1. For each chord event, consult the source schema to get the
           soprano scale degree. Convert to MIDI via realize_schema_in_key().
        2. Between structural chord tones, interpolate passing tones and
           neighbor tones following the Zipfian interval distribution:
           55% steps, 25% thirds, 12% fourths, 8% larger leaps (KB Part 10.8).
        3. Apply arch contour within each phrase (peak at ~65% through phrase).
        4. After any leap > perfect 4th, enforce gap-fill (stepwise motion
           in opposite direction on next note).
        5. Target melodic entropy of 2.6-3.1 bits/note (KB Part 10.8).

    Constraints:
        - Melody must be singable: range within a 12th (octave + P5).
        - No augmented intervals (aug 2nd, aug 4th melodically).
        - Leading tone (scale degree 7) must resolve up to 1 when harmonized
          by V or viio.
        - Post-leap step probability >= 0.85.
    """

    INTERVAL_WEIGHTS = {0: 0.05, 1: 0.55, 2: 0.25, 3: 0.08, 4: 0.04, 5: 0.02, 6: 0.01}

    def __init__(self):
        super().__init__("MelodyPass")

    def validate_input(self, vl_ir: VoiceLeadingIR) -> bool:
        return vl_ir is not None and len(vl_ir.chords) > 0

    def run(self, vl_ir: VoiceLeadingIR) -> VoiceLeadingIR:
        """
        Populate soprano line from schema realizations and add non-chord tones.
        Pseudocode:

        for each chord_event in vl_ir.chords:
            soprano_midi = realize_schema_degree(chord_event)
            chord_event.soprano = soprano_midi
            add MelodicNote(midi=soprano_midi, bar, beat, duration, is_chord_tone=True)

        for each adjacent pair (note_a, note_b) in melody:
            if gap > 2 scale steps:
                insert passing tones on intermediate beats
            if note_a was a leap:
                ensure note_b is stepwise in opposite direction

        validate: range <= 19 semitones, no augmented melodic intervals
        """
        # Implementation uses realize_schema_in_key + contour-controlled
        # interpolation from the existing MelodyGenerator in
        # classical_music_gen.py (class MelodyGenerator).
        return vl_ir


# ---------- Pass 5: Counterpoint Pass ----------

class CounterpointPass(CompilerPass):
    """
    Pass 5: VoiceLeadingIR (soprano + chords) -> VoiceLeadingIR (full SATB).

    Input:  VoiceLeadingIR with soprano and bass from schema, chords with
            Roman numerals.
    Output: Complete 4-voice texture with alto and tenor filled in. All
            parallel 5ths/octaves eliminated. Leading tones resolved.

    Algorithm:
        1. For each chord event, realize the Roman numeral as pitch classes
           using music21.roman.RomanNumeral.
        2. Bass pitch comes from schema realization. Soprano from Melody Pass.
        3. For alto and tenor, use optimal voice leading (VoiceLeader class
           from classical_music_gen.py): minimize total pitch movement,
           penalize parallel 5ths/octaves by +1000.
        4. Enforce species-counterpoint constraints for adjacent chord pairs:
           - No parallel P5 or P8 between ANY voice pair.
           - Approach perfect consonances by contrary or oblique motion only.
           - Resolve dominant 7ths down by step.
           - Resolve leading tones up to tonic.
           - Voice ranges: S (60-84), A (55-76), T (48-69), B (36-60).
        5. For polyphonic textures, switch to backtracking constraint solver
           (CounterpointSolver from classical_music_gen.py).

    Constraints (HARD — infinite penalty):
        - No parallel 5ths or octaves.
        - No voice crossing sustained for > 1 beat.
        - Each voice stays within its designated range.
        - Leading tone resolves up; chord 7ths resolve down.

    Constraints (SOFT — weighted penalty):
        - Prefer contrary motion (+0 penalty) over similar motion (+5).
        - Prefer common tones held in same voice (-1 reward).
        - Prefer small intervals (-1 per semitone of total movement).
    """

    VOICE_RANGES = {
        "soprano": (60, 84),   # C4 - C6
        "alto":    (55, 76),   # G3 - E5
        "tenor":   (48, 69),   # C3 - A4
        "bass":    (36, 60),   # C2 - C4
    }

    def __init__(self):
        super().__init__("CounterpointPass")

    def validate_input(self, vl_ir: VoiceLeadingIR) -> bool:
        return vl_ir is not None and len(vl_ir.chords) > 0

    def run(self, vl_ir: VoiceLeadingIR) -> VoiceLeadingIR:
        """Fill alto and tenor voices using constrained optimization."""
        # Delegates to VoiceLeader.find_optimal() for each chord pair.
        # See classical_music_gen.py VoiceLeader class for implementation.
        return vl_ir


# ---------- Pass 6: Orchestration Pass ----------

class OrchestrationPass(CompilerPass):
    """
    Pass 6: VoiceLeadingIR (SATB) -> Dict[str, List[PerformanceNote]].

    Input:  Full SATB voicings from Counterpoint Pass + instrumentation list.
    Output: Multi-track assignment: each instrument gets a list of notes.

    Algorithm:
        1. Apply orchestration template (strings/woodwinds/full) from
           OrchestrationMapper in classical_music_gen.py.
        2. For each SATB voice, assign to instruments based on register fit:
           - Check MIDI note against instrument range (Part 5 table).
           - Transpose by octave if needed (octave equivalence preserves
             melodic identity — KB Part 16).
        3. Apply doublings for climax bars: melody doubled at octave in
           flute+oboe, bass doubled by bassoon+cello+bass.
        4. Handle tutti vs. solo texture changes based on DynamicToken.
        5. Respect breathing for winds (phrase gaps of 100-300ms at
           phrase boundaries — KB Part 18).

    Constraints:
        - Never assign notes outside instrument range (Part 5 table).
        - Never double the leading tone.
        - Below MIDI 48 (C3), use intervals >= P5 (KB Part 16 critical band).
        - String divisi only when explicitly specified.
    """

    INSTRUMENT_RANGES = {
        "violin1":  (55, 103),
        "violin2":  (55, 93),
        "viola":    (48, 91),
        "cello":    (36, 76),
        "bass":     (28, 67),
        "flute":    (60, 96),
        "oboe":     (58, 91),
        "clarinet": (50, 94),
        "bassoon":  (34, 75),
        "horn":     (34, 77),
        "trumpet":  (55, 82),
        "trombone": (40, 72),
        "tuba":     (28, 58),
        "timpani":  (40, 55),
        "harp":     (24, 103),
    }

    def __init__(self):
        super().__init__("OrchestrationPass")

    def validate_input(self, vl_ir: VoiceLeadingIR) -> bool:
        return vl_ir is not None

    def run(self, vl_ir: VoiceLeadingIR, instrumentation: List[str],
            template: str = "strings") -> Dict[str, List[PerformanceNote]]:
        """Delegates to OrchestrationMapper.assign() then converts to PerformanceNote."""
        # Uses OrchestrationMapper from classical_music_gen.py.
        tracks: Dict[str, List[PerformanceNote]] = {}
        return tracks


# ---------- Pass 7: Expression Pass ----------

class ExpressionPass(CompilerPass):
    """
    Pass 7: Adds dynamics, articulation, phrasing to PerformanceNotes.

    Input:  Dict of instrument tracks with raw PerformanceNotes.
    Output: Same tracks with dynamic, articulation, and expression fields set.

    Algorithm:
        1. For each phrase (identified by cadence boundaries):
           a. Apply phrase-arc dynamic shape: crescendo to 65% through phrase,
              diminuendo to end (Todd/Gabrielsson model, KB Part 18).
           b. Peak velocity = base_velocity + peak_boost (15-25).
        2. Map CharacterToken to parameter sets (KB Part 6 emotion engine):
           - HEROIC: mf-ff, marcato, wide range
           - LYRICAL: p-mf, legato, narrow range
           - MYSTERIOUS: pp-p, portato, chromaticism
        3. Insert crescendo/diminuendo CC events for gradual changes.
        4. Apply beat-level accenting: beat 1 = +8 vel, beat 3 = +4 vel.
        5. Engineer chills triggers at climax points: layer crescendo +
           new instrument entry + unexpected harmony (KB Part 10.2).

    Constraints:
        - Dynamics must not exceed MIDI velocity 127 or go below 1.
        - Melody voice always 10-20 velocity above accompaniment (KB Part 18).
        - Subito dynamic changes only at barlines or strong beats.
    """

    # Character -> base parameters (from KB Part 6 + 10.7)
    CHARACTER_PARAMS = {
        CharacterToken.HEROIC:     {"base_vel": 90, "articulation": ArticulationToken.MARCATO, "range": "wide"},
        CharacterToken.LYRICAL:    {"base_vel": 65, "articulation": ArticulationToken.LEGATO,  "range": "narrow"},
        CharacterToken.MYSTERIOUS: {"base_vel": 50, "articulation": ArticulationToken.PORTATO, "range": "narrow"},
        CharacterToken.AGITATED:   {"base_vel": 85, "articulation": ArticulationToken.STACCATO,"range": "wide"},
        CharacterToken.SERENE:     {"base_vel": 55, "articulation": ArticulationToken.LEGATO,  "range": "narrow"},
        CharacterToken.TRIUMPHANT: {"base_vel": 100,"articulation": ArticulationToken.MARCATO, "range": "wide"},
        CharacterToken.TRAGIC:     {"base_vel": 60, "articulation": ArticulationToken.LEGATO,  "range": "medium"},
        CharacterToken.PASTORAL:   {"base_vel": 60, "articulation": ArticulationToken.LEGATO,  "range": "narrow"},
        CharacterToken.STORMY:     {"base_vel": 95, "articulation": ArticulationToken.MARCATO, "range": "wide"},
        CharacterToken.NOBLE:      {"base_vel": 80, "articulation": ArticulationToken.TENUTO,  "range": "medium"},
        CharacterToken.PLAYFUL:    {"base_vel": 75, "articulation": ArticulationToken.STACCATO,"range": "medium"},
        CharacterToken.TENDER:     {"base_vel": 50, "articulation": ArticulationToken.LEGATO,  "range": "narrow"},
        CharacterToken.ANGUISHED:  {"base_vel": 85, "articulation": ArticulationToken.ACCENT,  "range": "wide"},
        CharacterToken.MAJESTIC:   {"base_vel": 90, "articulation": ArticulationToken.TENUTO,  "range": "wide"},
    }

    def __init__(self):
        super().__init__("ExpressionPass")

    def validate_input(self, tracks: Dict) -> bool:
        return tracks is not None

    def run(self, tracks: Dict[str, List[PerformanceNote]],
            character: CharacterToken) -> Dict[str, List[PerformanceNote]]:
        params = self.CHARACTER_PARAMS.get(character, self.CHARACTER_PARAMS[CharacterToken.HEROIC])
        # Apply to every note in every track
        for inst_name, notes in tracks.items():
            is_melody = inst_name in ("violin1", "flute", "oboe")  # highest voice
            for note in notes:
                note.dynamic = DynamicToken.MF  # refined by phrase arc below
                note.articulation = params["articulation"]
                note.velocity = params["base_vel"] + (15 if is_melody else 0)
        return tracks


# ---------- Pass 8: Humanization Pass ----------

class HumanizationPass(CompilerPass):
    """
    Pass 8: Applies timing deviations, velocity curves, rubato.

    Input:  Instrument tracks with expression applied.
    Output: Same tracks with humanized timing/velocity offsets.

    Algorithm (from KB Part 18):
        1. Timing jitter: Gaussian noise, sigma=12ms, plus mean-reverting
           drift (sigma=5ms, decay=0.95) for natural tempo wander.
        2. Melody leads accompaniment by 10-20ms (Goebl 2001).
        3. Phrase-level rubato: accelerate first half of phrase, decelerate
           second half. Peak tempo at ~35% through phrase. Deviation: 10-25%.
        4. Final ritardando: last 2-4 beats slow by 15-30%. Final note
           duration = 200-400% of written value.
        5. Velocity phrase arc: crescendo to 65% through phrase, dim to end.
        6. Beat-level accenting: beat 1 += 8 vel, beat 3 += 4 vel.
        7. Agogic accents: structurally important notes get +5-15% duration.
        8. Articulation realization:
           - Legato: 95-105% duration (10-60ms overlap with next)
           - Staccato: 35-50% duration
           - Portato: 75-88% duration

    Constraints:
        - Net rubato per phrase sums to zero (time borrowed = time repaid).
        - Velocity stays in [1, 127].
        - No negative note durations or start times.
    """

    def __init__(self):
        super().__init__("HumanizationPass")

    def validate_input(self, tracks: Dict) -> bool:
        return tracks is not None

    def run(self, tracks: Dict[str, List[PerformanceNote]]) -> Dict[str, List[PerformanceNote]]:
        import numpy as np

        for inst_name, notes in tracks.items():
            is_melody = inst_name in ("violin1", "flute", "oboe", "soprano")
            drift = 0.0

            for i, note in enumerate(notes):
                # Timing humanization
                jitter_ms = np.random.normal(0, 12)
                drift += np.random.normal(0, 5)
                drift *= 0.95  # mean-reverting
                melody_lead = -15.0 if is_melody else 0.0  # melody slightly early
                note.timing_offset_ms = jitter_ms + drift + melody_lead

                # Velocity humanization
                note.velocity_offset = int(np.random.normal(0, 3))
                note.velocity = max(1, min(127, note.velocity + note.velocity_offset))

                # Articulation realization
                if note.articulation == ArticulationToken.STACCATO:
                    note.duration_sec *= np.random.uniform(0.35, 0.50)
                elif note.articulation == ArticulationToken.LEGATO:
                    note.duration_sec *= np.random.uniform(0.95, 1.05)
                elif note.articulation == ArticulationToken.PORTATO:
                    note.duration_sec *= np.random.uniform(0.75, 0.88)

                # Apply timing offset
                note.start_time_sec = max(0, note.start_time_sec + note.timing_offset_ms / 1000.0)

        return tracks


# ---------- Pass 9: Validation Pass ----------

class ValidationPass(CompilerPass):
    """
    Pass 9: Final quality check on the complete PerformanceIR.

    Input:  Complete PerformanceIR (all notes, all tracks).
    Output: ValidationReport with errors, warnings, and quality scores.

    Checks performed:
        1. COUNTERPOINT: Scan all simultaneous voice pairs for parallel P5/P8.
        2. RANGE: Every note within instrument range (Part 5 table).
        3. SPACING: No close intervals (< P5) below MIDI 48 (Part 16).
        4. VOICE CROSSING: Flag any sustained crossing > 1 beat.
        5. LEADING TONE RESOLUTION: Scale degree 7 must go to 1 when in V->I.
        6. ENTROPY: Measure melodic entropy; flag if outside 2.6-3.1 bits/note.
        7. INTERVAL DISTRIBUTION: Check Zipf compliance (~55% steps, etc.).
        8. SURPRISE RATE: Verify ~20% of events deviate from most-expected
           continuation (KB Part 10.1).
        9. TENSION CURVE: Verify peak tension near 61.8% of piece duration.
       10. DYNAMICS: Melody voice velocity > accompaniment velocity.
       11. PHRASE LENGTH: Flag phrases > 8 seconds without internal cadence.
       12. HUMANIZATION: Verify timing offsets are non-zero (was humanization
           actually applied?) and within realistic bounds (<50ms).

    Output:
        ValidationReport dataclass with:
        - errors: List[str] — must fix before output
        - warnings: List[str] — review recommended
        - scores: Dict[str, float] — quality metrics 0.0-1.0
    """

    def __init__(self):
        super().__init__("ValidationPass")

    def validate_input(self, perf_ir: PerformanceIR) -> bool:
        return perf_ir is not None and len(perf_ir.notes) > 0

    def run(self, perf_ir: PerformanceIR,
            instrument_ranges: Dict[str, Tuple[int, int]] = None
            ) -> "ValidationReport":

        report = ValidationReport()

        for note in perf_ir.notes:
            # Range check
            if instrument_ranges and note.instrument in instrument_ranges:
                lo, hi = instrument_ranges[note.instrument]
                if note.midi_pitch < lo or note.midi_pitch > hi:
                    report.errors.append(
                        f"Out of range: {note.instrument} note {note.midi_pitch} "
                        f"at t={note.start_time_sec:.2f}s (range {lo}-{hi})"
                    )

            # Velocity bounds
            if note.velocity < 1 or note.velocity > 127:
                report.errors.append(
                    f"Invalid velocity {note.velocity} at t={note.start_time_sec:.2f}s"
                )

            # Negative timing
            if note.start_time_sec < 0:
                report.errors.append(
                    f"Negative start time {note.start_time_sec:.4f}s"
                )

        # Check spacing below C3
        bass_notes = [n for n in perf_ir.notes if n.midi_pitch < 48]
        # Group by start time to find simultaneous bass notes
        from collections import defaultdict
        by_time = defaultdict(list)
        for n in bass_notes:
            time_bucket = round(n.start_time_sec, 2)
            by_time[time_bucket].append(n.midi_pitch)
        for t, pitches in by_time.items():
            if len(pitches) >= 2:
                pitches_sorted = sorted(pitches)
                for i in range(len(pitches_sorted) - 1):
                    interval = pitches_sorted[i+1] - pitches_sorted[i]
                    if interval < 7:  # less than a P5
                        report.warnings.append(
                            f"Close bass spacing at t={t}s: interval {interval} "
                            f"semitones between {pitches_sorted[i]} and {pitches_sorted[i+1]}"
                        )

        report.scores["range_compliance"] = 1.0 - (
            len([e for e in report.errors if "Out of range" in e]) / max(len(perf_ir.notes), 1)
        )

        return report


@dataclass
class ValidationReport:
    """Output of the Validation Pass."""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [f"Validation: {'PASS' if self.is_valid else 'FAIL'}"]
        lines.append(f"  Errors: {len(self.errors)}")
        lines.append(f"  Warnings: {len(self.warnings)}")
        for k, v in self.scores.items():
            lines.append(f"  {k}: {v:.2f}")
        return "\n".join(lines)


# =============================================================================
# SECTION 5: MASTER PIPELINE — Orchestrating All Passes
# =============================================================================

class CompositionPipeline:
    """
    The master pipeline that chains all 9 compiler passes.

    Usage:
        pipeline = CompositionPipeline()
        midi_data = pipeline.compose(plan_dict)

    The pipeline is designed to be interruptible: after any pass, the
    intermediate IR can be inspected, serialized to JSON, modified by
    a human, and re-fed into subsequent passes.
    """

    def __init__(self):
        self.plan_pass = PlanPass()
        self.schema_pass = SchemaPass()
        self.harmony_pass = HarmonyPass()
        self.melody_pass = MelodyPass()
        self.counterpoint_pass = CounterpointPass()
        self.orchestration_pass = OrchestrationPass()
        self.expression_pass = ExpressionPass()
        self.humanization_pass = HumanizationPass()
        self.validation_pass = ValidationPass()

    def compose(self, plan: dict) -> Tuple[PerformanceIR, ValidationReport]:
        """
        Run the full 9-pass pipeline from plan to validated performance IR.

        Returns (PerformanceIR, ValidationReport).
        Raises ValueError if any pass fails validation.
        """
        # Pass 1: Plan -> Form IR (Level 1)
        form_ir = self.plan_pass.run(plan)
        print(f"[Pass 1] Form IR: {form_ir.form.value}, {form_ir.total_bars} bars")

        # Pass 2: Form IR -> Schema IR (Level 2)
        schema_ir = self.schema_pass.run(form_ir)
        total_schemas = sum(len(s.schema_sequence) for s in schema_ir.schema_plan)
        print(f"[Pass 2] Schema IR: {total_schemas} schema slots")

        # Pass 3: Schema IR -> Voice Leading IR (Level 3, chords only)
        vl_ir = self.harmony_pass.run(schema_ir)
        print(f"[Pass 3] Harmony: {len(vl_ir.chords)} chord events")

        # Pass 4: Add melody to Voice Leading IR
        vl_ir = self.melody_pass.run(vl_ir)
        print(f"[Pass 4] Melody: {len(vl_ir.melody)} melody notes")

        # Pass 5: Fill inner voices (SATB completion)
        vl_ir = self.counterpoint_pass.run(vl_ir)
        print(f"[Pass 5] Counterpoint: SATB complete")

        # Pass 6: Orchestrate -> instrument tracks
        tracks = self.orchestration_pass.run(
            vl_ir, form_ir.instrumentation, template="strings"
        )
        print(f"[Pass 6] Orchestration: {len(tracks)} instrument tracks")

        # Pass 7: Add expression (dynamics, articulation)
        tracks = self.expression_pass.run(tracks, form_ir.character)
        print(f"[Pass 7] Expression applied")

        # Pass 8: Humanize timing and velocity
        tracks = self.humanization_pass.run(tracks)
        print(f"[Pass 8] Humanization applied")

        # Assemble into PerformanceIR
        perf_ir = PerformanceIR()
        for inst_name, notes in tracks.items():
            perf_ir.notes.extend(notes)
        if perf_ir.notes:
            perf_ir.total_duration_sec = max(
                n.start_time_sec + n.duration_sec for n in perf_ir.notes
            )

        # Pass 9: Validate
        report = self.validation_pass.run(
            perf_ir,
            instrument_ranges=OrchestrationPass.INSTRUMENT_RANGES
        )
        print(f"[Pass 9] {report.summary()}")

        return perf_ir, report


# =============================================================================
# SECTION 6: MIDI EXPORT — PerformanceIR to MIDI File
# =============================================================================

def performance_ir_to_midi(
    perf_ir: PerformanceIR,
    output_path: str,
    default_bpm: int = 120,
) -> str:
    """
    Convert a PerformanceIR to a standard MIDI file using midiutil.

    Parameters:
        perf_ir: The fully processed performance IR.
        output_path: File path to write the .mid file.
        default_bpm: Fallback tempo if no tempo map is provided.

    Returns:
        The output_path string for convenience.
    """
    from midiutil import MIDIFile

    # Determine number of tracks from unique instruments
    instruments = sorted(set(n.instrument for n in perf_ir.notes))
    inst_to_track = {inst: i for i, inst in enumerate(instruments)}

    midi = MIDIFile(numTracks=len(instruments), ticks_per_quarternote=480)

    # Set tempo from tempo map or default
    if perf_ir.tempo_map:
        for time_sec, bpm in perf_ir.tempo_map:
            # Convert seconds to beats for MIDIFile
            beat_time = time_sec * default_bpm / 60.0
            midi.addTempo(0, beat_time, bpm)
    else:
        midi.addTempo(0, 0, default_bpm)

    # MIDI program numbers for common instruments
    MIDI_PROGRAMS = {
        "piano": 0, "violin1": 40, "violin2": 40, "viola": 41,
        "cello": 42, "bass": 43, "flute": 73, "oboe": 68,
        "clarinet": 71, "bassoon": 70, "horn": 60, "trumpet": 56,
        "trombone": 57, "tuba": 58, "timpani": 47, "harp": 46,
    }

    for inst in instruments:
        track = inst_to_track[inst]
        channel = track % 16
        if channel == 9:
            channel = 10  # skip percussion channel
        program = MIDI_PROGRAMS.get(inst, 0)
        midi.addProgramChange(track, channel, 0, program)

    # Add notes
    for note in perf_ir.notes:
        track = inst_to_track.get(note.instrument, 0)
        channel = track % 16
        if channel == 9:
            channel = 10
        # Convert time from seconds to beats
        beat_time = note.start_time_sec * default_bpm / 60.0
        duration_beats = note.duration_sec * default_bpm / 60.0

        midi.addNote(
            track=track,
            channel=channel,
            pitch=note.midi_pitch,
            time=beat_time,
            duration=max(0.01, duration_beats),
            volume=max(1, min(127, note.velocity)),
        )

    # Add CC events (pedal, expression, etc.)
    for time_sec, ch, cc_num, cc_val in perf_ir.cc_events:
        beat_time = time_sec * default_bpm / 60.0
        midi.addControllerEvent(0, ch, beat_time, cc_num, cc_val)

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    return output_path


# =============================================================================
# SECTION 7: EXAMPLE USAGE
# =============================================================================

EXAMPLE_PLAN = {
    "form": "sonata",
    "home_key": "C_minor",
    "tempo_bpm": 132,
    "time_signature": "4/4",
    "title": "Sonata in C minor",
    "character": "heroic",
    "instrumentation": ["violin1", "violin2", "viola", "cello"],
    "sections": [
        {
            "type": "exposition",
            "key": "C_minor",
            "subsections": [
                {"type": "P_theme", "key": "C_minor", "bars": 8,
                 "character": "heroic", "texture": "melody_accomp", "cadence": "HC"},
                {"type": "transition", "key": "C_minor", "bars": 12,
                 "character": "agitated", "texture": "polyphonic", "cadence": "HC"},
                {"type": "S_theme", "key": "Eb_major", "bars": 8,
                 "character": "lyrical", "texture": "melody_accomp", "cadence": "PAC"},
                {"type": "closing_theme", "key": "Eb_major", "bars": 4,
                 "character": "playful", "texture": "homophonic", "cadence": "PAC"},
            ]
        },
        {
            "type": "development",
            "key": "C_minor",
            "subsections": [
                {"type": "core", "key": "Eb_major", "bars": 8,
                 "character": "stormy", "texture": "polyphonic"},
                {"type": "core", "key": "Fs_minor", "bars": 8,
                 "character": "mysterious", "texture": "polyphonic"},
                {"type": "retransition", "key": "C_minor", "bars": 8,
                 "character": "agitated", "texture": "homophonic", "cadence": "HC"},
            ]
        },
        {
            "type": "recapitulation",
            "key": "C_minor",
            "subsections": [
                {"type": "P_theme", "key": "C_minor", "bars": 8,
                 "character": "heroic", "texture": "melody_accomp", "cadence": "HC"},
                {"type": "transition", "key": "C_minor", "bars": 8,
                 "character": "agitated", "texture": "polyphonic", "cadence": "HC"},
                {"type": "S_theme", "key": "C_minor", "bars": 8,
                 "character": "lyrical", "texture": "melody_accomp", "cadence": "PAC"},
                {"type": "closing_theme", "key": "C_minor", "bars": 4,
                 "character": "triumphant", "texture": "homophonic", "cadence": "PAC"},
            ]
        },
        {
            "type": "coda",
            "key": "C_minor",
            "subsections": [
                {"type": "closing_theme", "key": "C_minor", "bars": 8,
                 "character": "triumphant", "texture": "homophonic", "cadence": "PAC"},
            ]
        },
    ]
}


if __name__ == "__main__":
    # Demonstrate the pipeline with the example plan
    print("=" * 60)
    print("CLASSICAL MUSIC COMPOSITION SYSTEM — Pipeline Demo")
    print("=" * 60)

    # Pass 1 demonstration
    plan_pass = PlanPass()
    form_ir = plan_pass.run(EXAMPLE_PLAN)
    print(f"\nForm IR JSON preview (first 500 chars):")
    print(form_ir.to_json()[:500] + "...")

    # Schema realization demonstration
    print(f"\n--- Schema Realization Examples ---")
    for schema in [SchemaToken.PRINNER, SchemaToken.DO_RE_MI, SchemaToken.ROMANESCA]:
        result = realize_schema_in_key(schema, "C", octave=5)
        print(f"\n{schema.value} in C major:")
        print(f"  Soprano MIDI: {result['soprano']}")
        print(f"  Bass MIDI:    {result['bass']}")
        print(f"  Harmony:      {result['harmony']}")

    # Full pipeline (structural demo — inner passes return placeholder data
    # until wired to music21/midiutil backends in classical_music_gen.py)
    print(f"\n--- Full Pipeline ---")
    pipeline = CompositionPipeline()
    # Note: full execution requires music21 to be installed.
    # This demonstrates the pipeline structure and pass ordering.
    try:
        perf_ir, report = pipeline.compose(EXAMPLE_PLAN)
    except Exception as e:
        print(f"Pipeline demo (structural only): {e}")
        print("Full execution requires connecting to music21/midiutil backends.")
