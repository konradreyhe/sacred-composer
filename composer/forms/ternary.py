"""Ternary (ABA') form plan builder."""

from __future__ import annotations

from typing import List

from SYSTEM_ARCHITECTURE import (
    SectionIR, SubsectionIR, SectionType, SubsectionType,
    KeyToken, CharacterToken, TextureToken, CadenceType,
)
from composer.parser import _key_is_minor, _relative_major, _subdominant_key


def _build_ternary_plan(home_key: KeyToken, total_bars: int,
                        character: CharacterToken) -> List[SectionIR]:
    """
    Build an ABA' ternary form with clear section boundaries.

    Structure:
      - A:  8 bars in tonic, memorable theme, PAC cadence
      - B:  8-16 bars in contrasting key, distinct character, HC cadence
      - A': 8 bars in tonic, literal replay of A melody, PAC cadence

    The A sections are tagged with notes="ternary_a_section" so the melody
    pass can replay them identically (like rondo refrains), boosting the
    autocorrelation / phrase_boundaries metric.
    """
    # --- Key plan: B goes to a CONTRASTING key ---
    is_minor = _key_is_minor(home_key)
    if is_minor:
        # Minor -> relative major (e.g. D minor -> F major)
        b_key = _relative_major(home_key)
    else:
        # Major -> subdominant (e.g. D major -> G major) for clear contrast
        b_key = _subdominant_key(home_key)

    # --- Bar distribution: A=8, B=8-16, A'=8 ---
    a_bars = 8
    a2_bars = 8
    # B gets whatever remains, clamped to 8-16
    b_bars = max(8, min(16, total_bars - a_bars - a2_bars))
    # If total_bars is very small, scale down A sections
    if total_bars < 24:
        a_bars = max(4, total_bars // 3)
        a2_bars = a_bars
        b_bars = max(4, total_bars - a_bars - a2_bars)
    # Adjust remainder into B
    diff = total_bars - (a_bars + b_bars + a2_bars)
    b_bars += diff
    b_bars = max(4, b_bars)

    # --- Contrasting character for B ---
    if character in (CharacterToken.SERENE, CharacterToken.LYRICAL,
                     CharacterToken.TENDER, CharacterToken.PASTORAL):
        b_character = CharacterToken.AGITATED
    elif character in (CharacterToken.HEROIC, CharacterToken.TRIUMPHANT,
                       CharacterToken.MAJESTIC):
        b_character = CharacterToken.LYRICAL
    else:
        b_character = CharacterToken.LYRICAL

    # --- Build sections ---
    # A: First statement (tagged for replay)
    a_section = SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=a_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
                notes="ternary_a_section",
            ),
        ],
        key_path=[home_key],
    )

    # B: Contrasting middle (different key, character, texture)
    b_section = SectionIR(
        type=SectionType.B_SECTION, key=b_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.S_THEME, key=b_key,
                bars=b_bars, character=b_character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.HC,
                notes="ternary_b_section",
            ),
        ],
        key_path=[b_key],
    )

    # A': Return (tagged for literal replay of A melody)
    a2_section = SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=a2_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
                notes="ternary_a_section",
            ),
        ],
        key_path=[home_key],
    )
    return [a_section, b_section, a2_section]
