"""PASS 1: Plan (Text -> FormIR)."""

from __future__ import annotations

import logging
from typing import Optional

_log = logging.getLogger(__name__)

from SYSTEM_ARCHITECTURE import FormIR, FormType
from composer.parser import (
    _KEY_TO_M21, MotivicEngine, SeedMotif,
    _current_seed_motif,
)
from composer.forms import (
    _build_sonata_exposition_plan, _build_ternary_plan,
    _build_theme_and_variations_plan, _build_rondo_plan,
    _build_fugue_plan,
)
import composer.parser as _parser_module
from sacred_composer.constants import PHI_INVERSE


def pass_1_plan(parsed: dict) -> FormIR:
    """
    PASS 1: Convert parsed prompt into a FormIR (Level 1).
    Creates the formal structure with sections, keys, bar counts.
    """
    form = parsed["form"]
    home_key = parsed["home_key"]
    total_bars = parsed["total_bars"]
    character = parsed["character"]

    if form == FormType.FUGUE:
        sections = _build_fugue_plan(
            home_key, total_bars, character,
            num_voices=parsed.get("fugue_voices", 3))
    elif form == FormType.SONATA:
        sections = _build_sonata_exposition_plan(home_key, total_bars, character)
    elif form == FormType.THEME_AND_VARIATIONS:
        sections = _build_theme_and_variations_plan(
            home_key, total_bars, character, parsed.get("num_variations", 3))
    elif form == FormType.RONDO:
        sections = _build_rondo_plan(home_key, total_bars, character)
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
    climax_bar = round(actual_bars * PHI_INVERSE)
    _log.info(f"  [Plan] Golden-ratio climax target: bar {climax_bar}/{actual_bars}")

    # Generate seed motif for motivic development
    m21_key_str = _KEY_TO_M21.get(home_key, "C")
    _parser_module._current_seed_motif = MotivicEngine.generate_seed(m21_key_str)
    _log.info(f"  [Plan] Seed motif: {len(_parser_module._current_seed_motif.rhythm)} notes, "
          f"intervals={_parser_module._current_seed_motif.intervals}, "
          f"rhythm={_parser_module._current_seed_motif.rhythm}")

    return form_ir
