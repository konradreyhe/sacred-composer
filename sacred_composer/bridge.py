"""Bridge to existing PerformanceIR — reuse humanization infrastructure.

Converts Sacred Composer Score/Voice objects to the PerformanceIR/PerformanceNote
format defined in SYSTEM_ARCHITECTURE.py, enabling use of the existing
humanization pass (1/f rubato, KTH rules, etc.).
"""

from __future__ import annotations

import sys
import os

from sacred_composer.core import Score, Voice, Note


def score_to_performance_ir(score: Score):
    """Convert a Sacred Composer Score to a PerformanceIR.

    Returns a PerformanceIR object (from SYSTEM_ARCHITECTURE.py)
    containing all notes from all voices, with timing converted
    from beats to seconds using the score's tempo.
    """
    # Import from the existing system
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from SYSTEM_ARCHITECTURE import PerformanceNote, PerformanceIR

    beats_per_sec = score.tempo / 60.0
    perf_notes = []

    for voice in score.voices:
        for note in voice.notes:
            if note.is_rest:
                continue

            start_sec = note.time / beats_per_sec
            dur_sec = note.duration / beats_per_sec

            perf_notes.append(PerformanceNote(
                midi_pitch=max(0, min(127, note.pitch)),
                start_time_sec=start_sec,
                duration_sec=dur_sec,
                velocity=max(1, min(127, note.velocity)),
                channel=voice.channel,
                instrument=_gm_to_instrument_name(voice.instrument),
            ))

    # Sort by start time
    perf_notes.sort(key=lambda n: n.start_time_sec)

    total_dur = max((n.start_time_sec + n.duration_sec for n in perf_notes), default=0.0)

    return PerformanceIR(
        notes=perf_notes,
        tempo_map=[(0.0, float(score.tempo))],
        total_duration_sec=total_dur,
    )


def voice_to_performance_notes(voice: Voice, tempo: int = 72) -> list:
    """Convert a single Voice to a list of PerformanceNote objects."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from SYSTEM_ARCHITECTURE import PerformanceNote

    beats_per_sec = tempo / 60.0
    notes = []

    for note in voice.notes:
        if note.is_rest:
            continue
        notes.append(PerformanceNote(
            midi_pitch=max(0, min(127, note.pitch)),
            start_time_sec=note.time / beats_per_sec,
            duration_sec=note.duration / beats_per_sec,
            velocity=max(1, min(127, note.velocity)),
            channel=voice.channel,
            instrument=_gm_to_instrument_name(voice.instrument),
        ))

    return notes


def _gm_to_instrument_name(program: int) -> str:
    """Map GM program number to instrument name."""
    gm_names = {
        0: "piano", 6: "harpsichord", 8: "celesta", 11: "vibraphone",
        12: "marimba", 19: "organ", 24: "guitar", 40: "violin",
        41: "viola", 42: "cello", 43: "contrabass", 46: "harp",
        48: "strings", 52: "choir", 56: "trumpet", 57: "trombone",
        58: "tuba", 60: "horn", 68: "oboe", 70: "bassoon",
        71: "clarinet", 73: "flute", 74: "recorder", 75: "pan_flute",
    }
    return gm_names.get(program, "piano")
