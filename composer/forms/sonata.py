"""Sonata exposition form plan builder."""

from __future__ import annotations

from typing import List

from SYSTEM_ARCHITECTURE import (
    SectionIR, SubsectionIR, SectionType, SubsectionType,
    KeyToken, CharacterToken, TextureToken, CadenceType,
)
from composer.parser import _dominant_key


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
