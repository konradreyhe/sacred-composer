"""PASS 2: Schema (FormIR -> SchemaIR)."""

from __future__ import annotations

import random
from typing import Dict, List

from SYSTEM_ARCHITECTURE import (
    FormIR, SchemaIR, SubsectionSchemaIR, SchemaSlot,
    SubsectionType, SchemaToken, CadenceType,
    SCHEMA_REALIZATIONS,
)


# Which schemata suit which formal functions
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
    SubsectionType.SUBJECT_ENTRY: [
        SchemaToken.DO_RE_MI, SchemaToken.ROMANESCA, SchemaToken.FENAROLI,
    ],
    SubsectionType.ANSWER_ENTRY: [
        SchemaToken.DO_RE_MI, SchemaToken.PRINNER, SchemaToken.FENAROLI,
    ],
    SubsectionType.COUNTERSUBJECT: [
        SchemaToken.PRINNER, SchemaToken.FENAROLI, SchemaToken.ROMANESCA,
    ],
    SubsectionType.PEDAL_POINT: [
        SchemaToken.QUIESCENZA, SchemaToken.PONTE, SchemaToken.INDUGIO,
    ],
}


def pass_2_schema(form_ir: FormIR) -> SchemaIR:
    """
    PASS 2: Fill each subsection with a sequence of galant schemata.
    Selects schemata by formal function, chains them to fill bar counts,
    and appends cadences at section ends.
    """
    schema_ir = SchemaIR(form_ref=form_ir)

    for section in form_ir.sections:
        for subsection in section.subsections:
            sub_schema = SubsectionSchemaIR(subsection_ref=subsection)
            bars_remaining = subsection.bars

            preferred = SCHEMA_AFFINITIES.get(
                subsection.type,
                [SchemaToken.DO_RE_MI, SchemaToken.PRINNER],
            )

            while bars_remaining > 0:
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

            # Terminal cadence
            if subsection.cadence_at_end:
                cad_slot = SchemaSlot(
                    schema=subsection.cadence_at_end,
                    bars=0,
                    local_key=subsection.key,
                )
                sub_schema.schema_sequence.append(cad_slot)

            schema_ir.schema_plan.append(sub_schema)

    return schema_ir


def pass_2_schema_fugue(form_ir: FormIR) -> SchemaIR:
    """
    PASS 2 (Fugue variant): Assign harmonic schemata to fugue sections.

    Fugue harmony is simpler than sonata form -- mostly I-V-I with
    sequential passages (Monte/Fonte) in episodes.
    """
    schema_ir = SchemaIR(form_ref=form_ir)

    # Schema preferences for fugue section types
    fugue_schema_map = {
        SubsectionType.SUBJECT_ENTRY: [
            SchemaToken.DO_RE_MI, SchemaToken.ROMANESCA, SchemaToken.FENAROLI,
        ],
        SubsectionType.ANSWER_ENTRY: [
            SchemaToken.DO_RE_MI, SchemaToken.PRINNER, SchemaToken.FENAROLI,
        ],
        SubsectionType.TR: [
            SchemaToken.MONTE, SchemaToken.FONTE, SchemaToken.PONTE,
        ],
        SubsectionType.PEDAL_POINT: [
            SchemaToken.QUIESCENZA, SchemaToken.PONTE, SchemaToken.INDUGIO,
        ],
    }

    for section in form_ir.sections:
        for subsection in section.subsections:
            sub_schema = SubsectionSchemaIR(subsection_ref=subsection)
            bars_remaining = subsection.bars

            preferred = fugue_schema_map.get(
                subsection.type,
                [SchemaToken.DO_RE_MI, SchemaToken.PRINNER],
            )

            while bars_remaining > 0:
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

            # Terminal cadence
            if subsection.cadence_at_end:
                cad_slot = SchemaSlot(
                    schema=subsection.cadence_at_end,
                    bars=0,
                    local_key=subsection.key,
                )
                sub_schema.schema_sequence.append(cad_slot)

            schema_ir.schema_plan.append(sub_schema)

    return schema_ir
