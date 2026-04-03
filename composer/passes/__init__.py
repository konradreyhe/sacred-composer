"""9-pass composition pipeline modules."""

from composer.passes.pass_1_plan import pass_1_plan
from composer.passes.pass_2_schema import pass_2_schema, pass_2_schema_fugue, SCHEMA_AFFINITIES
from composer.passes.pass_3_harmony import pass_3_harmony
from composer.passes.pass_4_melody import (
    pass_4_melody, pass_4_melody_fugue,
    _apply_rondo_refrain_replay, _apply_ternary_refrain_replay,
    _build_subsection_bar_ranges,
)
from composer.passes.pass_5_counterpoint import pass_5_counterpoint
from composer.passes.pass_6_orchestration import (
    pass_6_orchestration, pass_6_orchestration_fugue,
    _smooth_section_transitions, pass_6b_phrase_breathing,
)
from composer.passes.pass_7_expression import pass_7_expression, CHARACTER_EXPRESSION
from composer.passes.pass_8_humanization import pass_8_humanization
from composer.passes.pass_9_validation import pass_9_validation, ValidationReport

__all__ = [
    "pass_1_plan",
    "pass_2_schema", "pass_2_schema_fugue", "SCHEMA_AFFINITIES",
    "pass_3_harmony",
    "pass_4_melody", "pass_4_melody_fugue",
    "_apply_rondo_refrain_replay", "_apply_ternary_refrain_replay",
    "_build_subsection_bar_ranges",
    "pass_5_counterpoint",
    "pass_6_orchestration", "pass_6_orchestration_fugue",
    "_smooth_section_transitions", "pass_6b_phrase_breathing",
    "pass_7_expression", "CHARACTER_EXPRESSION",
    "pass_8_humanization",
    "pass_9_validation", "ValidationReport",
]
