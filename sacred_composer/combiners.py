"""Combiners — create polyphony from pattern data.

Combiners take mapped musical data (pitches, durations, velocities)
and produce multiple voices through transformations like canon,
phase shifting, layering, and fractal form.
"""

from __future__ import annotations

from sacred_composer.core import Voice, Note
from sacred_composer.mappers import FormSection


def _build_voice_from_arrays(
    name: str,
    pitches: list[int],
    durations: list[float],
    velocities: list[int],
    channel: int = 0,
    instrument: int = 0,
    start_time: float = 0.0,
    pitch_offset: int = 0,
    duration_scale: float = 1.0,
    min_duration: float = 0.0,
) -> Voice:
    """Create a Voice by assembling Notes from parallel arrays.

    Parameters
    ----------
    name : Voice name.
    pitches : MIDI note numbers.
    durations : Beat durations (negative = rest).
    velocities : MIDI velocities.
    channel : MIDI channel.
    instrument : GM program number.
    start_time : Time offset for the first note (beats).
    pitch_offset : Semitone transposition applied to every pitch.
    duration_scale : Multiplier applied to every duration.
    min_duration : Floor for positive durations (0 = no floor).
    """
    n = min(len(pitches), len(durations))
    voice = Voice(name=name, channel=channel, instrument=instrument)

    time = start_time
    for j in range(n):
        dur = durations[j] * duration_scale
        if durations[j] < 0:
            voice.notes.append(Note(pitch=-1, duration=abs(dur), velocity=0, time=time))
            time += abs(dur)
        else:
            actual_dur = max(min_duration, dur) if min_duration > 0 else dur
            pitch = max(0, min(127, pitches[j % len(pitches)] + pitch_offset))
            voice.notes.append(Note(
                pitch=pitch,
                duration=actual_dur,
                velocity=velocities[j % len(velocities)],
                time=time,
            ))
            time += actual_dur

    return voice


def layer(
    voices_data: list[dict],
) -> list[Voice]:
    """Layer different pattern data as independent voices.

    Parameters
    ----------
    voices_data : list of dicts, each with keys:
        - name: str
        - pitches: list[int]
        - durations: list[float]
        - velocities: list[int] (optional, defaults to 80)
        - instrument: int (optional, GM program number, defaults to 0)

    Returns
    -------
    list[Voice] ready to add to a Score.
    """
    result = []
    for i, vd in enumerate(voices_data):
        pitches = vd["pitches"]
        durations = vd["durations"]
        velocities = vd.get("velocities", [80] * len(pitches))
        voice = _build_voice_from_arrays(
            name=vd.get("name", f"voice_{i}"),
            pitches=pitches,
            durations=durations,
            velocities=velocities,
            channel=i % 16,
            instrument=vd.get("instrument", 0),
        )
        result.append(voice)
    return result


def canon(
    pitches: list[int],
    durations: list[float],
    velocities: list[int] | None = None,
    n_voices: int = 3,
    offset_beats: float = 4.0,
    transpositions: list[int] | None = None,
    instrument: int = 0,
) -> list[Voice]:
    """Create a canon — the same melody at staggered time offsets.

    Parameters
    ----------
    pitches : The melody as MIDI note numbers.
    durations : Note durations in beats.
    velocities : MIDI velocities (optional).
    n_voices : Number of canon voices.
    offset_beats : Time delay between successive voice entries.
    transpositions : Semitone transposition for each voice (optional).
        Default: [0, 0, 0, ...] (all at same pitch).
    instrument : GM program number.

    Returns
    -------
    list[Voice] — n_voices voices, each entering offset_beats later.
    """
    n = min(len(pitches), len(durations))
    if velocities is None:
        velocities = [80] * n
    if transpositions is None:
        transpositions = [0] * n_voices

    result = []
    for v_idx in range(n_voices):
        trans = transpositions[v_idx % len(transpositions)]
        voice = _build_voice_from_arrays(
            name=f"canon_{v_idx + 1}",
            pitches=pitches,
            durations=durations,
            velocities=velocities,
            channel=v_idx % 16,
            instrument=instrument,
            start_time=v_idx * offset_beats,
            pitch_offset=trans,
        )
        result.append(voice)
    return result


def phase(
    pitches: list[int],
    durations: list[float],
    velocities: list[int] | None = None,
    n_voices: int = 2,
    rate_multipliers: list[float] | None = None,
    instrument: int = 0,
) -> list[Voice]:
    """Create phasing — the same pattern at slightly different rates.

    Inspired by Steve Reich's phase music. Voice 1 plays at the base
    rate, voice 2 plays slightly faster (or slower), so they gradually
    drift in and out of alignment.

    Parameters
    ----------
    pitches : The melody as MIDI note numbers.
    durations : Note durations in beats.
    velocities : MIDI velocities (optional).
    n_voices : Number of voices.
    rate_multipliers : Duration multiplier for each voice.
        Default: [1.0, 0.98] — voice 2 is 2% faster.
    instrument : GM program number.

    Returns
    -------
    list[Voice] — voices playing at different rates.
    """
    n = min(len(pitches), len(durations))
    if velocities is None:
        velocities = [80] * n
    if rate_multipliers is None:
        # Default: each subsequent voice is slightly faster
        rate_multipliers = [1.0 - 0.02 * i for i in range(n_voices)]

    result = []
    for v_idx in range(n_voices):
        rate = rate_multipliers[v_idx % len(rate_multipliers)]
        voice = _build_voice_from_arrays(
            name=f"phase_{v_idx + 1}",
            pitches=pitches,
            durations=durations,
            velocities=velocities,
            channel=v_idx % 16,
            instrument=instrument,
            duration_scale=rate,
            min_duration=0.0625,
        )
        result.append(voice)
    return result


def fractal_form(
    motifs: dict[str, dict],
    axiom: str = "A",
    rules: dict[str, str] | None = None,
    depth: int = 3,
) -> tuple[list[Voice], list[FormSection]]:
    """Create fractal formal structure using L-system expansion.

    Each character in the L-system alphabet maps to a musical motif.
    The L-system expands recursively, producing self-similar structure
    at multiple scales.

    Parameters
    ----------
    motifs : Mapping of L-system characters to musical data.
        Each value is a dict with keys: pitches, durations, velocities (optional),
        instrument (optional), transposition (optional, int semitones).
    axiom : Starting string for L-system.
    rules : Production rules. Default: {"A": "ABA", "B": "BCB", "C": "A"}.
    depth : Number of L-system expansions.

    Returns
    -------
    (voices, form_sections) — a list of Voice objects and FormSection metadata.
    """
    from sacred_composer.patterns import Lindenmayer

    if rules is None:
        rules = {"A": "ABA", "B": "BCB", "C": "A"}

    lsys = Lindenmayer(axiom=axiom, rules=rules)
    expansion = lsys.expand(depth)

    all_pitches: list[int] = []
    all_durations: list[float] = []
    all_velocities: list[int] = []
    sections: list[FormSection] = []
    current_beat = 0.0

    for i, char in enumerate(expansion):
        if char not in motifs:
            continue
        section_beats = _append_motif_instance(
            motifs[char], char, i, current_beat,
            all_pitches, all_durations, all_velocities, sections,
        )
        current_beat += section_beats

    instrument = _default_fractal_instrument(motifs)
    voice = _build_fractal_voice(all_pitches, all_durations, all_velocities, instrument)
    return [voice], sections


def _append_motif_instance(
    m: dict, char: str, i: int, current_beat: float,
    all_pitches: list, all_durations: list, all_velocities: list,
    sections: list,
) -> float:
    """Append one motif's notes to the accumulators and record its FormSection.

    Returns the number of beats consumed by this motif.
    """
    pitches = m["pitches"]
    durations = m["durations"]
    velocities = m.get("velocities", [80] * len(pitches))
    transposition = m.get("transposition", 0)

    n = min(len(pitches), len(durations))
    section_beats = sum(abs(d) for d in durations[:n])
    bars = max(1, round(section_beats / 4.0))

    sections.append(FormSection(
        label=f"{char}{i}",
        start_bar=round(current_beat / 4.0),
        end_bar=round((current_beat + section_beats) / 4.0),
        bars=bars,
        character=char,
    ))

    for j in range(n):
        p = max(0, min(127, pitches[j] + transposition))
        all_pitches.append(p)
        all_durations.append(durations[j])
        all_velocities.append(velocities[j % len(velocities)])

    return section_beats


def _default_fractal_instrument(motifs: dict) -> int:
    for m in motifs.values():
        if "instrument" in m:
            return m["instrument"]
    return 0


def _build_fractal_voice(pitches: list[int], durations: list[float],
                         velocities: list[int], instrument: int) -> Voice:
    voice = Voice(name="fractal", channel=0, instrument=instrument)
    time = 0.0
    for j in range(len(pitches)):
        dur = durations[j]
        if dur < 0:
            voice.notes.append(Note(pitch=-1, duration=abs(dur), velocity=0, time=time))
            time += abs(dur)
        else:
            voice.notes.append(Note(
                pitch=pitches[j],
                duration=dur,
                velocity=velocities[j],
                time=time,
            ))
            time += dur
    return voice
