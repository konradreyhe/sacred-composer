"""Mappers — translate raw pattern values into musical parameters.

Pure functions. No side effects, no state. Each returns a list of
the same length as the input.
"""

from __future__ import annotations

from dataclasses import dataclass

from sacred_composer.constants import parse_scale


@dataclass
class FormSection:
    """One section in a formal plan."""
    label: str
    start_bar: int
    end_bar: int
    bars: int
    key: str | None = None
    character: str | None = None


def to_pitch(
    values: list[float],
    scale: str = "C_major",
    octave_range: tuple[int, int] = (3, 6),
    strategy: str = "modular",
    pitch_set: list[int] | None = None,
) -> list[int]:
    """Map numeric values to MIDI note numbers within a scale.

    Parameters
    ----------
    values : Raw pattern values (any range).
    scale : Scale name like "C_major", "A_minor", "D_dorian".
    octave_range : MIDI octave bounds (inclusive).
    strategy : "modular" (wrap), "normalize" (linear scale), "nearest" (quantize).
    pitch_set : Optional explicit list of allowed MIDI notes (overrides scale).
    """
    if pitch_set is not None:
        allowed = sorted(pitch_set)
    else:
        all_notes = parse_scale(scale)
        low = octave_range[0] * 12 + 12  # MIDI octave convention: C4 = 60 = octave 4
        high = (octave_range[1] + 1) * 12 + 11
        allowed = [n for n in all_notes if low <= n <= high]

    if not allowed:
        import logging
        logging.getLogger(__name__).warning(
            f"No scale notes in octave range {octave_range} for scale '{scale}'. "
            f"Defaulting all pitches to middle C (60)."
        )
        return [60] * len(values)

    result = []
    if strategy == "modular":
        n_notes = len(allowed)
        for v in values:
            idx = int(v) % n_notes
            result.append(allowed[idx])

    elif strategy == "normalize":
        if not values:
            return []
        v_min = min(values)
        v_max = max(values)
        v_range = v_max - v_min if v_max != v_min else 1.0
        for v in values:
            normalized = (v - v_min) / v_range
            idx = int(normalized * (len(allowed) - 1))
            idx = max(0, min(idx, len(allowed) - 1))
            result.append(allowed[idx])

    elif strategy == "nearest":
        for v in values:
            # Treat v as a MIDI note number, find nearest in allowed set
            target = v
            best = min(allowed, key=lambda n: abs(n - target))
            result.append(best)

    else:
        raise ValueError(f"Unknown pitch strategy: {strategy}")

    return result


def to_pitch_microtonal(
    frequencies: list[float],
) -> list[float]:
    """Map frequencies (Hz) to fractional MIDI note numbers.

    Use with Composition.add_voice_microtonal() for just intonation,
    overtone series, or other non-12-TET tunings.

    Parameters
    ----------
    frequencies : Frequencies in Hz.

    Returns
    -------
    list[float] — fractional MIDI note numbers (e.g. 69.0 = A4, 69.5 = A4+50 cents).
    """
    import math
    result = []
    for f in frequencies:
        if f <= 0:
            result.append(-1.0)
        else:
            midi = 69 + 12 * math.log2(f / 440.0)
            result.append(midi)
    return result


def to_rhythm(
    values: list[float],
    base_duration: float = 1.0,
    time_signature: tuple[int, int] = (4, 4),
    strategy: str = "proportional",
) -> list[float]:
    """Map numeric values to note durations in beats.

    Negative durations indicate rests.

    Strategies:
    - "proportional": duration = value * base_duration
    - "binary": value > 0.5 -> base_duration, else rest (-base_duration)
    - "quantize": snap to nearest standard duration
    - "ratio": values are duration ratios directly
    """
    standard_durations = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]

    result = []
    if strategy == "proportional":
        for v in values:
            dur = abs(v) * base_duration
            if dur < 0.125:
                dur = 0.125  # minimum sixteenth note
            result.append(dur)

    elif strategy == "binary":
        for v in values:
            if v > 0.5:
                result.append(base_duration)
            else:
                result.append(-base_duration)  # rest

    elif strategy == "quantize":
        for v in values:
            dur = abs(v) * base_duration
            best = min(standard_durations, key=lambda d: abs(d - dur))
            result.append(best)

    elif strategy == "ratio":
        for v in values:
            dur = abs(v) * base_duration
            if dur < 0.125:
                dur = 0.125
            result.append(dur)

    else:
        raise ValueError(f"Unknown rhythm strategy: {strategy}")

    return result


def to_dynamics(
    values: list[float],
    velocity_range: tuple[int, int] = (40, 110),
    strategy: str = "normalize",
) -> list[int]:
    """Map numeric values to MIDI velocity (1-127).

    Strategies:
    - "normalize": linearly scale values to velocity range
    - "threshold": above median -> high, else low
    - "absolute": values used directly as velocities (clamped)
    """
    lo, hi = velocity_range

    if strategy == "normalize":
        if not values:
            return []
        v_min = min(values)
        v_max = max(values)
        v_range = v_max - v_min if v_max != v_min else 1.0
        result = []
        for v in values:
            normalized = (v - v_min) / v_range
            vel = int(lo + normalized * (hi - lo))
            result.append(max(1, min(127, vel)))
        return result

    elif strategy == "threshold":
        if not values:
            return []
        median = sorted(values)[len(values) // 2]
        return [hi if v > median else lo for v in values]

    elif strategy == "absolute":
        return [max(1, min(127, int(v))) for v in values]

    else:
        raise ValueError(f"Unknown dynamics strategy: {strategy}")


def to_form(
    values: list[float],
    total_bars: int,
    section_labels: list[str] | None = None,
) -> list[FormSection]:
    """Map numeric values to formal section boundaries.

    Values are used as proportional lengths of sections.
    E.g., [5, 8, 13, 8, 5] with total_bars=39 -> sections of 5, 8, 13, 8, 5 bars.
    """
    if not values:
        return [FormSection(label="A", start_bar=0, end_bar=total_bars, bars=total_bars)]

    total_weight = sum(abs(v) for v in values)
    if total_weight == 0:
        total_weight = len(values)
        values = [1.0] * len(values)

    # Calculate proportional bar counts, ensuring at least 1 bar each
    raw_bars = [(abs(v) / total_weight) * total_bars for v in values]
    bar_counts = [max(1, round(b)) for b in raw_bars]

    # Adjust to match total_bars exactly
    diff = total_bars - sum(bar_counts)
    if diff != 0:
        # Add/subtract from the largest section
        largest_idx = bar_counts.index(max(bar_counts))
        bar_counts[largest_idx] += diff

    # Generate labels
    if section_labels is None:
        labels = []
        for i in range(len(values)):
            labels.append(chr(ord("A") + i) if i < 26 else f"S{i}")
    else:
        labels = section_labels

    sections = []
    current_bar = 0
    for i, bars in enumerate(bar_counts):
        label = labels[i] if i < len(labels) else f"S{i}"
        sections.append(FormSection(
            label=label,
            start_bar=current_bar,
            end_bar=current_bar + bars,
            bars=bars,
        ))
        current_bar += bars

    return sections
