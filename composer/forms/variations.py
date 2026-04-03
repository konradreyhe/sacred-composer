"""Theme and Variations form plan builder."""

from __future__ import annotations

from typing import List

from SYSTEM_ARCHITECTURE import (
    SectionIR, SubsectionIR, SectionType, SubsectionType,
    KeyToken, CharacterToken, TextureToken, CadenceType,
)


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
