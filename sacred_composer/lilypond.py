"""LilyPond renderer — publication-ready .ly notation from Sacred Composer scores.

Generates LilyPond source with intelligent clef selection, dynamics,
articulations, key/time signatures, piano grand staff, and orchestral
staff grouping.  Compile to PDF/PNG with ``lilypond``.
"""

from __future__ import annotations

import logging
import statistics
from typing import Sequence

from sacred_composer.core import Score, Voice, Note

_log = logging.getLogger(__name__)


# ── Pitch helpers ────────────────────────────────────────────────────

_NOTE_NAMES = ["c", "cis", "d", "dis", "e", "f", "fis", "g", "gis", "a", "ais", "b"]

_SHARP_KEYS = {
    "c": r'\key c \major',   "a": r'\key a \minor',
    "g": r'\key g \major',   "e": r'\key e \minor',
    "d": r'\key d \major',   "b": r'\key b \minor',
    "a_major": r'\key a \major', "fis": r'\key fis \minor',
    "e_major": r'\key e \major', "cis": r'\key cis \minor',
    "b_major": r'\key b \major', "gis": r'\key gis \minor',
    "fis_major": r'\key fis \major', "dis": r'\key dis \minor',
    "f": r'\key f \major',   "d_minor": r'\key d \minor',
    "bes": r'\key bes \major', "g_minor": r'\key g \minor',
    "ees": r'\key ees \major', "c_minor": r'\key c \minor',
    "aes": r'\key aes \major', "f_minor": r'\key f \minor',
    "des": r'\key des \major', "bes_minor": r'\key bes \minor',
    "ges": r'\key ges \major', "ees_minor": r'\key ees \minor',
}

# Velocity-to-dynamic mapping: (upper_bound, lily_dynamic)
_DYN_BRACKETS = [
    (31, r"\ppp"), (47, r"\pp"), (63, r"\p"), (79, r"\mp"),
    (95, r"\mf"), (111, r"\f"), (126, r"\ff"), (127, r"\fff"),
]

# Instruments typically written in bass clef
_BASS_INSTRUMENTS = {"cello", "contrabass", "bassoon", "tuba", "trombone"}
_ALTO_INSTRUMENTS = {"viola"}
_TREBLE_INSTRUMENTS = {"violin", "flute", "oboe", "clarinet", "trumpet", "recorder"}

# Orchestral family grouping
_STRING_NAMES = {"violin", "viola", "cello", "contrabass", "strings", "harp"}
_WOODWIND_NAMES = {"flute", "oboe", "clarinet", "bassoon", "recorder", "pan_flute"}
_BRASS_NAMES = {"trumpet", "horn", "trombone", "tuba"}

# GM program-to-name reverse lookup (rough)
_GM_PROG_TO_NAME: dict[int, str] = {}
try:
    from sacred_composer.core import GM_INSTRUMENTS
    for _name, _prog in GM_INSTRUMENTS.items():
        _GM_PROG_TO_NAME.setdefault(_prog, _name)
except ImportError as exc:
    _log.warning("GM_INSTRUMENTS not available; LilyPond output "
                 "will use generic instrument names: %s", exc)


# ── Conversion utilities ─────────────────────────────────────────────

def _midi_to_lily(midi: int) -> str:
    """Convert MIDI note number to LilyPond pitch string."""
    name = _NOTE_NAMES[midi % 12]
    lily_octave = (midi // 12) - 1 - 4  # relative to middle-C octave
    if lily_octave > 0:
        name += "'" * lily_octave
    elif lily_octave < 0:
        name += "," * (-lily_octave)
    return name


def _duration_to_lily(beats: float) -> str:
    """Convert duration in beats to a LilyPond duration string."""
    dur_map = {
        4.0: "1", 3.0: "2.", 2.0: "2", 1.5: "4.", 1.0: "4",
        0.75: "8.", 0.5: "8", 0.375: "16.", 0.25: "16",
        0.125: "32", 0.0625: "64",
    }
    best_key = min(dur_map, key=lambda d: abs(d - abs(beats)))
    return dur_map[best_key]


def _velocity_to_dynamic(vel: int) -> str:
    """Map a MIDI velocity to a LilyPond dynamic mark."""
    for upper, dyn in _DYN_BRACKETS:
        if vel <= upper:
            return dyn
    return r"\fff"


def _select_clef(voice: Voice) -> str:
    """Choose clef based on instrument name and median pitch."""
    name_lower = voice.name.lower()
    gm_name = _GM_PROG_TO_NAME.get(voice.instrument, "")

    # Instrument-name heuristics first
    for tag in _BASS_INSTRUMENTS:
        if tag in name_lower or tag in gm_name:
            return "bass"
    for tag in _ALTO_INSTRUMENTS:
        if tag in name_lower or tag in gm_name:
            return "alto"
    for tag in _TREBLE_INSTRUMENTS:
        if tag in name_lower or tag in gm_name:
            return "treble"

    # Fall back to median pitch
    pitches = [n.pitch for n in voice.notes if not n.is_rest]
    if not pitches:
        return "treble"
    med = statistics.median(pitches)
    if med < 55:
        return "bass"
    if med < 60:
        return "alto"
    return "treble"


def _resolve_key_signature(key: str | None) -> str:
    """Return a LilyPond \\key directive, or empty string."""
    if key is None:
        return ""
    normalised = key.strip().lower().replace(" ", "_").replace("-", "_")
    # Try direct lookup
    if normalised in _SHARP_KEYS:
        return _SHARP_KEYS[normalised]
    # Try stripping trailing _major / _minor
    base = normalised.replace("_major", "").replace("_minor", "")
    if base in _SHARP_KEYS:
        return _SHARP_KEYS[base]
    return ""


def _instrument_family(voice: Voice) -> str:
    """Classify a voice into an orchestral family."""
    tag = voice.name.lower()
    gm = _GM_PROG_TO_NAME.get(voice.instrument, "")
    for s in _STRING_NAMES:
        if s in tag or s in gm:
            return "strings"
    for s in _WOODWIND_NAMES:
        if s in tag or s in gm:
            return "woodwinds"
    for s in _BRASS_NAMES:
        if s in tag or s in gm:
            return "brass"
    if "piano" in tag or voice.instrument == 0:
        return "piano"
    return "other"


def _is_piano(voice: Voice) -> bool:
    return "piano" in voice.name.lower() or voice.instrument == 0


# ── Voice rendering ──────────────────────────────────────────────────

def _voice_to_lily(
    voice: Voice,
    beats_per_bar: float,
) -> str:
    """Convert a Voice to a LilyPond note sequence with dynamics,
    articulations, and bar-line-aware wrapping."""

    tokens: list[str] = []
    prev_dyn: str | None = None
    beat_accum = 0.0  # beats accumulated in current bar
    notes = voice.notes

    # Pre-compute stepwise slur spans: groups of 3+ consecutive notes
    # with intervals <= 2 semitones.
    slur_starts: set[int] = set()
    slur_ends: set[int] = set()
    _compute_slurs(notes, slur_starts, slur_ends)

    for idx, note in enumerate(notes):
        dur_str = _duration_to_lily(note.duration)

        if note.is_rest:
            tok = f"r{dur_str}"
        else:
            pitch_str = _midi_to_lily(note.pitch)
            tok = f"{pitch_str}{dur_str}"

            # Articulation
            if note.duration < 0.3:
                tok += "-."
            elif note.duration >= 2.0:
                tok += "--"

            # Slurs
            if idx in slur_starts:
                tok += "("
            if idx in slur_ends:
                tok += ")"

            # Dynamics (only on non-rest notes)
            dyn = _velocity_to_dynamic(note.velocity)
            if prev_dyn is None or (abs(note.velocity - _dyn_to_vel(prev_dyn)) >= 16
                                    and dyn != prev_dyn):
                tok += dyn
                prev_dyn = dyn

        tokens.append(tok)

        # Bar-line wrapping
        beat_accum += abs(note.duration)
        if beat_accum >= beats_per_bar - 0.001:
            tokens.append("|")
            beat_accum -= beats_per_bar
            # Clamp tiny float residue
            if beat_accum < 0.01:
                beat_accum = 0.0

    # Format into indented lines, splitting on bar lines
    lines: list[str] = []
    current: list[str] = []
    bars_on_line = 0
    for tok in tokens:
        if tok == "|":
            bars_on_line += 1
            if bars_on_line >= 4:
                lines.append("    " + " ".join(current))
                current = []
                bars_on_line = 0
        else:
            current.append(tok)
    if current:
        lines.append("    " + " ".join(current))

    return "\n".join(lines)


def _compute_slurs(
    notes: Sequence[Note],
    starts: set[int],
    ends: set[int],
) -> None:
    """Find runs of 3+ stepwise notes (interval <= 2 semitones) and
    record slur start/end indices."""
    run_start: int | None = None
    for i in range(1, len(notes)):
        prev, cur = notes[i - 1], notes[i]
        if prev.is_rest or cur.is_rest:
            if run_start is not None and (i - 1) - run_start >= 2:
                starts.add(run_start)
                ends.add(i - 1)
            run_start = None
            continue
        interval = abs(cur.pitch - prev.pitch)
        if interval <= 2:
            if run_start is None:
                run_start = i - 1
        else:
            if run_start is not None and (i - 1) - run_start >= 2:
                starts.add(run_start)
                ends.add(i - 1)
            run_start = None
    # Close trailing run
    if run_start is not None and (len(notes) - 1) - run_start >= 2:
        starts.add(run_start)
        ends.add(len(notes) - 1)


def _dyn_to_vel(dyn: str) -> int:
    """Approximate centre velocity for a dynamic mark."""
    mapping = {
        r"\ppp": 16, r"\pp": 40, r"\p": 56, r"\mp": 72,
        r"\mf": 88, r"\f": 104, r"\ff": 119, r"\fff": 127,
    }
    return mapping.get(dyn, 80)


# ── Staff / score assembly ───────────────────────────────────────────

def _build_staff(
    voice: Voice,
    tempo: int,
    key_sig: str,
    time_sig: tuple[int, int],
    beats_per_bar: float,
) -> str:
    """Build a single \\new Staff block."""
    clef = _select_clef(voice)
    notes_str = _voice_to_lily(voice, beats_per_bar)
    time_str = f"\\time {time_sig[0]}/{time_sig[1]}"

    lines = [
        f'  \\new Staff \\with {{ instrumentName = "{voice.name}" }} {{',
        f"    \\tempo 4 = {tempo}",
        f"    {time_str}",
    ]
    if key_sig:
        lines.append(f"    {key_sig}")
    lines.append(f"    \\clef {clef}")
    lines.append(notes_str)
    lines.append("  }")
    return "\n".join(lines)


def _build_piano_staff(
    voice: Voice,
    tempo: int,
    key_sig: str,
    time_sig: tuple[int, int],
    beats_per_bar: float,
) -> str:
    """Split a piano voice at middle C into treble + bass staves."""
    treble_notes: list[Note] = []
    bass_notes: list[Note] = []
    for n in voice.notes:
        if n.is_rest or n.pitch >= 60:
            treble_notes.append(n)
        if n.is_rest or n.pitch < 60:
            bass_notes.append(n)

    time_str = f"\\time {time_sig[0]}/{time_sig[1]}"
    key_line = f"\n    {key_sig}" if key_sig else ""

    # Build dummy voices for rendering
    tv = Voice(name=voice.name, notes=treble_notes, instrument=voice.instrument)
    bv = Voice(name=voice.name, notes=bass_notes, instrument=voice.instrument)

    treble_body = _voice_to_lily(tv, beats_per_bar)
    bass_body = _voice_to_lily(bv, beats_per_bar)

    return "\n".join([
        f'  \\new PianoStaff \\with {{ instrumentName = "{voice.name}" }} <<',
        f"    \\new Staff {{",
        f"      \\tempo 4 = {tempo}",
        f"      {time_str}{key_line}",
        f"      \\clef treble",
        treble_body,
        f"    }}",
        f"    \\new Staff {{",
        f"      {time_str}{key_line}",
        f"      \\clef bass",
        bass_body,
        f"    }}",
        f"  >>",
    ])


# ── Public API ───────────────────────────────────────────────────────

def render_lilypond(
    score: Score,
    filename: str,
    title: str = "Sacred Composition",
    *,
    key_signature: str | None = None,
    time_signature: tuple[int, int] = (4, 4),
) -> str:
    """Render a Score to a publication-ready LilyPond ``.ly`` file.

    Parameters
    ----------
    score : Score to render.
    filename : Output ``.ly`` path.
    title : Title for the score header.
    key_signature : Optional key name (e.g. ``"d"``, ``"bes"``,
        ``"c_minor"``).  When *None* no ``\\key`` is emitted.
    time_signature : Tuple of (numerator, denominator), default 4/4.

    Returns
    -------
    The *filename* written.
    """
    num, denom = time_signature
    beats_per_bar = num * (4.0 / denom)
    key_sig = _resolve_key_signature(key_signature)

    # ── Header ────────────────────────────────────────────────────
    header = [
        r'\version "2.24.0"',
        r"\header {",
        f'  title = "{title}"',
        '  composer = "Sacred Composer"',
        '  tagline = ##f',
        "}",
        "",
        r"\paper {",
        "  indent = 15\\mm",
        "  short-indent = 8\\mm",
        "}",
        "",
    ]

    # ── Classify voices by family ─────────────────────────────────
    families: dict[str, list[Voice]] = {}
    for v in score.voices:
        fam = _instrument_family(v)
        families.setdefault(fam, []).append(v)

    # ── Build staff blocks ────────────────────────────────────────
    staff_blocks: list[str] = []

    def _render_voice(v: Voice) -> str:
        if _is_piano(v):
            return _build_piano_staff(v, score.tempo, key_sig, time_signature, beats_per_bar)
        return _build_staff(v, score.tempo, key_sig, time_signature, beats_per_bar)

    multi_family = sum(1 for f in families if f != "piano") > 1

    if multi_family:
        # Group orchestral families in StaffGroups
        for fam in ("woodwinds", "brass", "strings"):
            if fam not in families:
                continue
            group_lines = [f'  \\new StaffGroup \\with {{ instrumentName = "{fam.title()}" }} <<']
            for v in families[fam]:
                group_lines.append(_render_voice(v))
            group_lines.append("  >>")
            staff_blocks.append("\n".join(group_lines))
        # Piano and other outside groups
        for fam in ("piano", "other"):
            for v in families.get(fam, []):
                staff_blocks.append(_render_voice(v))
    else:
        # Single family or simple layout — no StaffGroup wrappers
        for v in score.voices:
            staff_blocks.append(_render_voice(v))

    # ── Assemble \\score ──────────────────────────────────────────
    body = [r"\score {", "  <<"]
    for sb in staff_blocks:
        body.append(sb)
    body += [
        "  >>",
        "  \\layout {",
        "    \\context {",
        "      \\Score",
        "      \\override SpacingSpanner.common-shortest-duration =",
        "        #(ly:make-moment 1/8)",
        "    }",
        "  }",
        "  \\midi { }",
        "}",
    ]

    content = "\n".join(header + body) + "\n"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return filename
