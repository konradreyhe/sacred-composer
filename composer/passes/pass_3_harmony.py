"""PASS 3: Harmony (SchemaIR -> VoiceLeadingIR with chords)."""

from __future__ import annotations

from SYSTEM_ARCHITECTURE import (
    SchemaIR, SchemaToken, CadenceType,
    VoiceLeadingIR, ChordEvent,
    SCHEMA_REALIZATIONS, realize_schema_in_key,
)
from composer.parser import _KEY_TO_M21


def pass_3_harmony(schema_ir: SchemaIR) -> VoiceLeadingIR:
    """
    PASS 3: Realize schemata as Roman numeral progressions and concrete chords.

    For each schema slot:
      1. Look up the realization template (soprano degrees, bass degrees, harmony)
      2. Convert to actual MIDI pitches using realize_schema_in_key
      3. Create ChordEvent objects with bar/beat positions
    """
    vl_ir = VoiceLeadingIR()
    current_bar = 1

    for sub_schema in schema_ir.schema_plan:
        for slot in sub_schema.schema_sequence:
            # Cadence-only slots (bars=0) just mark the previous chord
            if isinstance(slot.schema, CadenceType):
                if vl_ir.chords:
                    vl_ir.chords[-1].is_cadential = True
                continue

            template = SCHEMA_REALIZATIONS.get(slot.schema)
            if template is None:
                continue

            # Realize in concrete pitches
            m21_key_str = _KEY_TO_M21.get(slot.local_key, "C")
            realization = realize_schema_in_key(slot.schema, m21_key_str, octave=5)

            num_events = len(template.harmony)
            beats_per_event = max(1, (slot.bars * 4) // num_events)

            for i in range(num_events):
                bar_offset = (i * beats_per_event) // 4
                beat_in_bar = 1.0 + (i * beats_per_event) % 4

                soprano_midi = realization["soprano"][i] if i < len(realization["soprano"]) else realization["soprano"][-1]
                bass_midi = realization["bass"][i] if i < len(realization["bass"]) else realization["bass"][-1]

                chord_evt = ChordEvent(
                    bar=current_bar + bar_offset,
                    beat=beat_in_bar,
                    roman_numeral=template.harmony[i],
                    key=slot.local_key,
                    soprano=soprano_midi,
                    alto=0,       # filled in Pass 5
                    tenor=0,      # filled in Pass 5
                    bass=bass_midi,
                    duration_beats=beats_per_event,
                    source_schema=slot.schema if isinstance(slot.schema, SchemaToken) else None,
                )
                vl_ir.chords.append(chord_evt)

            current_bar += slot.bars

    return vl_ir
