"""MusicXML export for Sacred Composer.

Renders a Score to MusicXML format, opening in MuseScore, Finale,
Sibelius, Dorico, and any other notation software that supports MusicXML.

Uses music21 if available, with a raw XML fallback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sacred_composer.core import Score


# MIDI pitch names for raw XML output
_PITCH_NAMES = ["C", "C", "D", "D", "E", "F", "F", "G", "G", "A", "A", "B"]
_PITCH_ALTERS = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]


def render_musicxml(score: "Score", filename: str, title: str = "Sacred Composition") -> str:
    """Convert a Score to a MusicXML file.

    Tries music21 first; falls back to raw XML string generation.
    Returns the filename written.
    """
    try:
        return _render_via_music21(score, filename, title)
    except ImportError:
        return _render_raw_xml(score, filename, title)


def _render_via_music21(score: "Score", filename: str, title: str) -> str:
    from music21 import stream, note, clef, meter, tempo, metadata

    s = stream.Score()
    s.metadata = metadata.Metadata(title=title, composer="Sacred Composer")

    for voice in score.voices:
        part = stream.Part()
        part.partName = voice.name

        # Auto-detect clef from median pitch
        pitches = [n.pitch for n in voice.notes if not n.is_rest]
        if pitches:
            median = sorted(pitches)[len(pitches) // 2]
            if median < 55:
                part.append(clef.BassClef())
            elif median < 60:
                part.append(clef.AltoClef())

        part.append(meter.TimeSignature("4/4"))
        part.append(tempo.MetronomeMark(number=score.tempo))

        for n in voice.notes:
            if n.is_rest:
                m21note = note.Rest(quarterLength=abs(n.duration))
            else:
                m21note = note.Note(n.pitch, quarterLength=n.duration)
                m21note.volume.velocity = n.velocity
            part.append(m21note)

        s.append(part)

    s.write("musicxml", fp=filename)
    return filename


def _render_raw_xml(score: "Score", filename: str, title: str) -> str:
    """Generate MusicXML 4.0 without music21 using string templating."""
    lines: list[str] = []
    lines.extend(_xml_document_header(title))
    lines.extend(_xml_part_list(score))
    for i, voice in enumerate(score.voices):
        lines.extend(_xml_part(voice, pid=f"P{i + 1}", score=score))
    lines.append("</score-partwise>")

    xml_str = "\n".join(lines)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_str)

    return filename


def _xml_document_header(title: str) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"',
        '  "http://www.musicxml.org/dtds/partwise.dtd">',
        '<score-partwise version="4.0">',
        "  <work>",
        f"    <work-title>{_xml_escape(title)}</work-title>",
        "  </work>",
        "  <identification>",
        '    <creator type="composer">Sacred Composer</creator>',
        "  </identification>",
    ]


def _xml_part_list(score: "Score") -> list[str]:
    lines = ["  <part-list>"]
    for i, voice in enumerate(score.voices):
        pid = f"P{i + 1}"
        lines.append(f'    <score-part id="{pid}">')
        lines.append(f"      <part-name>{_xml_escape(voice.name)}</part-name>")
        lines.append("    </score-part>")
    lines.append("  </part-list>")
    return lines


def _xml_part(voice, pid: str, score: "Score") -> list[str]:
    beats_per_measure = 4
    lines = [f'  <part id="{pid}">']

    # Collect notes into measures
    measures: list[list] = []
    for n in voice.notes:
        measure_idx = int(n.time // beats_per_measure)
        while len(measures) <= measure_idx:
            measures.append([])
        measures[measure_idx].append(n)

    # Ensure at least one measure
    if not measures:
        measures.append([])

    for m_idx, m_notes in enumerate(measures):
        lines.append(f'    <measure number="{m_idx + 1}">')
        if m_idx == 0:
            lines.extend(_xml_first_measure_attributes(voice, score))
        for n in m_notes:
            lines.extend(_xml_note(n))
        lines.append("    </measure>")

    lines.append("  </part>")
    return lines


def _xml_first_measure_attributes(voice, score: "Score") -> list[str]:
    lines = [
        "      <attributes>",
        "        <divisions>4</divisions>",  # 4 divisions per quarter
        "        <time>",
        "          <beats>4</beats>",
        "          <beat-type>4</beat-type>",
        "        </time>",
    ]
    lines.extend(_xml_clef_lines(voice))
    lines.append("      </attributes>")
    lines.append("      <direction>")
    lines.append('        <sound tempo="{}"/>'.format(score.tempo))
    lines.append("      </direction>")
    return lines


def _xml_clef_lines(voice) -> list[str]:
    pitches = [n.pitch for n in voice.notes if not n.is_rest]
    if pitches:
        median = sorted(pitches)[len(pitches) // 2]
        if median < 55:
            sign, line = "F", 4
        elif median < 60:
            sign, line = "C", 3
        else:
            sign, line = "G", 2
    else:
        sign, line = "G", 2
    return [
        "        <clef>",
        f"          <sign>{sign}</sign>",
        f"          <line>{line}</line>",
        "        </clef>",
    ]


def _xml_note(n) -> list[str]:
    dur_divisions = max(1, int(round(abs(n.duration) * 4)))  # 4 divs per quarter
    dur_type = _duration_type(abs(n.duration))
    if n.is_rest:
        return [
            "      <note>",
            "        <rest/>",
            f"        <duration>{dur_divisions}</duration>",
            f"        <type>{dur_type}</type>",
            "      </note>",
        ]
    step = _PITCH_NAMES[n.pitch % 12]
    alter = _PITCH_ALTERS[n.pitch % 12]
    octave = (n.pitch // 12) - 1
    lines = [
        "      <note>",
        "        <pitch>",
        f"          <step>{step}</step>",
    ]
    if alter:
        lines.append(f"          <alter>{alter}</alter>")
    lines.append(f"          <octave>{octave}</octave>")
    lines.append("        </pitch>")
    lines.append(f"        <duration>{dur_divisions}</duration>")
    lines.append(f"        <type>{dur_type}</type>")
    if n.velocity > 0:
        # MusicXML dynamics as percentage (0-100 roughly)
        dyn_pct = round(n.velocity / 127 * 100)
        lines.append("        <dynamics>")
        lines.append(f"          <other-dynamics>{dyn_pct}</other-dynamics>")
        lines.append("        </dynamics>")
    lines.append("      </note>")
    return lines


def _duration_type(beats: float) -> str:
    """Map beat duration to MusicXML duration type name."""
    if beats >= 4.0:
        return "whole"
    elif beats >= 2.0:
        return "half"
    elif beats >= 1.0:
        return "quarter"
    elif beats >= 0.5:
        return "eighth"
    elif beats >= 0.25:
        return "16th"
    elif beats >= 0.125:
        return "32nd"
    else:
        return "64th"


def _xml_escape(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
