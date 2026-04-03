"""
COMPOSER PACKAGE -- Complete Integrated Composition Pipeline
=============================================================
End-to-end system: text prompt -> structured plan -> 9 compiler passes -> MIDI file.

Public API:
    from composer import compose, compose_suite

Usage:
    python -m composer
    python -m composer "A piano sonata exposition in C minor, heroic character, 40 bars"

Install:
    pip install music21 midiutil numpy
"""

from composer.pipeline import compose, compose_suite
from composer.parser import parse_prompt
from composer.passes.pass_1_plan import pass_1_plan
from composer.passes.pass_9_validation import ValidationReport

# Re-export everything that was previously importable from the monolithic composer.py
from composer.pipeline import (
    export_midi,
    fix_augmented_intervals,
    fix_leading_tone_resolution,
    fix_seventh_resolution,
    fix_leap_recovery,
    fix_voice_crossing,
    mark_cadence_positions,
    print_quality_report,
)
from composer.parser import (
    MIDI_PROGRAMS,
    INSTRUMENT_RANGES,
    SAMPLE_PROMPTS,
    SeedMotif,
    MotivicEngine,
    _KEY_MAP,
    _KEY_TO_M21,
    _CHARACTER_MAP,
    _INST_VOICE_ORDER,
    _key_is_minor,
    _relative_major,
    _dominant_key,
    _subdominant_key,
    _submediant_key,
    _snap_to_scale,
)
from composer.passes import (
    pass_2_schema,
    pass_2_schema_fugue,
    pass_3_harmony,
    pass_4_melody,
    pass_4_melody_fugue,
    pass_5_counterpoint,
    pass_6_orchestration,
    pass_6_orchestration_fugue,
    pass_7_expression,
    pass_8_humanization,
    pass_9_validation,
    SCHEMA_AFFINITIES,
    CHARACTER_EXPRESSION,
    _apply_rondo_refrain_replay,
    _apply_ternary_refrain_replay,
    _build_subsection_bar_ranges,
    _smooth_section_transitions,
    pass_6b_phrase_breathing,
)
from composer.helpers import (
    generate_1f_noise,
    phyllotaxis_interval,
    flocking_voice_force,
)
from composer.forms import (
    _build_sonata_exposition_plan,
    _build_fugue_plan,
    _build_rondo_plan,
    _build_ternary_plan,
    _build_theme_and_variations_plan,
    FugueSubject,
    _generate_fugue_subject,
    _build_fugue_episode_sequence,
    _get_fugue_voice_ranges,
    _fugue_start_pitch,
)


__all__ = [
    "compose",
    "compose_suite",
    "parse_prompt",
    "pass_1_plan",
    "ValidationReport",
]
