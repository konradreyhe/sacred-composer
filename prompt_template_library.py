"""
PROMPT TEMPLATE LIBRARY — Claude as Composition Planner
========================================================

Production-ready prompt templates for a two-pass music composition system:
    Pass 1: Claude generates a structured JSON composition plan.
    Pass 2: Python code (SYSTEM_ARCHITECTURE.py) realizes that plan as MIDI.

Each template contains:
    1. The exact prompt text (ready to send to Claude API)
    2. The expected JSON output schema
    3. Example input and output
    4. Validation rules for the output

Usage:
    from prompt_template_library import TEMPLATES, MASTER_SYSTEM_PROMPT
    import anthropic

    client = anthropic.Anthropic()
    prompt = TEMPLATES["sonata_exposition"].format_prompt(
        home_key="C_minor",
        character="heroic",
        tempo_bpm=132,
    )
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        system=MASTER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import json
import re


# =============================================================================
# MASTER SYSTEM PROMPT
# =============================================================================
#
# This prompt is sent as the `system` parameter on every Claude API call.
# It establishes Claude's role, the vocabulary it must use, and the rules
# it must respect. All six templates assume this context is loaded.
# =============================================================================

MASTER_SYSTEM_PROMPT = """\
You are the PLANNER in a two-pass classical music composition system.

=== YOUR ROLE ===
You generate detailed, structured JSON composition plans. You do NOT generate
audio, MIDI, code, or notation. A separate Python pipeline (the "Realizer")
reads your JSON output and compiles it into MIDI through four passes:
  Pass 1 (YOU):  Natural-language request -> structured JSON plan
  Pass 2:        JSON plan -> Level 1 FormIR (form, sections, keys, bars)
  Pass 3:        FormIR -> Level 2 SchemaIR (galant schemata sequences)
  Pass 4:        SchemaIR -> Level 3 VoiceLeadingIR -> Level 4 PerformanceIR -> MIDI

Everything you output must be valid JSON parseable by Python's json.loads().
Do NOT wrap output in markdown code fences. Output raw JSON only.

=== TOKEN VOCABULARY ===
You MUST use ONLY these tokens. Any value outside these sets will cause a
parse error in the Realizer.

FORM TYPES:
  sonata | rondo | ternary | binary | theme_and_variations | fugue |
  minuet_and_trio | through_composed

SECTION TYPES:
  exposition | development | recapitulation | coda | introduction |
  A_section | B_section | C_section |
  fugue_exposition | episode | middle_entry | stretto |
  transition | closing

SUBSECTION TYPES:
  P_theme | S_theme | closing_theme | transition | core | retransition |
  standing_on_dominant | subject_entry | answer_entry | countersubject |
  pedal_point

GALANT SCHEMATA (Gjerdingen):
  do_re_mi | prinner | monte | fonte | ponte | romanesca | quiescenza |
  sol_fa_mi | indugio | fenaroli | comma | cudworth | jupiter | meyer |
  pastorella | passo_indietro

CADENCE TYPES:
  PAC | IAC | HC | DC | plagal | phrygian_HC | evaded | abandoned

KEY TOKENS (all 24 major/minor):
  C_major | C_minor | Db_major | Cs_minor | D_major | D_minor |
  Eb_major | Eb_minor | E_major | E_minor | F_major | F_minor |
  Fs_major | Fs_minor | G_major | G_minor | Ab_major | Gs_minor |
  A_major | A_minor | Bb_major | Bb_minor | B_major | B_minor

KEY RELATIONSHIPS:
  to_dominant | to_subdominant | to_relative_major | to_relative_minor |
  to_parallel_major | to_parallel_minor | to_mediant | to_flat_mediant |
  to_flat_submediant | to_supertonic | to_neapolitan | to_tritone |
  enharmonic_pivot

TEXTURE TOKENS:
  melody_accomp | homophonic | polyphonic | unison | antiphonal |
  homorhythmic | chorale | tremolo | ostinato | alberti_bass |
  murky_bass | arpeggio

CHARACTER TOKENS:
  heroic | lyrical | mysterious | agitated | serene | triumphant |
  tragic | pastoral | stormy | noble | playful | tender | anguished |
  majestic

DYNAMIC TOKENS:
  ppp | pp | p | mp | mf | f | ff | fff | crescendo | diminuendo |
  subito_p | subito_f | sfz | fp

ARTICULATION TOKENS:
  legato | staccato | staccatissimo | marcato | tenuto | portato |
  accent | trill | mordent | turn | appoggiatura | acciaccatura

=== THE 50 COMPOSITION RULES (condensed) ===
You must respect ALL of these. The Realizer enforces them; plans that
violate them produce low evaluation scores.

COUNTERPOINT (Rules 1-10):
  1. No parallel 5ths or octaves between any voice pair.
  2. Approach perfect consonances by contrary or oblique motion only.
  3. Voice ranges: soprano 60-81, alto 55-74, tenor 48-67, bass 40-62 (MIDI).
  4. No melodic tritones, 7ths, or intervals larger than an octave.
  5. Resolve suspensions downward by step (7-6, 4-3, 9-8).
  6. Dissonances on strong beats only as suspensions or appoggiaturas.
  7. Dissonances on weak beats only as passing tones or neighbor tones.
  8. Leading tone resolves upward to tonic.
  9. Chordal 7ths resolve downward by step.
  10. Never double the leading tone.

MELODY (Rules 11-18):
  11. 60-70% stepwise motion, 15-20% thirds, 10-15% leaps.
  12. Leaps larger than a 4th must be followed by step in opposite direction.
  13. Climax note should appear once, near golden-ratio point (0.618).
  14. Overall contour: arch shape preferred (rise-peak-fall).
  15. Phrase length: 4 or 8 bars (2-bar units for sentences).
  16. Antecedent ends on HC; consequent ends on PAC.
  17. Avoid sequences longer than 3 repetitions.
  18. Surprise rate 15-25% of melodic events deviate from most-likely continuation.

HARMONY (Rules 19-30):
  19. Sonata exposition: P-theme in tonic, S-theme in dominant (major) or
      relative major (minor).
  20. Recapitulation S-theme must return to tonic key.
  21. Modulations use pivot chords, not abrupt jumps (except for expressive effect).
  22. Cadential 6/4 resolves to V before final I.
  23. Deceptive cadences (V-vi) at max 15% of cadences; most should be PAC/HC.
  24. Harmonic rhythm: typically one chord per bar in slow tempi, two per bar in fast.
  25. Secondary dominants approach their targets by resolution.
  26. Augmented 6th chords resolve to V or cadential 6/4.
  27. Neapolitan (bII6) approaches V or cadential 6/4.
  28. Consonant events / total events ratio: 0.70-0.85.
  29. Dominant pedal points precede recapitulations.
  30. Tonic pedal points appear in codas.

RHYTHM & METER (Rules 31-36):
  31. Metric hierarchy: strongest accent on beat 1, secondary on beat 3 (in 4/4).
  32. Syncopation at 15-25% of rhythmic events.
  33. Tempo ranges: Adagio 40-60, Andante 60-80, Moderato 80-120, Allegro 120-160.
  34. Hemiola at cadence points in triple meter is idiomatic.
  35. Avoid more than 2 bars of rhythmic unison across all voices.
  36. Euclidean rhythms for non-melody ostinato patterns.

FORM & STRUCTURE (Rules 37-44):
  37. Golden-ratio climax placement: bar = total_bars * 0.618.
  38. Repeat thematic material 2-4 times before major variation.
  39. Each variation alters 10-30% of original material.
  40. Fugue subject: 2-4 bars, clear tonic-dominant polarity.
  41. Fugue answer: tonal (mutated) if subject spans tonic-dominant boundary.
  42. Development section modulates through at least 2 keys outside tonic/dominant.
  43. Transition sections must connect adjacent key areas with pivot chords.
  44. Total bars must sum correctly across all subsections.

EXPRESSION & NEUROSCIENCE (Rules 45-50):
  45. Tension peak at 60-75% through each phrase (golden ratio).
  46. Chills triggers: layer 2-3 of {unexpected harmony, crescendo, new timbre,
      appoggiatura, melodic descent from sustained high note, enharmonic shift}.
  47. Space chills candidates at 45-90 second intervals.
  48. Wundt curve: increase complexity through development, return to familiarity
      in recapitulation.
  49. Optimal tension segment duration: 8-16 seconds before resolution.
  50. Repetition with 10-30% variation for maximum pleasure response.

=== SCHEMA REALIZATIONS (reference) ===
Each schema maps to concrete soprano degrees, bass degrees, and harmony:
  do_re_mi:  sop[1,2,3]  bass[1,7,1]  harm[I, V6, I]           2 bars
  prinner:   sop[6,5,4,3] bass[4,3,2,1] harm[IV, I6, viio6, I] 4 bars
  monte:     sop[1,7,2,1] bass[4,5,5,6] harm[ii, V, iii, vi]   4 bars
  fonte:     sop[6,5,5,4] bass[4,3,3,2] harm[ii, V/V, I6, V]   4 bars
  ponte:     sop[2,2,2,2] bass[5,5,5,5] harm[V, V, V, V]       4 bars
  romanesca: sop[3,2,1,7] bass[1,5,6,3] harm[I, V, vi, iii]    4 bars
  quiescenza:sop[1,2,7,1] bass[1,1,1,1] harm[I, IV64, V7, I]   4 bars
  sol_fa_mi: sop[5,4,#4,5] bass[1,1,7,1] harm[I, IV, V/V, V]   2 bars
  indugio:   sop[2,4,2,2] bass[5,5,5,5] harm[V, V42, V65, V]   4 bars
  fenaroli:  sop[4,3,7,1] bass[1,2,3,1] harm[I, V6, I6, I]     4 bars
  comma:     sop[7,1]     bass[5,1]     harm[V, I]              1 bar
  cudworth:  sop[1,1,7,1] bass[1,2,7,1] harm[I, V6, V, I]      2 bars
  jupiter:   sop[1,2,3,4] bass[1,7,1,2] harm[I, V6, I, ii6]    4 bars
  meyer:     sop[1,7,4,3] bass[1,2,7,1] harm[I, V6, viio6, I]  4 bars
  pastorella:sop[1,7,1,1] bass[5,5,3,1] harm[I64, V, I6, I]    2 bars
  passo_indietro: sop[2,1] bass[5,1]    harm[V, I]              1 bar

=== OUTPUT FORMAT ===
Always output a single JSON object. Never include commentary, preamble, or
markdown formatting. The JSON must be directly parseable by json.loads().
Follow the specific schema requested by each template prompt.
"""


# =============================================================================
# TEMPLATE DATA CLASS
# =============================================================================

@dataclass
class PromptTemplate:
    """One prompt template with its schema, example, and validation."""
    name: str
    description: str
    prompt_text: str                         # Python format string with {placeholders}
    output_schema: Dict[str, Any]            # JSON Schema (draft-07 subset)
    example_input: Dict[str, Any]            # kwargs to .format_prompt()
    example_output: Dict[str, Any]           # expected JSON from Claude
    validation_rules: List[str]              # human-readable rules
    _validators: List[Callable] = field(default_factory=list, repr=False)

    def format_prompt(self, **kwargs) -> str:
        """Fill in template placeholders and return the final prompt string."""
        return self.prompt_text.format(**kwargs)

    def validate_output(self, output: dict) -> List[str]:
        """Run all validation rules against a parsed JSON output. Returns list of errors."""
        errors = []
        for validator_fn in self._validators:
            err = validator_fn(output)
            if err:
                errors.extend(err if isinstance(err, list) else [err])
        return errors


# =============================================================================
# SHARED VALIDATORS
# =============================================================================

VALID_KEYS = {
    "C_major", "C_minor", "Db_major", "Cs_minor", "D_major", "D_minor",
    "Eb_major", "Eb_minor", "E_major", "E_minor", "F_major", "F_minor",
    "Fs_major", "Fs_minor", "G_major", "G_minor", "Ab_major", "Gs_minor",
    "A_major", "A_minor", "Bb_major", "Bb_minor", "B_major", "B_minor",
}

VALID_SCHEMATA = {
    "do_re_mi", "prinner", "monte", "fonte", "ponte", "romanesca",
    "quiescenza", "sol_fa_mi", "indugio", "fenaroli", "comma", "cudworth",
    "jupiter", "meyer", "pastorella", "passo_indietro",
}

VALID_CADENCES = {"PAC", "IAC", "HC", "DC", "plagal", "phrygian_HC", "evaded", "abandoned"}

VALID_TEXTURES = {
    "melody_accomp", "homophonic", "polyphonic", "unison", "antiphonal",
    "homorhythmic", "chorale", "tremolo", "ostinato", "alberti_bass",
    "murky_bass", "arpeggio",
}

VALID_CHARACTERS = {
    "heroic", "lyrical", "mysterious", "agitated", "serene", "triumphant",
    "tragic", "pastoral", "stormy", "noble", "playful", "tender",
    "anguished", "majestic",
}

VALID_DYNAMICS = {
    "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff",
    "crescendo", "diminuendo", "subito_p", "subito_f", "sfz", "fp",
}

VALID_SECTION_TYPES = {
    "exposition", "development", "recapitulation", "coda", "introduction",
    "A_section", "B_section", "C_section",
    "fugue_exposition", "episode", "middle_entry", "stretto",
    "transition", "closing",
}

VALID_SUBSECTION_TYPES = {
    "P_theme", "S_theme", "closing_theme", "transition", "core",
    "retransition", "standing_on_dominant", "subject_entry",
    "answer_entry", "countersubject", "pedal_point",
}


def _validate_key(output: dict) -> List[str]:
    """Check that all key tokens are valid."""
    errors = []
    if "home_key" in output and output["home_key"] not in VALID_KEYS:
        errors.append(f"Invalid home_key: {output['home_key']}")
    for sec in output.get("sections", []):
        for sub in sec.get("subsections", []):
            if sub.get("key") and sub["key"] not in VALID_KEYS:
                errors.append(f"Invalid key in subsection: {sub['key']}")
    return errors


def _validate_cadences(output: dict) -> List[str]:
    errors = []
    for sec in output.get("sections", []):
        for sub in sec.get("subsections", []):
            cad = sub.get("cadence")
            if cad and cad not in VALID_CADENCES:
                errors.append(f"Invalid cadence: {cad}")
    return errors


def _validate_schemata(output: dict) -> List[str]:
    errors = []
    for sec in output.get("sections", []):
        for sub in sec.get("subsections", []):
            for slot in sub.get("schema_sequence", []):
                s = slot.get("schema") if isinstance(slot, dict) else None
                if s and s not in VALID_SCHEMATA and s not in VALID_CADENCES:
                    errors.append(f"Invalid schema token: {s}")
    return errors


def _validate_bars_sum(output: dict) -> List[str]:
    """Check that subsection bars sum to total_bars (if present)."""
    errors = []
    total_declared = output.get("total_bars")
    if total_declared is None:
        return errors
    computed = 0
    # Strategy 1: sections -> subsections (sonata, fugue)
    for sec in output.get("sections", []):
        for sub in sec.get("subsections", []):
            computed += sub.get("bars", 0)
    # Strategy 2: sections with bars directly (emotional_arc, free_composition)
    if computed == 0:
        for sec in output.get("sections", []):
            computed += sec.get("bars", 0)
    # Strategy 3: theme + variations (theme_and_variations)
    if computed == 0:
        theme = output.get("theme", {})
        computed += theme.get("bars", 0)
        for var in output.get("variations", []):
            computed += var.get("bars", 0)
    if computed > 0 and computed != total_declared:
        errors.append(
            f"Bar count mismatch: declared total_bars={total_declared}, "
            f"sum of component bars={computed}"
        )
    return errors


def _validate_tempo(output: dict) -> List[str]:
    errors = []
    bpm = output.get("tempo_bpm")
    if bpm is not None and (bpm < 20 or bpm > 300):
        errors.append(f"Tempo out of range: {bpm} (expected 20-300)")
    return errors


def _validate_textures(output: dict) -> List[str]:
    errors = []
    for sec in output.get("sections", []):
        for sub in sec.get("subsections", []):
            t = sub.get("texture")
            if t and t not in VALID_TEXTURES:
                errors.append(f"Invalid texture: {t}")
    return errors


def _validate_characters(output: dict) -> List[str]:
    errors = []
    if output.get("character") and output["character"] not in VALID_CHARACTERS:
        errors.append(f"Invalid top-level character: {output['character']}")
    for sec in output.get("sections", []):
        for sub in sec.get("subsections", []):
            c = sub.get("character")
            if c and c not in VALID_CHARACTERS:
                errors.append(f"Invalid subsection character: {c}")
    return errors


COMMON_VALIDATORS = [
    _validate_key,
    _validate_cadences,
    _validate_schemata,
    _validate_bars_sum,
    _validate_tempo,
    _validate_textures,
    _validate_characters,
]


# =============================================================================
# TEMPLATE 1: SONATA EXPOSITION
# =============================================================================

def _validate_sonata_exposition(output: dict) -> List[str]:
    """Sonata-specific validation: P-theme in tonic, S-theme in dominant/relative."""
    errors = []
    home = output.get("home_key", "")
    is_minor = home.endswith("_minor")

    for sec in output.get("sections", []):
        for sub in sec.get("subsections", []):
            if sub.get("type") == "P_theme" and sub.get("key") != home:
                errors.append(f"P_theme must be in home key ({home}), got {sub['key']}")
            if sub.get("type") == "S_theme":
                s_key = sub.get("key", "")
                if is_minor:
                    # relative major expected
                    if "_major" not in s_key:
                        errors.append(
                            f"In minor-key sonata, S_theme should be in relative major, got {s_key}"
                        )
                else:
                    # dominant expected
                    if s_key == home:
                        errors.append("S_theme must NOT be in tonic key in exposition")
    return errors


SONATA_EXPOSITION_PROMPT = """\
Generate a SONATA EXPOSITION plan for the following parameters:

  Home key:       {home_key}
  Character:      {character}
  Tempo:          {tempo_bpm} BPM
  Time signature: {time_signature}
  Instrumentation: {instrumentation}

Produce a complete exposition containing:

1. PRIMARY THEME (P-theme): In the home key. Describe:
   - Melodic contour (arch, ascending, descending, wavelike)
   - Rhythmic character (dotted, even, syncopated, lombard)
   - A schema sequence of 3-5 galant schemata filling the P-theme bars
   - Cadence type at the end (must be HC or IAC to leave room for transition)

2. TRANSITION (TR): Modulating from tonic to the secondary key. Describe:
   - Modulation method (pivot chord, chromatic, sequential)
   - Texture change from P-theme
   - Energy trajectory (intensifying, dissolving, static)
   - Schema sequence (typically monte or fonte for sequences, sol_fa_mi for HC approach)
   - Ends on HC in the new key (standing on the dominant)

3. SECONDARY THEME (S-theme): In the contrasting key. Describe:
   - How it contrasts with P-theme on at least 3 of these dimensions:
     {{texture, character, rhythm, register, dynamics, articulation}}
   - Melodic contour and schema sequence (3-5 schemata)
   - Cadence type (PAC to establish the new key)

4. CLOSING SECTION: Confirm the secondary key. Describe:
   - Brief, cadential material
   - Schema sequence (typically comma, passo_indietro, or quiescenza)
   - Ends with strong PAC

For a MINOR home key, the S-theme should be in the RELATIVE MAJOR.
For a MAJOR home key, the S-theme should be in the DOMINANT key.

Output a single JSON object matching this exact structure:
{{
  "form": "sonata",
  "home_key": "<key_token>",
  "tempo_bpm": <int>,
  "time_signature": "<str>",
  "character": "<character_token>",
  "instrumentation": [<str>, ...],
  "total_bars": <int>,
  "sections": [
    {{
      "type": "exposition",
      "subsections": [
        {{
          "type": "P_theme",
          "key": "<key_token>",
          "bars": <int>,
          "character": "<character_token>",
          "texture": "<texture_token>",
          "melodic_contour": "<arch|ascending|descending|wavelike>",
          "rhythmic_character": "<dotted|even|syncopated|lombard>",
          "dynamic": "<dynamic_token>",
          "schema_sequence": [
            {{"schema": "<schema_token>", "bars": <int>, "local_key": "<key_token>"}}
          ],
          "cadence": "<cadence_token>",
          "notes": "<free text: any extra detail for the Realizer>"
        }},
        {{
          "type": "transition",
          "key": "<starting_key_token>",
          "target_key": "<target_key_token>",
          "bars": <int>,
          "character": "<character_token>",
          "texture": "<texture_token>",
          "modulation_method": "<pivot_chord|chromatic|sequential>",
          "energy_trajectory": "<intensifying|dissolving|static>",
          "schema_sequence": [...],
          "cadence": "HC",
          "notes": "<free text>"
        }},
        {{
          "type": "S_theme",
          "key": "<secondary_key_token>",
          "bars": <int>,
          "character": "<character_token>",
          "texture": "<texture_token>",
          "melodic_contour": "<...>",
          "rhythmic_character": "<...>",
          "dynamic": "<dynamic_token>",
          "contrast_dimensions": ["<dim1>", "<dim2>", "<dim3>"],
          "schema_sequence": [...],
          "cadence": "PAC",
          "notes": "<free text>"
        }},
        {{
          "type": "closing_theme",
          "key": "<secondary_key_token>",
          "bars": <int>,
          "character": "<character_token>",
          "texture": "<texture_token>",
          "schema_sequence": [...],
          "cadence": "PAC",
          "notes": "<free text>"
        }}
      ]
    }}
  ]
}}
"""

SONATA_EXPOSITION_TEMPLATE = PromptTemplate(
    name="sonata_exposition",
    description="Generates a complete sonata-form exposition plan with P-theme, transition, S-theme, and closing.",
    prompt_text=SONATA_EXPOSITION_PROMPT,
    output_schema={
        "type": "object",
        "required": ["form", "home_key", "tempo_bpm", "time_signature", "character",
                      "instrumentation", "total_bars", "sections"],
        "properties": {
            "form": {"type": "string", "enum": ["sonata"]},
            "home_key": {"type": "string", "enum": list(VALID_KEYS)},
            "tempo_bpm": {"type": "integer", "minimum": 20, "maximum": 300},
            "time_signature": {"type": "string"},
            "character": {"type": "string", "enum": list(VALID_CHARACTERS)},
            "instrumentation": {"type": "array", "items": {"type": "string"}},
            "total_bars": {"type": "integer", "minimum": 16, "maximum": 200},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "subsections"],
                    "properties": {
                        "type": {"type": "string"},
                        "subsections": {"type": "array"},
                    },
                },
            },
        },
    },
    example_input={
        "home_key": "C_minor",
        "character": "heroic",
        "tempo_bpm": 132,
        "time_signature": "4/4",
        "instrumentation": '["piano"]',
    },
    example_output={
        "form": "sonata",
        "home_key": "C_minor",
        "tempo_bpm": 132,
        "time_signature": "4/4",
        "character": "heroic",
        "instrumentation": ["piano"],
        "total_bars": 48,
        "sections": [
            {
                "type": "exposition",
                "subsections": [
                    {
                        "type": "P_theme",
                        "key": "C_minor",
                        "bars": 12,
                        "character": "heroic",
                        "texture": "melody_accomp",
                        "melodic_contour": "arch",
                        "rhythmic_character": "dotted",
                        "dynamic": "f",
                        "schema_sequence": [
                            {"schema": "do_re_mi", "bars": 2, "local_key": "C_minor"},
                            {"schema": "monte", "bars": 4, "local_key": "C_minor"},
                            {"schema": "prinner", "bars": 4, "local_key": "C_minor"},
                            {"schema": "sol_fa_mi", "bars": 2, "local_key": "C_minor"},
                        ],
                        "cadence": "HC",
                        "notes": "Bold opening octave leap, dotted rhythms suggest martial energy. Sentence structure: 2+2+4+4.",
                    },
                    {
                        "type": "transition",
                        "key": "C_minor",
                        "target_key": "Eb_major",
                        "bars": 8,
                        "character": "agitated",
                        "texture": "polyphonic",
                        "modulation_method": "sequential",
                        "energy_trajectory": "intensifying",
                        "schema_sequence": [
                            {"schema": "monte", "bars": 4, "local_key": "C_minor"},
                            {"schema": "ponte", "bars": 4, "local_key": "Eb_major"},
                        ],
                        "cadence": "HC",
                        "notes": "Rising sequences build energy. Monte sequence modulates through D_minor before arriving on Bb dominant pedal (= V of Eb).",
                    },
                    {
                        "type": "S_theme",
                        "key": "Eb_major",
                        "bars": 16,
                        "character": "lyrical",
                        "texture": "melody_accomp",
                        "melodic_contour": "wavelike",
                        "rhythmic_character": "even",
                        "dynamic": "mp",
                        "contrast_dimensions": ["character", "texture", "dynamics"],
                        "schema_sequence": [
                            {"schema": "romanesca", "bars": 4, "local_key": "Eb_major"},
                            {"schema": "prinner", "bars": 4, "local_key": "Eb_major"},
                            {"schema": "fenaroli", "bars": 4, "local_key": "Eb_major"},
                            {"schema": "sol_fa_mi", "bars": 2, "local_key": "Eb_major"},
                            {"schema": "comma", "bars": 2, "local_key": "Eb_major"},
                        ],
                        "cadence": "PAC",
                        "notes": "Lyrical, singing melody in Eb major. Contrasts P-theme heroism with warmth and tenderness. Period structure: 8+8.",
                    },
                    {
                        "type": "closing_theme",
                        "key": "Eb_major",
                        "bars": 12,
                        "character": "triumphant",
                        "texture": "homophonic",
                        "schema_sequence": [
                            {"schema": "quiescenza", "bars": 4, "local_key": "Eb_major"},
                            {"schema": "cudworth", "bars": 2, "local_key": "Eb_major"},
                            {"schema": "passo_indietro", "bars": 1, "local_key": "Eb_major"},
                            {"schema": "comma", "bars": 1, "local_key": "Eb_major"},
                            {"schema": "passo_indietro", "bars": 1, "local_key": "Eb_major"},
                            {"schema": "comma", "bars": 1, "local_key": "Eb_major"},
                            {"schema": "PAC", "bars": 2, "local_key": "Eb_major"},
                        ],
                        "cadence": "PAC",
                        "notes": "Cadential confirmations in Eb. Repeated V-I gestures cement the new key.",
                    },
                ],
            }
        ],
    },
    validation_rules=[
        "home_key must be a valid KeyToken",
        "P_theme key must equal home_key",
        "S_theme key must be dominant (major) or relative major (minor) of home_key",
        "closing_theme key must equal S_theme key",
        "Transition must end on HC",
        "S_theme must end on PAC",
        "Closing must end on PAC",
        "Sum of all subsection bars must equal total_bars",
        "Schema bars within each subsection must sum to the subsection bars",
        "All schema tokens must be from the valid set",
        "All cadence tokens must be from the valid set",
        "tempo_bpm must be between 20 and 300",
    ],
    _validators=COMMON_VALIDATORS + [_validate_sonata_exposition],
)


# =============================================================================
# TEMPLATE 2: THEME AND VARIATIONS
# =============================================================================

THEME_AND_VARIATIONS_PROMPT = """\
Generate a THEME AND VARIATIONS plan for the following parameters:

  Home key:        {home_key}
  Character:       {character}
  Theme length:    {theme_bars} bars
  Number of vars:  {num_variations}
  Tempo:           {tempo_bpm} BPM
  Time signature:  {time_signature}
  Instrumentation: {instrumentation}

Produce a plan containing:

1. THEME: A complete theme in binary form (two halves, each repeated).
   - Melody description (contour, range, interval preferences)
   - Harmonic plan with schema sequence
   - Phrase structure (period or sentence)
   - First half ends on HC; second half ends on PAC

2. VARIATIONS (one per object in the "variations" array):
   Each variation must specify:
   - technique: one of {{ornamental, rhythmic, mode_change, texture_change,
     character_change, register_change, tempo_change, harmonic_enrichment,
     contrapuntal, culmination}}
   - What specifically changes (description)
   - What stays the same (the harmonic skeleton, the phrase structure, or the melody)
   - Key (same as theme unless mode_change or modulation)
   - Bars (same as theme unless augmented/diminished)
   - Character, texture, tempo, dynamic changes
   - Schema sequence (same skeleton as theme, possibly reharmonized)

IMPORTANT constraints:
- Variation techniques must progress in complexity and intensity.
- At least one variation must change mode (major<->minor).
- The final variation should be a "culmination" that combines techniques.
- Each variation must preserve the theme's phrase structure (same bar counts per half).
- No two adjacent variations should use the same technique.

Output a single JSON object:
{{
  "form": "theme_and_variations",
  "home_key": "<key_token>",
  "tempo_bpm": <int>,
  "time_signature": "<str>",
  "character": "<character_token>",
  "instrumentation": [<str>, ...],
  "total_bars": <int>,
  "theme": {{
    "bars": <int>,
    "form": "binary",
    "phrase_structure": "<period|sentence>",
    "melodic_contour": "<arch|ascending|descending|wavelike>",
    "dynamic": "<dynamic_token>",
    "texture": "<texture_token>",
    "first_half": {{
      "bars": <int>,
      "schema_sequence": [...],
      "cadence": "HC"
    }},
    "second_half": {{
      "bars": <int>,
      "schema_sequence": [...],
      "cadence": "PAC"
    }},
    "notes": "<free text>"
  }},
  "variations": [
    {{
      "number": <int>,
      "technique": "<technique_name>",
      "description": "<what changes>",
      "preserved": "<what stays the same>",
      "key": "<key_token>",
      "bars": <int>,
      "character": "<character_token>",
      "texture": "<texture_token>",
      "tempo_bpm": <int or null>,
      "dynamic": "<dynamic_token>",
      "first_half": {{
        "schema_sequence": [...],
        "cadence": "<cadence_token>"
      }},
      "second_half": {{
        "schema_sequence": [...],
        "cadence": "<cadence_token>"
      }},
      "notes": "<free text>"
    }}
  ]
}}
"""

def _validate_theme_and_variations(output: dict) -> List[str]:
    errors = []
    theme = output.get("theme", {})
    if theme.get("first_half", {}).get("cadence") not in ("HC", "IAC"):
        errors.append("Theme first half should end on HC or IAC")
    if theme.get("second_half", {}).get("cadence") != "PAC":
        errors.append("Theme second half must end on PAC")

    variations = output.get("variations", [])
    techniques = [v.get("technique") for v in variations]
    # No two adjacent techniques the same
    for i in range(len(techniques) - 1):
        if techniques[i] == techniques[i + 1]:
            errors.append(f"Adjacent variations {i+1} and {i+2} use same technique: {techniques[i]}")
    # At least one mode_change
    if "mode_change" not in techniques:
        errors.append("At least one variation must use mode_change technique")
    # Last should be culmination
    if variations and variations[-1].get("technique") != "culmination":
        errors.append("Final variation should use 'culmination' technique")
    return errors


THEME_AND_VARIATIONS_TEMPLATE = PromptTemplate(
    name="theme_and_variations",
    description="Generates a theme with binary form and 4-6 progressive variations.",
    prompt_text=THEME_AND_VARIATIONS_PROMPT,
    output_schema={
        "type": "object",
        "required": ["form", "home_key", "tempo_bpm", "theme", "variations"],
        "properties": {
            "form": {"type": "string", "enum": ["theme_and_variations"]},
            "home_key": {"type": "string"},
            "theme": {"type": "object", "required": ["bars", "first_half", "second_half"]},
            "variations": {"type": "array", "minItems": 4, "maxItems": 8},
        },
    },
    example_input={
        "home_key": "A_major",
        "character": "noble",
        "theme_bars": 16,
        "num_variations": 5,
        "tempo_bpm": 108,
        "time_signature": "4/4",
        "instrumentation": '["piano"]',
    },
    example_output={
        "form": "theme_and_variations",
        "home_key": "A_major",
        "tempo_bpm": 108,
        "time_signature": "4/4",
        "character": "noble",
        "instrumentation": ["piano"],
        "total_bars": 96,
        "theme": {
            "bars": 16,
            "form": "binary",
            "phrase_structure": "period",
            "melodic_contour": "arch",
            "dynamic": "mf",
            "texture": "melody_accomp",
            "first_half": {
                "bars": 8,
                "schema_sequence": [
                    {"schema": "do_re_mi", "bars": 2, "local_key": "A_major"},
                    {"schema": "prinner", "bars": 4, "local_key": "A_major"},
                    {"schema": "sol_fa_mi", "bars": 2, "local_key": "A_major"},
                ],
                "cadence": "HC",
            },
            "second_half": {
                "bars": 8,
                "schema_sequence": [
                    {"schema": "romanesca", "bars": 4, "local_key": "A_major"},
                    {"schema": "fenaroli", "bars": 2, "local_key": "A_major"},
                    {"schema": "comma", "bars": 2, "local_key": "A_major"},
                ],
                "cadence": "PAC",
            },
            "notes": "Singing melody in the soprano, Alberti bass accompaniment. Period: antecedent (4+4) + consequent (4+4).",
        },
        "variations": [
            {
                "number": 1,
                "technique": "ornamental",
                "description": "Sixteenth-note figuration decorates the theme melody with passing tones, neighbor tones, and turns.",
                "preserved": "Harmonic skeleton and phrase structure identical to theme.",
                "key": "A_major",
                "bars": 16,
                "character": "playful",
                "texture": "melody_accomp",
                "tempo_bpm": 108,
                "dynamic": "mf",
                "first_half": {
                    "schema_sequence": [
                        {"schema": "do_re_mi", "bars": 2, "local_key": "A_major"},
                        {"schema": "prinner", "bars": 4, "local_key": "A_major"},
                        {"schema": "sol_fa_mi", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "HC",
                },
                "second_half": {
                    "schema_sequence": [
                        {"schema": "romanesca", "bars": 4, "local_key": "A_major"},
                        {"schema": "fenaroli", "bars": 2, "local_key": "A_major"},
                        {"schema": "comma", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "PAC",
                },
                "notes": "Melody becomes a continuous stream of sixteenths. Every other note is a chord tone from the original theme.",
            },
            {
                "number": 2,
                "technique": "rhythmic",
                "description": "Dotted rhythms and syncopation transform the theme. Left hand plays off-beat chords.",
                "preserved": "Melody pitches (on downbeats) and harmonic skeleton.",
                "key": "A_major",
                "bars": 16,
                "character": "heroic",
                "texture": "homophonic",
                "tempo_bpm": 108,
                "dynamic": "f",
                "first_half": {
                    "schema_sequence": [
                        {"schema": "do_re_mi", "bars": 2, "local_key": "A_major"},
                        {"schema": "prinner", "bars": 4, "local_key": "A_major"},
                        {"schema": "sol_fa_mi", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "HC",
                },
                "second_half": {
                    "schema_sequence": [
                        {"schema": "romanesca", "bars": 4, "local_key": "A_major"},
                        {"schema": "fenaroli", "bars": 2, "local_key": "A_major"},
                        {"schema": "comma", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "PAC",
                },
                "notes": "March-like dotted rhythm. Forte dynamic. Syncopation at ~20% of events.",
            },
            {
                "number": 3,
                "technique": "mode_change",
                "description": "Theme in A minor. Melody adjusted for minor scale. Chromatic inflections.",
                "preserved": "Phrase structure and rhythmic profile of the original theme.",
                "key": "A_minor",
                "bars": 16,
                "character": "tragic",
                "texture": "melody_accomp",
                "tempo_bpm": 96,
                "dynamic": "p",
                "first_half": {
                    "schema_sequence": [
                        {"schema": "do_re_mi", "bars": 2, "local_key": "A_minor"},
                        {"schema": "prinner", "bars": 4, "local_key": "A_minor"},
                        {"schema": "sol_fa_mi", "bars": 2, "local_key": "A_minor"},
                    ],
                    "cadence": "HC",
                },
                "second_half": {
                    "schema_sequence": [
                        {"schema": "romanesca", "bars": 4, "local_key": "A_minor"},
                        {"schema": "fenaroli", "bars": 2, "local_key": "A_minor"},
                        {"schema": "comma", "bars": 2, "local_key": "A_minor"},
                    ],
                    "cadence": "PAC",
                },
                "notes": "Parallel minor transforms character entirely. Slower tempo. Added appoggiaturas for pathos.",
            },
            {
                "number": 4,
                "technique": "texture_change",
                "description": "Fugato treatment: theme becomes a 2-voice canon at the octave, 1 bar apart.",
                "preserved": "Theme melody as subject. Harmonic skeleton implied by canon.",
                "key": "A_major",
                "bars": 16,
                "character": "noble",
                "texture": "polyphonic",
                "tempo_bpm": 108,
                "dynamic": "mf",
                "first_half": {
                    "schema_sequence": [
                        {"schema": "do_re_mi", "bars": 2, "local_key": "A_major"},
                        {"schema": "prinner", "bars": 4, "local_key": "A_major"},
                        {"schema": "sol_fa_mi", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "HC",
                },
                "second_half": {
                    "schema_sequence": [
                        {"schema": "romanesca", "bars": 4, "local_key": "A_major"},
                        {"schema": "fenaroli", "bars": 2, "local_key": "A_major"},
                        {"schema": "comma", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "PAC",
                },
                "notes": "Canonic writing. Second voice enters one bar later at the lower octave.",
            },
            {
                "number": 5,
                "technique": "culmination",
                "description": "Combines ornamental figuration, forte dynamics, full texture. Extended coda with tonic pedal.",
                "preserved": "Harmonic skeleton. Phrase structure extended by 4-bar coda.",
                "key": "A_major",
                "bars": 16,
                "character": "triumphant",
                "texture": "homophonic",
                "tempo_bpm": 120,
                "dynamic": "ff",
                "first_half": {
                    "schema_sequence": [
                        {"schema": "do_re_mi", "bars": 2, "local_key": "A_major"},
                        {"schema": "prinner", "bars": 4, "local_key": "A_major"},
                        {"schema": "sol_fa_mi", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "HC",
                },
                "second_half": {
                    "schema_sequence": [
                        {"schema": "romanesca", "bars": 4, "local_key": "A_major"},
                        {"schema": "fenaroli", "bars": 2, "local_key": "A_major"},
                        {"schema": "comma", "bars": 2, "local_key": "A_major"},
                    ],
                    "cadence": "PAC",
                },
                "notes": "Grand finale. Thick chords, wide register, triumphant character. Accelerated tempo.",
            },
        ],
    },
    validation_rules=[
        "Theme first_half must end on HC or IAC",
        "Theme second_half must end on PAC",
        "No two adjacent variations may use the same technique",
        "At least one variation must use mode_change",
        "Final variation must use 'culmination' technique",
        "Each variation bars should equal theme bars (unless documented otherwise)",
        "Schema bars within each half must sum to that half's bar count",
        "All schema and cadence tokens must be from valid sets",
    ],
    _validators=COMMON_VALIDATORS + [_validate_theme_and_variations],
)


# =============================================================================
# TEMPLATE 3: FUGUE EXPOSITION
# =============================================================================

FUGUE_EXPOSITION_PROMPT = """\
Generate a FUGUE EXPOSITION plan for the following parameters:

  Home key:        {home_key}
  Number of voices: {num_voices}
  Character:       {character}
  Tempo:           {tempo_bpm} BPM
  Time signature:  {time_signature}
  Instrumentation: {instrumentation}

Produce a plan containing:

1. SUBJECT: 2-4 bars. Describe:
   - Melodic contour (scale degrees, not specific pitches)
   - Rhythmic profile (note values, any rests, characteristic rhythm)
   - Tonic-dominant polarity (does it emphasize 1-5? span tonic to dominant?)
   - Starting scale degree and ending scale degree
   - Whether it modulates to the dominant or stays in tonic

2. ANSWER TYPE: Decide tonal vs. real.
   - TONAL answer: if the subject prominently features scale degrees 1-5 at the
     start, mutate them to 5-1 (the "tonal adjustment"). Explain which notes change.
   - REAL answer: exact transposition up a 5th. Use only if the subject does not
     cross the tonic-dominant boundary prominently.

3. COUNTERSUBJECT: The line that accompanies the answer. Describe:
   - Invertible counterpoint at the octave (it must work above OR below the subject)
   - Rhythmic complementarity (fills gaps in the subject's rhythm)
   - Melodic independence (contrasting contour to the subject)
   - Interval constraints with subject: mostly 3rds, 6ths, and 10ths; avoid parallel 5ths/8ves

4. VOICE ENTRY ORDER: Which voice enters first, second, third, (fourth).
   Typical: alto-soprano-tenor-bass or soprano-alto-tenor-bass.
   State each entry's role (subject/answer) and key.

5. CODETTA/LINK material between entries (if needed to re-establish tonic).

Output a single JSON object:
{{
  "form": "fugue",
  "home_key": "<key_token>",
  "tempo_bpm": <int>,
  "time_signature": "<str>",
  "character": "<character_token>",
  "instrumentation": [<str>, ...],
  "num_voices": <int>,
  "subject": {{
    "bars": <int>,
    "scale_degrees": [<int>, ...],
    "rhythmic_profile": "<description of note values>",
    "starting_degree": <int>,
    "ending_degree": <int>,
    "contour": "<ascending|descending|arch|inverted_arch|wavelike>",
    "modulates_to_dominant": <bool>,
    "notes": "<free text>"
  }},
  "answer": {{
    "type": "<tonal|real>",
    "tonal_adjustments": "<description of which degrees change, or 'none' if real>",
    "key": "<key_token for the answer, typically the dominant>",
    "notes": "<free text>"
  }},
  "countersubject": {{
    "rhythmic_character": "<description>",
    "contour": "<ascending|descending|arch|inverted_arch|wavelike>",
    "invertible_at": "octave",
    "notes": "<free text describing melodic strategy>"
  }},
  "voice_entries": [
    {{
      "voice": "<soprano|alto|tenor|bass>",
      "entry_bar": <int>,
      "role": "<subject|answer>",
      "key": "<key_token>",
      "accompanying_material": "<free_voices|countersubject|countersubject_2|none>"
    }}
  ],
  "codettas": [
    {{
      "after_entry": <int>,
      "bars": <int>,
      "purpose": "<re-establish tonic|link to next entry>",
      "notes": "<free text>"
    }}
  ],
  "total_bars": <int>,
  "sections": [
    {{
      "type": "fugue_exposition",
      "subsections": [
        {{
          "type": "subject_entry",
          "key": "<key_token>",
          "bars": <int>,
          "character": "<character_token>",
          "texture": "polyphonic",
          "cadence": null
        }}
      ]
    }}
  ]
}}
"""

def _validate_fugue(output: dict) -> List[str]:
    errors = []
    subject = output.get("subject", {})
    if subject.get("bars", 0) < 2 or subject.get("bars", 0) > 4:
        errors.append(f"Fugue subject should be 2-4 bars, got {subject.get('bars')}")

    entries = output.get("voice_entries", [])
    num_voices = output.get("num_voices", 4)
    if len(entries) != num_voices:
        errors.append(f"Expected {num_voices} voice entries, got {len(entries)}")

    # Alternating subject/answer
    for i, entry in enumerate(entries):
        expected_role = "subject" if i % 2 == 0 else "answer"
        if entry.get("role") != expected_role:
            # This is a warning, not hard error (some fugues vary)
            pass

    answer = output.get("answer", {})
    if answer.get("type") not in ("tonal", "real"):
        errors.append(f"Answer type must be 'tonal' or 'real', got {answer.get('type')}")

    return errors


FUGUE_EXPOSITION_TEMPLATE = PromptTemplate(
    name="fugue_exposition",
    description="Generates a fugue exposition plan with subject, answer, countersubject, and voice entries.",
    prompt_text=FUGUE_EXPOSITION_PROMPT,
    output_schema={
        "type": "object",
        "required": ["form", "home_key", "subject", "answer", "countersubject",
                      "voice_entries", "num_voices"],
        "properties": {
            "form": {"type": "string", "enum": ["fugue"]},
            "subject": {
                "type": "object",
                "required": ["bars", "scale_degrees", "contour", "modulates_to_dominant"],
            },
            "answer": {
                "type": "object",
                "required": ["type", "key"],
            },
            "voice_entries": {
                "type": "array",
                "minItems": 2,
                "maxItems": 6,
            },
        },
    },
    example_input={
        "home_key": "D_minor",
        "num_voices": 4,
        "character": "agitated",
        "tempo_bpm": 96,
        "time_signature": "4/4",
        "instrumentation": '["string_quartet"]',
    },
    example_output={
        "form": "fugue",
        "home_key": "D_minor",
        "tempo_bpm": 96,
        "time_signature": "4/4",
        "character": "agitated",
        "instrumentation": ["string_quartet"],
        "num_voices": 4,
        "subject": {
            "bars": 3,
            "scale_degrees": [1, 1, 2, 3, 4, 5, 5, 4, 3, 2, 1],
            "rhythmic_profile": "quarter, eighth-eighth, quarter, quarter, half | quarter, eighth-eighth, quarter, quarter, half | whole note",
            "starting_degree": 1,
            "ending_degree": 1,
            "contour": "arch",
            "modulates_to_dominant": False,
            "notes": "Subject rises scalewise from D to A, then falls back. Begins with repeated tonic for rhythmic drive. Clearly stays within D minor.",
        },
        "answer": {
            "type": "tonal",
            "tonal_adjustments": "First note (degree 1=D) becomes degree 5=A in the answer. The leap 1->5 in the subject becomes 5->1 in the answer, preserving tonic-dominant polarity.",
            "key": "A_minor",
            "notes": "Tonal answer because the subject begins on scale degree 1 and prominently features the 1-5 boundary.",
        },
        "countersubject": {
            "rhythmic_character": "Syncopated eighth notes filling the gaps in the subject's quarter-note motion. Ties across barlines.",
            "contour": "descending",
            "invertible_at": "octave",
            "notes": "Descending stepwise line with chromatic passing tones. Predominantly 3rds and 6ths with the answer. Rhythmic offset creates a continuous texture when combined with the subject.",
        },
        "voice_entries": [
            {
                "voice": "alto",
                "entry_bar": 1,
                "role": "subject",
                "key": "D_minor",
                "accompanying_material": "none",
            },
            {
                "voice": "soprano",
                "entry_bar": 4,
                "role": "answer",
                "key": "A_minor",
                "accompanying_material": "countersubject",
            },
            {
                "voice": "tenor",
                "entry_bar": 8,
                "role": "subject",
                "key": "D_minor",
                "accompanying_material": "countersubject",
            },
            {
                "voice": "bass",
                "entry_bar": 11,
                "role": "answer",
                "key": "A_minor",
                "accompanying_material": "countersubject",
            },
        ],
        "codettas": [
            {
                "after_entry": 2,
                "bars": 1,
                "purpose": "re-establish tonic",
                "notes": "Brief descending scale passage returning from A minor to D minor.",
            },
        ],
        "total_bars": 14,
        "sections": [
            {
                "type": "fugue_exposition",
                "subsections": [
                    {"type": "subject_entry", "key": "D_minor", "bars": 3, "character": "agitated", "texture": "polyphonic", "cadence": None},
                    {"type": "answer_entry", "key": "A_minor", "bars": 3, "character": "agitated", "texture": "polyphonic", "cadence": None},
                    {"type": "subject_entry", "key": "D_minor", "bars": 4, "character": "agitated", "texture": "polyphonic", "cadence": None},
                    {"type": "answer_entry", "key": "A_minor", "bars": 4, "character": "agitated", "texture": "polyphonic", "cadence": "PAC"},
                ],
            }
        ],
    },
    validation_rules=[
        "Subject must be 2-4 bars",
        "Answer type must be 'tonal' or 'real'",
        "Number of voice_entries must equal num_voices",
        "Voice entries must alternate subject/answer",
        "Each voice name must be unique",
        "Entry bars must be in ascending order",
        "Answer key must be the dominant of home_key",
        "All schema, cadence, and key tokens must be valid",
    ],
    _validators=COMMON_VALIDATORS + [_validate_fugue],
)


# =============================================================================
# TEMPLATE 4: EMOTIONAL ARC GENERATOR
# =============================================================================

EMOTIONAL_ARC_PROMPT = """\
Generate a COMPOSITION PLAN driven by the following emotional trajectory:

  Emotional arc:   {emotional_arc}
  Total duration:  {total_duration_sec} seconds (approximately {approx_bars} bars)
  Instrumentation: {instrumentation}
  Starting key:    {starting_key}

Each stage of the emotional arc becomes one section of the piece. For EACH stage,
generate a complete parameter set:

1. TEMPO MAP: BPM for each section. Transitions between tempi should be gradual
   (rallentando/accelerando) unless a sudden shift is dramatically appropriate.

2. KEY PLAN: The key for each section. Use key relationships that support the
   emotion:
   - Peaceful: major keys, subdominant relationships
   - Anxious: minor keys, chromatic mediants, tritone relationships
   - Crisis: remote keys, enharmonic modulations, diminished/augmented sonorities
   - Resolution: return toward home key via dominant
   - Transcendence: major key, possibly raised from the home key (e.g., C minor piece
     ending in C major or Db major)

3. DYNAMIC PLAN: Dynamic level and trajectory for each section.

4. TEXTURE PLAN: Texture type and density for each section.

5. REGISTER PLAN: Pitch range (low/mid/high, narrow/wide) for each section.

6. CHARACTER and ARTICULATION for each section.

7. SCHEMA SEQUENCES for each section, chosen to support the emotion.

8. CHILLS TRIGGERS: Identify 2-3 moments for peak emotional impact. Layer
   2-3 chills triggers at each (unexpected harmony + crescendo + new timbre, etc.).

Output a single JSON object:
{{
  "form": "through_composed",
  "emotional_arc": ["<stage1>", "<stage2>", ...],
  "home_key": "<key_token>",
  "total_bars": <int>,
  "total_duration_sec": <int>,
  "instrumentation": [<str>, ...],
  "sections": [
    {{
      "emotion": "<emotion_label>",
      "type": "<section_type_token>",
      "key": "<key_token>",
      "bars": <int>,
      "tempo_bpm": <int>,
      "tempo_transition": "<subito|accelerando|rallentando|null>",
      "dynamic": "<dynamic_token>",
      "dynamic_trajectory": "<crescendo|diminuendo|steady|swell>",
      "texture": "<texture_token>",
      "density": "<sparse|moderate|dense|very_dense>",
      "register": "<low|mid|high|full>",
      "register_width": "<narrow|medium|wide>",
      "character": "<character_token>",
      "articulation": "<articulation_token>",
      "modulation_to_next": {{
        "method": "<pivot_chord|chromatic|enharmonic|sequential|none>",
        "relationship": "<key_relationship_token or null>"
      }},
      "schema_sequence": [
        {{"schema": "<schema_token>", "bars": <int>, "local_key": "<key_token>"}}
      ],
      "cadence": "<cadence_token>",
      "chills_trigger": {{
        "active": <bool>,
        "techniques": ["<unexpected_harmony|crescendo|new_timbre|appoggiatura|melodic_descent|enharmonic_shift>"],
        "placement_bar": <int or null>
      }},
      "notes": "<free text>"
    }}
  ],
  "tension_curve": [<float 0.0-1.0 for each section>],
  "notes": "<free text overview>"
}}
"""

def _validate_emotional_arc(output: dict) -> List[str]:
    errors = []
    arc = output.get("emotional_arc", [])
    sections = output.get("sections", [])
    if len(arc) != len(sections):
        errors.append(f"emotional_arc has {len(arc)} stages but there are {len(sections)} sections")

    tension = output.get("tension_curve", [])
    if tension and len(tension) != len(sections):
        errors.append(f"tension_curve length ({len(tension)}) must match sections ({len(sections)})")

    # Check for at least one chills trigger
    chills_count = sum(1 for s in sections if s.get("chills_trigger", {}).get("active"))
    if chills_count < 1:
        errors.append("At least one section should have an active chills_trigger")

    return errors


EMOTIONAL_ARC_TEMPLATE = PromptTemplate(
    name="emotional_arc",
    description="Generates a composition plan from an emotional trajectory, mapping emotions to musical parameters.",
    prompt_text=EMOTIONAL_ARC_PROMPT,
    output_schema={
        "type": "object",
        "required": ["form", "emotional_arc", "home_key", "total_bars", "sections", "tension_curve"],
        "properties": {
            "form": {"type": "string", "enum": ["through_composed"]},
            "emotional_arc": {"type": "array", "items": {"type": "string"}},
            "sections": {"type": "array", "minItems": 2},
            "tension_curve": {"type": "array", "items": {"type": "number", "minimum": 0, "maximum": 1}},
        },
    },
    example_input={
        "emotional_arc": "peaceful -> anxious -> crisis -> resolution -> transcendence",
        "total_duration_sec": 300,
        "approx_bars": 80,
        "instrumentation": '["violin", "viola", "cello", "double_bass"]',
        "starting_key": "F_major",
    },
    example_output={
        "form": "through_composed",
        "emotional_arc": ["peaceful", "anxious", "crisis", "resolution", "transcendence"],
        "home_key": "F_major",
        "total_bars": 80,
        "total_duration_sec": 300,
        "instrumentation": ["violin", "viola", "cello", "double_bass"],
        "sections": [
            {
                "emotion": "peaceful",
                "type": "A_section",
                "key": "F_major",
                "bars": 16,
                "tempo_bpm": 72,
                "tempo_transition": None,
                "dynamic": "p",
                "dynamic_trajectory": "steady",
                "texture": "melody_accomp",
                "density": "sparse",
                "register": "mid",
                "register_width": "narrow",
                "character": "serene",
                "articulation": "legato",
                "modulation_to_next": {"method": "chromatic", "relationship": "to_parallel_minor"},
                "schema_sequence": [
                    {"schema": "romanesca", "bars": 4, "local_key": "F_major"},
                    {"schema": "prinner", "bars": 4, "local_key": "F_major"},
                    {"schema": "fenaroli", "bars": 4, "local_key": "F_major"},
                    {"schema": "quiescenza", "bars": 4, "local_key": "F_major"},
                ],
                "cadence": "PAC",
                "chills_trigger": {"active": False, "techniques": [], "placement_bar": None},
                "notes": "Cello solo melody over sustained viola and bass pedal. Pastoral warmth. Spacious.",
            },
            {
                "emotion": "anxious",
                "type": "B_section",
                "key": "F_minor",
                "bars": 16,
                "tempo_bpm": 96,
                "tempo_transition": "accelerando",
                "dynamic": "mp",
                "dynamic_trajectory": "crescendo",
                "texture": "tremolo",
                "density": "moderate",
                "register": "mid",
                "register_width": "medium",
                "character": "agitated",
                "articulation": "staccato",
                "modulation_to_next": {"method": "chromatic", "relationship": "to_flat_mediant"},
                "schema_sequence": [
                    {"schema": "monte", "bars": 4, "local_key": "F_minor"},
                    {"schema": "fonte", "bars": 4, "local_key": "F_minor"},
                    {"schema": "indugio", "bars": 4, "local_key": "F_minor"},
                    {"schema": "sol_fa_mi", "bars": 4, "local_key": "F_minor"},
                ],
                "cadence": "HC",
                "chills_trigger": {"active": False, "techniques": [], "placement_bar": None},
                "notes": "Tremolo strings. Rising sequences build anxiety. Gradual accelerando and crescendo.",
            },
            {
                "emotion": "crisis",
                "type": "C_section",
                "key": "Db_major",
                "bars": 20,
                "tempo_bpm": 144,
                "tempo_transition": "subito",
                "dynamic": "ff",
                "dynamic_trajectory": "swell",
                "texture": "homophonic",
                "density": "very_dense",
                "register": "full",
                "register_width": "wide",
                "character": "stormy",
                "articulation": "marcato",
                "modulation_to_next": {"method": "enharmonic", "relationship": "to_dominant"},
                "schema_sequence": [
                    {"schema": "monte", "bars": 4, "local_key": "Db_major"},
                    {"schema": "monte", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "fonte", "bars": 4, "local_key": "Db_major"},
                    {"schema": "ponte", "bars": 4, "local_key": "C_major"},
                    {"schema": "sol_fa_mi", "bars": 4, "local_key": "F_major"},
                ],
                "cadence": "evaded",
                "chills_trigger": {
                    "active": True,
                    "techniques": ["unexpected_harmony", "crescendo", "melodic_descent"],
                    "placement_bar": 12,
                },
                "notes": "Climax of the piece. Full fortissimo. Rapid modulations through remote keys. Climax at bar 12 (golden ratio of this section). Evaded cadence drives into resolution.",
            },
            {
                "emotion": "resolution",
                "type": "A_section",
                "key": "F_major",
                "bars": 16,
                "tempo_bpm": 84,
                "tempo_transition": "rallentando",
                "dynamic": "mf",
                "dynamic_trajectory": "diminuendo",
                "texture": "chorale",
                "density": "moderate",
                "register": "mid",
                "register_width": "medium",
                "character": "noble",
                "articulation": "legato",
                "modulation_to_next": {"method": "pivot_chord", "relationship": None},
                "schema_sequence": [
                    {"schema": "romanesca", "bars": 4, "local_key": "F_major"},
                    {"schema": "prinner", "bars": 4, "local_key": "F_major"},
                    {"schema": "fenaroli", "bars": 4, "local_key": "F_major"},
                    {"schema": "comma", "bars": 4, "local_key": "F_major"},
                ],
                "cadence": "PAC",
                "chills_trigger": {
                    "active": True,
                    "techniques": ["enharmonic_shift", "new_timbre"],
                    "placement_bar": 1,
                },
                "notes": "Return to F major feels like homecoming. Chorale texture suggests hymn-like dignity. The shift back to major after the crisis is itself a chills trigger.",
            },
            {
                "emotion": "transcendence",
                "type": "coda",
                "key": "F_major",
                "bars": 12,
                "tempo_bpm": 60,
                "tempo_transition": "rallentando",
                "dynamic": "pp",
                "dynamic_trajectory": "diminuendo",
                "texture": "melody_accomp",
                "density": "sparse",
                "register": "high",
                "register_width": "narrow",
                "character": "serene",
                "articulation": "legato",
                "modulation_to_next": {"method": "none", "relationship": None},
                "schema_sequence": [
                    {"schema": "quiescenza", "bars": 4, "local_key": "F_major"},
                    {"schema": "quiescenza", "bars": 4, "local_key": "F_major"},
                    {"schema": "passo_indietro", "bars": 2, "local_key": "F_major"},
                    {"schema": "comma", "bars": 2, "local_key": "F_major"},
                ],
                "cadence": "plagal",
                "chills_trigger": {
                    "active": True,
                    "techniques": ["appoggiatura", "new_timbre"],
                    "placement_bar": 5,
                },
                "notes": "Ethereal high harmonics on violin. Tonic pedal throughout. Plagal cadence (amen). Dissolves into silence with solo violin.",
            },
        ],
        "tension_curve": [0.15, 0.45, 0.95, 0.40, 0.10],
        "notes": "Five-part arc. Crisis at section 3 (golden ratio of total duration). Return to opening material in resolution creates Wundt-curve familiarity. Transcendence section new material at very low tension.",
    },
    validation_rules=[
        "Number of sections must equal number of emotions in the arc",
        "tension_curve length must equal number of sections",
        "tension_curve values must be between 0.0 and 1.0",
        "At least one section must have active chills_trigger",
        "Chills triggers should layer 2-3 techniques",
        "All key, cadence, schema, texture, character tokens must be valid",
        "Section bars must sum to total_bars",
        "Tempo values must be in range 20-300",
    ],
    _validators=COMMON_VALIDATORS + [_validate_emotional_arc],
)


# =============================================================================
# TEMPLATE 5: STYLE EMULATION
# =============================================================================

STYLE_EMULATION_PROMPT = """\
Generate a STYLE PARAMETER PROFILE for composing in the style of: {composer}

Analyze this composer's characteristic style and produce a comprehensive parameter
set that the Realizer can use to generate music in this style.

Cover ALL of the following dimensions:

1. HARMONIC VOCABULARY: What chords does this composer favor? Secondary dominants?
   Augmented 6ths? Chromatic mediants? Pedal points? Typical progression patterns.

2. MELODIC PREFERENCES: Interval distribution (% steps, 3rds, leaps). Preferred
   contour shapes. Use of chromaticism. Ornament types. Range tendencies.

3. PHRASE STRUCTURE: Typical phrase lengths. Period vs. sentence preference.
   Extension techniques. Elision. Asymmetric phrasing?

4. RHYTHMIC CHARACTER: Preferred time signatures. Typical note values.
   Syncopation frequency. Hemiola usage. Tempo ranges.

5. TEXTURE PREFERENCES: Favorite textures. Accompaniment patterns.
   Density. Counterpoint usage. Voicing preferences.

6. FORMAL TENDENCIES: Preferred forms. How they handle transitions.
   Development techniques. Coda treatment.

7. EXPRESSIVE CHARACTERISTICS: Dynamic range. Articulation preferences.
   Rubato/flexibility. Register usage.

8. SCHEMA PREFERENCES: Which galant schemata does this composer favor?
   How does this composer typically open pieces? Handle cadences?

Output a single JSON object:
{{
  "composer": "<name>",
  "era": "<baroque|classical|romantic|impressionist>",
  "date_range": "<birth-death years>",
  "harmonic_vocabulary": {{
    "primary_chords": ["<roman_numerals>"],
    "secondary_dominants": <bool>,
    "augmented_sixths": "<none|rare|occasional|frequent>",
    "chromatic_mediants": "<none|rare|occasional|frequent>",
    "neapolitan": "<none|rare|occasional|frequent>",
    "pedal_points": "<none|rare|occasional|frequent>",
    "typical_progressions": ["<progression strings>"],
    "dissonance_level": <float 0.0-1.0>,
    "modulation_frequency": "<rare|moderate|frequent|constant>",
    "modulation_distance": "<close|medium|remote>",
    "notes": "<free text>"
  }},
  "melodic_preferences": {{
    "stepwise_percent": <int>,
    "thirds_percent": <int>,
    "leaps_percent": <int>,
    "chromaticism": "<none|rare|moderate|heavy>",
    "preferred_contours": ["<arch|descending|ascending|wavelike>"],
    "ornament_types": ["<trill|mordent|turn|appoggiatura|acciaccatura|none>"],
    "typical_range_semitones": <int>,
    "notes": "<free text>"
  }},
  "phrase_structure": {{
    "typical_length_bars": [<int>, ...],
    "period_vs_sentence": "<period|sentence|mixed>",
    "extensions": "<none|rare|common>",
    "elision": "<none|rare|common>",
    "asymmetry": "<none|rare|common>",
    "notes": "<free text>"
  }},
  "rhythmic_character": {{
    "preferred_time_signatures": ["<str>"],
    "typical_note_values": ["<whole|half|quarter|eighth|sixteenth|triplet>"],
    "syncopation_rate": <float 0.0-1.0>,
    "hemiola": "<none|rare|occasional|frequent>",
    "tempo_range_bpm": [<min>, <max>],
    "rubato": "<none|slight|moderate|heavy>",
    "notes": "<free text>"
  }},
  "texture_preferences": {{
    "primary_textures": ["<texture_token>"],
    "accompaniment_patterns": ["<alberti_bass|murky_bass|arpeggio|block_chords|tremolo|ostinato|other>"],
    "typical_density": "<sparse|moderate|dense|variable>",
    "counterpoint_usage": "<none|rare|moderate|extensive>",
    "voicing_style": "<close|open|mixed>",
    "notes": "<free text>"
  }},
  "formal_tendencies": {{
    "preferred_forms": ["<form_token>"],
    "transition_style": "<smooth|dramatic|abrupt>",
    "development_techniques": ["<fragmentation|sequence|inversion|augmentation|diminution|reharmonization>"],
    "coda_style": "<brief|extended|none>",
    "notes": "<free text>"
  }},
  "expressive_characteristics": {{
    "dynamic_range": "<narrow_pp_mp|moderate_p_f|wide_pp_ff|extreme_ppp_fff>",
    "preferred_articulations": ["<articulation_token>"],
    "register_usage": "<low|mid|high|full>",
    "surprise_rate": <float 0.0-1.0>,
    "notes": "<free text>"
  }},
  "schema_preferences": {{
    "favored_opening_schemata": ["<schema_token>"],
    "favored_continuation_schemata": ["<schema_token>"],
    "favored_cadential_schemata": ["<schema_token>"],
    "cadence_preferences": {{
      "PAC_frequency": <float 0.0-1.0>,
      "HC_frequency": <float 0.0-1.0>,
      "DC_frequency": <float 0.0-1.0>,
      "evaded_frequency": <float 0.0-1.0>
    }},
    "notes": "<free text>"
  }},
  "realizer_overrides": {{
    "consonance_ratio": <float 0.0-1.0>,
    "voice_leading_strictness": "<strict|moderate|free>",
    "parallel_fifths_tolerance": <bool>,
    "humanization_amount": <float 0.0-1.0>,
    "notes": "<free text>"
  }}
}}
"""

STYLE_EMULATION_TEMPLATE = PromptTemplate(
    name="style_emulation",
    description="Generates a comprehensive style parameter profile for a named composer.",
    prompt_text=STYLE_EMULATION_PROMPT,
    output_schema={
        "type": "object",
        "required": ["composer", "era", "harmonic_vocabulary", "melodic_preferences",
                      "phrase_structure", "rhythmic_character", "texture_preferences",
                      "formal_tendencies", "expressive_characteristics", "schema_preferences",
                      "realizer_overrides"],
    },
    example_input={"composer": "Mozart"},
    example_output={
        "composer": "Mozart",
        "era": "classical",
        "date_range": "1756-1791",
        "harmonic_vocabulary": {
            "primary_chords": ["I", "IV", "V", "V7", "vi", "ii", "ii6", "viio6", "I6"],
            "secondary_dominants": True,
            "augmented_sixths": "occasional",
            "chromatic_mediants": "rare",
            "neapolitan": "occasional",
            "pedal_points": "occasional",
            "typical_progressions": [
                "I-IV-V-I", "I-ii6-V-I", "I-vi-IV-V-I",
                "I-V/V-V-I", "i-iv-V-i",
            ],
            "dissonance_level": 0.25,
            "modulation_frequency": "moderate",
            "modulation_distance": "close",
            "notes": "Clean, diatonic harmony. Secondary dominants common but chromatic adventurism rare outside development sections. Perfect balance of simplicity and sophistication.",
        },
        "melodic_preferences": {
            "stepwise_percent": 65,
            "thirds_percent": 20,
            "leaps_percent": 15,
            "chromaticism": "rare",
            "preferred_contours": ["arch", "wavelike"],
            "ornament_types": ["trill", "turn", "appoggiatura", "acciaccatura"],
            "typical_range_semitones": 16,
            "notes": "Singing, vocal-like melodies. Grace notes and trills as expressive decoration. Gap-fill principle strictly observed.",
        },
        "phrase_structure": {
            "typical_length_bars": [4, 8],
            "period_vs_sentence": "mixed",
            "extensions": "common",
            "elision": "occasional",
            "asymmetry": "rare",
            "notes": "Clean 4+4 and 8+8 structures. Occasionally extends phrases by 1-2 bars for expressive effect.",
        },
        "rhythmic_character": {
            "preferred_time_signatures": ["4/4", "3/4", "2/4", "6/8"],
            "typical_note_values": ["eighth", "sixteenth", "quarter"],
            "syncopation_rate": 0.10,
            "hemiola": "occasional",
            "tempo_range_bpm": [60, 160],
            "rubato": "none",
            "notes": "Rhythmic clarity. Alberti bass provides steady pulse. Minimal syncopation compared to Beethoven.",
        },
        "texture_preferences": {
            "primary_textures": ["melody_accomp", "homophonic", "polyphonic"],
            "accompaniment_patterns": ["alberti_bass", "arpeggio", "block_chords"],
            "typical_density": "moderate",
            "counterpoint_usage": "moderate",
            "voicing_style": "close",
            "notes": "Melody-and-accompaniment dominates, but contrapuntal passages appear in development sections and finales. Transparent textures.",
        },
        "formal_tendencies": {
            "preferred_forms": ["sonata", "rondo", "theme_and_variations", "minuet_and_trio"],
            "transition_style": "smooth",
            "development_techniques": ["fragmentation", "sequence", "reharmonization"],
            "coda_style": "brief",
            "notes": "Textbook sonata forms. Transitions are elegant, never forced. Development sections explore but don't wander. Short codas.",
        },
        "expressive_characteristics": {
            "dynamic_range": "moderate_p_f",
            "preferred_articulations": ["legato", "staccato", "trill", "turn"],
            "register_usage": "mid",
            "surprise_rate": 0.18,
            "notes": "Elegance over extremity. Surprises come as witty harmonic twists (deceptive cadences, unexpected modulations) rather than dynamic shocks.",
        },
        "schema_preferences": {
            "favored_opening_schemata": ["do_re_mi", "cudworth", "jupiter"],
            "favored_continuation_schemata": ["prinner", "monte", "fonte", "romanesca"],
            "favored_cadential_schemata": ["sol_fa_mi", "comma", "passo_indietro"],
            "cadence_preferences": {
                "PAC_frequency": 0.55,
                "HC_frequency": 0.30,
                "DC_frequency": 0.10,
                "evaded_frequency": 0.05,
            },
            "notes": "Mozart is the galant schema composer par excellence. Do-Re-Mi and Prinner are ubiquitous. Jupiter schema named after his Symphony No. 41.",
        },
        "realizer_overrides": {
            "consonance_ratio": 0.82,
            "voice_leading_strictness": "strict",
            "parallel_fifths_tolerance": False,
            "humanization_amount": 0.15,
            "notes": "Strict voice leading. No parallel fifths. Low humanization (Mozart's writing is precise).",
        },
    },
    validation_rules=[
        "composer must be a non-empty string",
        "era must be one of: baroque, classical, romantic, impressionist",
        "All percentage fields must sum appropriately (stepwise + thirds + leaps = 100)",
        "All float fields must be between 0.0 and 1.0",
        "Cadence preference frequencies should sum to approximately 1.0",
        "All schema, texture, articulation tokens must be from valid sets",
        "tempo_range_bpm must be [min, max] with min < max",
    ],
    _validators=COMMON_VALIDATORS,
)


# =============================================================================
# TEMPLATE 6: FREE COMPOSITION
# =============================================================================

FREE_COMPOSITION_PROMPT = """\
Generate a COMPLETE COMPOSITION PLAN from the following natural-language description:

"{description}"

You must interpret this description and produce a fully specified plan that the
Realizer can compile into MIDI. Make all musical decisions that the description
leaves unspecified, choosing options that best serve the described vision.

Your plan must include:

1. FORM: Choose the most appropriate form type. If the description implies a
   narrative arc, use through_composed. If it implies repetition, use ternary
   or rondo. If it implies development of an idea, use sonata.

2. KEY & MODULATION PLAN: Choose a home key and plan modulations that serve
   the emotional trajectory.

3. TEMPO & METER: Choose tempo and time signature.

4. INSTRUMENTATION: Infer from the description, or choose idiomatically.

5. SECTION-BY-SECTION PLAN: Break the description into sections. Each section
   needs all standard parameters (key, bars, character, texture, dynamics,
   schema sequence, cadence).

6. EMOTIONAL ARC: Even if not explicitly stated, infer a tension curve.

7. CHILLS MOMENTS: Identify the most powerful moment and engineer chills
   triggers for it.

Output a single JSON object with this structure:
{{
  "title": "<inferred title>",
  "form": "<form_token>",
  "home_key": "<key_token>",
  "tempo_bpm": <int>,
  "time_signature": "<str>",
  "character": "<character_token>",
  "instrumentation": [<str>, ...],
  "total_bars": <int>,
  "total_duration_sec": <int>,
  "interpretation": "<1-2 sentence summary of how you interpreted the description>",
  "sections": [
    {{
      "name": "<descriptive section name>",
      "type": "<section_type_token>",
      "key": "<key_token>",
      "bars": <int>,
      "tempo_bpm": <int>,
      "character": "<character_token>",
      "texture": "<texture_token>",
      "dynamic": "<dynamic_token>",
      "dynamic_trajectory": "<crescendo|diminuendo|steady|swell>",
      "articulation": "<articulation_token>",
      "register": "<low|mid|high|full>",
      "schema_sequence": [
        {{"schema": "<schema_token>", "bars": <int>, "local_key": "<key_token>"}}
      ],
      "cadence": "<cadence_token>",
      "modulation_to_next": {{
        "method": "<pivot_chord|chromatic|enharmonic|sequential|none>",
        "relationship": "<key_relationship_token or null>"
      }},
      "chills_trigger": {{
        "active": <bool>,
        "techniques": [<str>],
        "placement_bar": <int or null>
      }},
      "notes": "<free text: interpretation details, performance notes>"
    }}
  ],
  "tension_curve": [<float per section>],
  "golden_ratio_climax_bar": <int>,
  "notes": "<free text: overall compositional strategy>"
}}
"""

def _validate_free_composition(output: dict) -> List[str]:
    errors = []
    sections = output.get("sections", [])
    tension = output.get("tension_curve", [])
    if tension and len(tension) != len(sections):
        errors.append(f"tension_curve length ({len(tension)}) must match sections ({len(sections)})")
    # Check golden ratio climax
    total = output.get("total_bars", 0)
    climax = output.get("golden_ratio_climax_bar")
    if total and climax:
        expected = round(total * 0.618)
        if abs(climax - expected) > total * 0.1:
            errors.append(
                f"golden_ratio_climax_bar={climax} deviates significantly from "
                f"expected ~{expected} (total_bars={total} * 0.618)"
            )
    return errors


FREE_COMPOSITION_TEMPLATE = PromptTemplate(
    name="free_composition",
    description="Generates a complete composition plan from any natural-language description.",
    prompt_text=FREE_COMPOSITION_PROMPT,
    output_schema={
        "type": "object",
        "required": ["title", "form", "home_key", "tempo_bpm", "instrumentation",
                      "total_bars", "sections", "tension_curve"],
        "properties": {
            "title": {"type": "string"},
            "form": {"type": "string"},
            "home_key": {"type": "string"},
            "sections": {"type": "array", "minItems": 1},
            "tension_curve": {"type": "array", "items": {"type": "number"}},
            "golden_ratio_climax_bar": {"type": "integer"},
        },
    },
    example_input={
        "description": "A mysterious nocturne that starts with a solo cello melody, builds to a full string orchestra climax, then dissolves into silence",
    },
    example_output={
        "title": "Nocturne for Strings",
        "form": "ternary",
        "home_key": "Eb_minor",
        "tempo_bpm": 66,
        "time_signature": "6/8",
        "character": "mysterious",
        "instrumentation": ["violin_1", "violin_2", "viola", "cello", "double_bass"],
        "total_bars": 64,
        "total_duration_sec": 240,
        "interpretation": "A three-part nocturne in Eb minor: solo cello exposition of a dark, yearning theme; a central climax where the full string section transforms the theme into a passionate outpouring; and a fragmented dissolution where the theme evaporates into harmonics and silence.",
        "sections": [
            {
                "name": "Solo cello - the mystery",
                "type": "A_section",
                "key": "Eb_minor",
                "bars": 24,
                "tempo_bpm": 66,
                "character": "mysterious",
                "texture": "melody_accomp",
                "dynamic": "pp",
                "dynamic_trajectory": "crescendo",
                "articulation": "legato",
                "register": "low",
                "schema_sequence": [
                    {"schema": "romanesca", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "fenaroli", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "prinner", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "monte", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "fonte", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "indugio", "bars": 4, "local_key": "Eb_minor"},
                ],
                "cadence": "HC",
                "modulation_to_next": {"method": "chromatic", "relationship": "to_relative_major"},
                "chills_trigger": {"active": False, "techniques": [], "placement_bar": None},
                "notes": "Solo cello for first 8 bars. Viola enters with sustained pedal at bar 9. Second violin adds a counter-melody at bar 17. Slow build of forces.",
            },
            {
                "name": "Climax - the revelation",
                "type": "B_section",
                "key": "Gb_major",
                "bars": 16,
                "tempo_bpm": 80,
                "character": "majestic",
                "texture": "homophonic",
                "dynamic": "ff",
                "dynamic_trajectory": "swell",
                "articulation": "marcato",
                "register": "full",
                "schema_sequence": [
                    {"schema": "jupiter", "bars": 4, "local_key": "Gb_major"},
                    {"schema": "monte", "bars": 4, "local_key": "Gb_major"},
                    {"schema": "prinner", "bars": 4, "local_key": "Gb_major"},
                    {"schema": "sol_fa_mi", "bars": 2, "local_key": "Eb_minor"},
                    {"schema": "comma", "bars": 2, "local_key": "Eb_minor"},
                ],
                "cadence": "PAC",
                "modulation_to_next": {"method": "pivot_chord", "relationship": "to_parallel_minor"},
                "chills_trigger": {
                    "active": True,
                    "techniques": ["crescendo", "new_timbre", "unexpected_harmony"],
                    "placement_bar": 40,
                },
                "notes": "Full string orchestra in fortissimo. Theme transformed: what was mysterious becomes triumphant. Climax at bar 40 (golden ratio of 64). Double bass enters for the first time here as a chills-trigger timbre change.",
            },
            {
                "name": "Dissolution - into silence",
                "type": "A_section",
                "key": "Eb_minor",
                "bars": 24,
                "tempo_bpm": 54,
                "character": "serene",
                "texture": "arpeggio",
                "dynamic": "ppp",
                "dynamic_trajectory": "diminuendo",
                "articulation": "legato",
                "register": "high",
                "schema_sequence": [
                    {"schema": "quiescenza", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "romanesca", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "quiescenza", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "fenaroli", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "quiescenza", "bars": 4, "local_key": "Eb_minor"},
                    {"schema": "passo_indietro", "bars": 2, "local_key": "Eb_minor"},
                    {"schema": "comma", "bars": 2, "local_key": "Eb_minor"},
                ],
                "cadence": "plagal",
                "modulation_to_next": {"method": "none", "relationship": None},
                "chills_trigger": {
                    "active": True,
                    "techniques": ["appoggiatura", "melodic_descent"],
                    "placement_bar": 52,
                },
                "notes": "Instruments drop out one by one. Melody fragments into isolated notes. Final bars: solo cello harmonic on Eb, fading to niente. Mirrors the opening in reverse.",
            },
        ],
        "tension_curve": [0.30, 0.95, 0.10],
        "golden_ratio_climax_bar": 40,
        "notes": "Arch form: quiet-loud-quiet. The golden-ratio climax falls at bar 40 of 64. The dissolution section mirrors the opening (Wundt curve: return to familiarity). The shift from Eb minor to Gb major (relative major) for the climax is both surprising and warm. Plagal cadence at the end suggests acceptance rather than resolution.",
    },
    validation_rules=[
        "title must be a non-empty string",
        "form must be a valid form token",
        "home_key must be a valid key token",
        "All sections must have required fields: type, key, bars, character, texture, dynamic, schema_sequence, cadence",
        "Section bars must sum to total_bars",
        "golden_ratio_climax_bar should be approximately total_bars * 0.618",
        "tension_curve length must equal number of sections",
        "At least one section must have active chills_trigger",
        "All tokens must be from valid vocabulary sets",
    ],
    _validators=COMMON_VALIDATORS + [_validate_free_composition],
)


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

TEMPLATES: Dict[str, PromptTemplate] = {
    "sonata_exposition": SONATA_EXPOSITION_TEMPLATE,
    "theme_and_variations": THEME_AND_VARIATIONS_TEMPLATE,
    "fugue_exposition": FUGUE_EXPOSITION_TEMPLATE,
    "emotional_arc": EMOTIONAL_ARC_TEMPLATE,
    "style_emulation": STYLE_EMULATION_TEMPLATE,
    "free_composition": FREE_COMPOSITION_TEMPLATE,
}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_prompt(template_name: str, **kwargs) -> str:
    """
    Get a fully formatted prompt ready to send to Claude.

    Usage:
        prompt = get_prompt("sonata_exposition",
            home_key="C_minor",
            character="heroic",
            tempo_bpm=132,
            time_signature="4/4",
            instrumentation='["piano"]',
        )
    """
    if template_name not in TEMPLATES:
        raise ValueError(
            f"Unknown template: {template_name}. "
            f"Available: {list(TEMPLATES.keys())}"
        )
    return TEMPLATES[template_name].format_prompt(**kwargs)


def validate_plan(template_name: str, plan: dict) -> List[str]:
    """
    Validate a JSON plan against its template's rules.
    Returns a list of error strings (empty = valid).

    Usage:
        plan = json.loads(claude_response)
        errors = validate_plan("sonata_exposition", plan)
        if errors:
            print("Plan validation failed:", errors)
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    return TEMPLATES[template_name].validate_output(plan)


def send_to_claude(
    template_name: str,
    client,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8192,
    **kwargs,
) -> dict:
    """
    Complete pipeline: format prompt, send to Claude, parse and validate response.

    Returns the parsed JSON plan dict.
    Raises ValueError if response is not valid JSON or fails validation.

    Usage:
        import anthropic
        client = anthropic.Anthropic()
        plan = send_to_claude("sonata_exposition", client,
            home_key="C_minor", character="heroic",
            tempo_bpm=132, time_signature="4/4",
            instrumentation='["piano"]',
        )
    """
    prompt = get_prompt(template_name, **kwargs)
    response = client.messages.create(
        model=model,
        system=MASTER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )

    response_text = response.content[0].text.strip()

    # Strip markdown code fences if Claude included them despite instructions
    if response_text.startswith("```"):
        response_text = re.sub(r"^```(?:json)?\n?", "", response_text)
        response_text = re.sub(r"\n?```$", "", response_text)

    try:
        plan = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude response is not valid JSON: {e}\nRaw: {response_text[:500]}")

    errors = validate_plan(template_name, plan)
    if errors:
        raise ValueError(f"Plan validation failed with {len(errors)} error(s):\n" +
                         "\n".join(f"  - {e}" for e in errors))

    return plan


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 72)
    print("  PROMPT TEMPLATE LIBRARY — Self-Test")
    print("=" * 72)

    # Test 1: All templates exist and have required fields
    for name, tmpl in TEMPLATES.items():
        assert tmpl.name == name, f"Name mismatch: {tmpl.name} != {name}"
        assert len(tmpl.prompt_text) > 100, f"{name}: prompt too short"
        assert tmpl.output_schema, f"{name}: missing output_schema"
        assert tmpl.example_input, f"{name}: missing example_input"
        assert tmpl.example_output, f"{name}: missing example_output"
        assert tmpl.validation_rules, f"{name}: missing validation_rules"
        print(f"  [PASS] {name}: structure OK ({len(tmpl.prompt_text)} chars)")

    # Test 2: Example outputs pass their own validators
    for name, tmpl in TEMPLATES.items():
        errors = tmpl.validate_output(tmpl.example_output)
        if errors:
            print(f"  [WARN] {name}: example output has validation issues:")
            for e in errors:
                print(f"         - {e}")
        else:
            print(f"  [PASS] {name}: example output validates clean")

    # Test 3: Prompt formatting works
    try:
        p = get_prompt("sonata_exposition",
                       home_key="C_minor", character="heroic",
                       tempo_bpm=132, time_signature="4/4",
                       instrumentation='["piano"]')
        assert "C_minor" in p
        print(f"  [PASS] sonata_exposition: prompt formatting OK")
    except Exception as e:
        print(f"  [FAIL] sonata_exposition formatting: {e}")

    # Test 4: Master system prompt is substantial
    assert len(MASTER_SYSTEM_PROMPT) > 3000, "Master prompt too short"
    print(f"  [PASS] MASTER_SYSTEM_PROMPT: {len(MASTER_SYSTEM_PROMPT)} chars")

    # Summary
    total_chars = sum(len(t.prompt_text) for t in TEMPLATES.values()) + len(MASTER_SYSTEM_PROMPT)
    print(f"\n  Total prompt text: {total_chars:,} characters across {len(TEMPLATES)} templates + master prompt")
    print(f"  Total example output JSON: {sum(len(json.dumps(t.example_output)) for t in TEMPLATES.values()):,} characters")
    print("=" * 72)
