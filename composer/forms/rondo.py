"""Rondo (ABACA) form plan builder."""

from __future__ import annotations

from typing import List

from SYSTEM_ARCHITECTURE import (
    SectionIR, SubsectionIR, SectionType, SubsectionType,
    KeyToken, CharacterToken, TextureToken, CadenceType,
)
from composer.parser import (
    _key_is_minor, _dominant_key, _submediant_key, _subdominant_key,
)


def _build_rondo_plan(home_key: KeyToken, total_bars: int,
                      character: CharacterToken) -> List[SectionIR]:
    """
    Build an ABACA rondo form:
      - A (refrain):   8 bars in tonic, memorable theme, PAC ending
      - B (episode 1): 8 bars in dominant (major) or relative major (minor)
      - A (return 1):  8 bars refrain in tonic (can be abbreviated to 4)
      - C (episode 2): 8 bars in submediant/subdominant, most contrasting
      - A (final):     8 bars final refrain in tonic, possibly extended with coda

    The A sections are tagged with notes="rondo_refrain" so the melody pass
    can replay them identically, boosting autocorrelation / phrase_boundaries.
    """
    is_minor = _key_is_minor(home_key)

    # Key plan: B goes to dominant/relative major; C to submediant or subdominant
    b_key = _dominant_key(home_key)
    # C section: more distant key -- try submediant first, fall back to subdominant
    c_key = _submediant_key(home_key)
    if c_key == home_key:
        c_key = _subdominant_key(home_key)

    # --- Bar distribution ---
    # 5 sections, roughly equal; A sections are 8 bars each (minimum 4)
    # With 40 bars: A=8, B=8, A=8, C=8, A=8
    # With fewer bars, abbreviate the middle A and adjust
    if total_bars >= 40:
        a_bars = 8
        b_bars = max(4, round((total_bars - 3 * a_bars) * 0.5))
        c_bars = max(4, total_bars - 3 * a_bars - b_bars)
    elif total_bars >= 28:
        a_bars = max(4, round(total_bars * 0.2))
        b_bars = max(4, round(total_bars * 0.2))
        c_bars = max(4, round(total_bars * 0.2))
        # Middle A can be abbreviated
        a_mid_bars = max(4, total_bars - 2 * a_bars - b_bars - c_bars)
    else:
        # Compact rondo
        a_bars = max(4, total_bars // 5)
        b_bars = max(4, a_bars)
        c_bars = max(4, a_bars)

    # Compute specific section sizes
    a1_bars = a_bars
    b1_bars = b_bars if total_bars >= 40 else max(4, round(total_bars * 0.2))
    # Middle A: abbreviated if tight on space
    a2_bars = a_bars if total_bars >= 40 else max(4, a_bars - 2)
    c1_bars = c_bars if total_bars >= 40 else max(4, round(total_bars * 0.2))
    a3_bars = max(4, total_bars - a1_bars - b1_bars - a2_bars - c1_bars)

    # --- Contrasting characters for episodes ---
    if character in (CharacterToken.SERENE, CharacterToken.LYRICAL,
                     CharacterToken.TENDER, CharacterToken.PASTORAL):
        b_character = CharacterToken.AGITATED
        c_character = CharacterToken.MYSTERIOUS
    elif character in (CharacterToken.HEROIC, CharacterToken.TRIUMPHANT,
                       CharacterToken.MAJESTIC):
        b_character = CharacterToken.LYRICAL
        c_character = CharacterToken.MYSTERIOUS
    else:
        b_character = CharacterToken.LYRICAL
        c_character = CharacterToken.AGITATED

    # --- Build sections ---
    # A1: Refrain (first statement)
    a1_section = SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=a1_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
                notes="rondo_refrain",
            ),
        ],
        key_path=[home_key],
    )

    # B: Episode 1 (contrasting, dominant/relative major)
    b_section = SectionIR(
        type=SectionType.B_SECTION, key=b_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.S_THEME, key=b_key,
                bars=b1_bars, character=b_character,
                texture=TextureToken.POLYPHONIC,
                cadence_at_end=CadenceType.HC,
                notes="rondo_episode_1",
            ),
        ],
        key_path=[b_key],
    )

    # A2: Refrain return (identical replay)
    a2_section = SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=a2_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
                notes="rondo_refrain",
            ),
        ],
        key_path=[home_key],
    )

    # C: Episode 2 (most contrasting, distant key)
    c_section = SectionIR(
        type=SectionType.C_SECTION, key=c_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.CORE, key=c_key,
                bars=c1_bars, character=c_character,
                texture=TextureToken.ARPEGGIO,
                cadence_at_end=CadenceType.HC,
                notes="rondo_episode_2",
            ),
        ],
        key_path=[c_key],
    )

    # A3: Final refrain (tonic, possibly extended with coda feel)
    a3_section = SectionIR(
        type=SectionType.A_SECTION, key=home_key,
        subsections=[
            SubsectionIR(
                type=SubsectionType.P_THEME, key=home_key,
                bars=a3_bars, character=character,
                texture=TextureToken.MELODY_ACCOMP,
                cadence_at_end=CadenceType.PAC,
                notes="rondo_refrain",
            ),
        ],
        key_path=[home_key],
    )

    return [a1_section, b_section, a2_section, c_section, a3_section]
