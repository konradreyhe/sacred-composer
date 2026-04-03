"""Tonal tension model based on Lerdahl's tonal tension theory.

Computes tension values for musical events using three components:
  1. Surface dissonance — pitch against current chord
  2. Tonal distance — key distance on the Spiral Array
  3. Register tension — extremity of pitch register

These combine into a single tension value (0.0-1.0) per event, enabling
compositions to be shaped to follow target tension curves.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from sacred_composer.constants import NOTE_NAMES, SCALES, parse_scale, PHI_INVERSE
from sacred_composer.harmony import Chord, roman_to_chord, generate_progression

if TYPE_CHECKING:
    from sacred_composer.core import Composition


# ---------------------------------------------------------------------------
# Circle of fifths
# ---------------------------------------------------------------------------

# Maps pitch class (0-11) to position on the circle of fifths.
FIFTHS: list[int] = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]


def fifth_distance(pc1: int, pc2: int) -> int:
    """Distance on the circle of fifths between two pitch classes (0-6).

    Parameters
    ----------
    pc1, pc2 : Pitch classes (0-11, mod 12 applied internally).

    Returns
    -------
    Integer distance 0-6 (wraps at the tritone).
    """
    idx1 = FIFTHS.index(pc1 % 12)
    idx2 = FIFTHS.index(pc2 % 12)
    raw = abs(idx1 - idx2)
    return min(raw, 12 - raw)


# ---------------------------------------------------------------------------
# Surface dissonance
# ---------------------------------------------------------------------------

def surface_dissonance(pitch: int, chord_pcs: list[int], scale_pcs: list[int] | None = None) -> float:
    """How dissonant is this pitch against the current chord?

    Parameters
    ----------
    pitch : MIDI note number.
    chord_pcs : Pitch classes (0-11) of the current chord.
    scale_pcs : Pitch classes of the current scale (optional).
        If None, major scale from chord root is assumed.

    Returns
    -------
    0.0 = chord tone, 0.5 = scale tone (non-chord), 1.0 = chromatic tone.
    """
    pc = pitch % 12

    if pc in chord_pcs:
        return 0.0

    if scale_pcs is not None:
        if pc in scale_pcs:
            return 0.5
    else:
        # Assume major scale from the first chord pitch class.
        if chord_pcs:
            root = chord_pcs[0]
            major_pcs = [(root + iv) % 12 for iv in SCALES["major"]]
            if pc in major_pcs:
                return 0.5

    return 1.0


# ---------------------------------------------------------------------------
# Tonal distance (simplified Spiral Array)
# ---------------------------------------------------------------------------

# Spiral Array positions for each pitch class (simplified 2D projection).
# Based on Chew (2000): keys arranged so that close keys on the circle of
# fifths and relative major/minor are nearby in the space.

def _spiral_coords(pc: int) -> tuple[float, float]:
    """Map a pitch class to (x, y) on a simplified Spiral Array."""
    fifths_pos = FIFTHS.index(pc % 12)
    angle = fifths_pos * math.pi / 6  # 30 degrees per fifth
    r = 1.0
    return (r * math.cos(angle), r * math.sin(angle))


def tonal_distance(key_pc1: int, key_pc2: int) -> float:
    """Distance between two keys on the Spiral Array.

    Parameters
    ----------
    key_pc1, key_pc2 : Root pitch classes (0-11) of the two keys.

    Returns
    -------
    Float distance. Same key = 0, dominant/subdominant ~ 1,
    relative ~ 2, distant keys = 5+.

    The value is normalised so the maximum (tritone) is approximately 6.
    """
    if key_pc1 % 12 == key_pc2 % 12:
        return 0.0

    x1, y1 = _spiral_coords(key_pc1)
    x2, y2 = _spiral_coords(key_pc2)
    euclidean = math.hypot(x2 - x1, y2 - y1)

    # Scale so fifth distance = 1 maps to ~1.0 and tritone ~ 6.
    fifth_d = fifth_distance(key_pc1, key_pc2)
    # Blend geometric and circle-of-fifths distance for robustness.
    return 0.5 * euclidean + 0.5 * fifth_d


# ---------------------------------------------------------------------------
# Register tension
# ---------------------------------------------------------------------------

# Comfortable middle register: roughly MIDI 48 (C3) to 84 (C6).
_REGISTER_CENTER = 66.0  # midpoint
_REGISTER_SPAN = 18.0    # half-width of the comfortable zone


def register_tension(pitch: int) -> float:
    """Tension from pitch register extremity.

    Parameters
    ----------
    pitch : MIDI note number.

    Returns
    -------
    0.0 in the comfortable middle register, approaching 1.0 at extremes.
    """
    deviation = abs(pitch - _REGISTER_CENTER)
    normalised = deviation / _REGISTER_SPAN
    return min(1.0, normalised ** 1.5)  # slight exponential curve


# ---------------------------------------------------------------------------
# Combined tension
# ---------------------------------------------------------------------------

# Weights for the three tension components (sum to 1.0).
W_SURFACE = 0.45
W_TONAL = 0.30
W_REGISTER = 0.25


def compute_tension(
    pitch: int,
    chord: Chord | None,
    home_key_pc: int,
    current_key_pc: int,
    scale_pcs: list[int] | None = None,
) -> float:
    """Combined tension value for a single musical event.

    Parameters
    ----------
    pitch : MIDI note number.
    chord : Current chord (None = use tonic triad).
    home_key_pc : Pitch class of the home key root.
    current_key_pc : Pitch class of the local/current key root.
    scale_pcs : Pitch classes of the current scale (optional).

    Returns
    -------
    Float 0.0 (completely relaxed) to 1.0 (maximum tension).
    T = w1 * surface_dissonance + w2 * tonal_distance + w3 * register_tension
    """
    if pitch < 0:
        return 0.0  # rests have no tension

    # Surface dissonance
    if chord is not None:
        chord_pcs = list(chord.pitch_classes)
    else:
        # Default to tonic major triad.
        chord_pcs = [(home_key_pc + iv) % 12 for iv in (0, 4, 7)]
    sd = surface_dissonance(pitch, chord_pcs, scale_pcs)

    # Tonal distance (normalised to 0-1 range; max raw distance ~ 6).
    td_raw = tonal_distance(home_key_pc, current_key_pc)
    td = min(1.0, td_raw / 6.0)

    # Register tension
    rt = register_tension(pitch)

    return W_SURFACE * sd + W_TONAL * td + W_REGISTER * rt


# ---------------------------------------------------------------------------
# Tension curve for a full composition
# ---------------------------------------------------------------------------

def tension_curve(composition: "Composition", home_key: str = "C_major") -> list[float]:
    """Compute a tension value for each note in the composition.

    Parameters
    ----------
    composition : A Composition object.
    home_key : Key string like 'C_major' or 'D_minor'.

    Returns
    -------
    List of floats (one per non-rest note across all voices, in time order).
    """
    parts = home_key.split("_", 1)
    root_name = parts[0]
    scale_type = parts[1] if len(parts) > 1 else "major"
    home_key_pc = NOTE_NAMES.get(root_name, 0)
    scale_intervals = SCALES.get(scale_type, SCALES["major"])
    scale_pcs = [(home_key_pc + iv) % 12 for iv in scale_intervals]

    # Collect all non-rest notes with their start times.
    events: list[tuple[float, int]] = []
    for voice in composition.score.voices:
        for note in voice.notes:
            if not note.is_rest:
                events.append((note.time, note.pitch))

    # Sort by time for a coherent tension timeline.
    events.sort(key=lambda e: e[0])

    # Default chord: tonic triad.
    tonic_chord = Chord(
        root=home_key_pc,
        quality="major" if "major" in scale_type else "minor",
        pitch_classes=tuple((home_key_pc + iv) % 12 for iv in (0, 4, 7)
                           if "major" in scale_type)
        or tuple((home_key_pc + iv) % 12 for iv in (0, 3, 7)),
        roman="I",
    )

    tensions: list[float] = []
    for _time, pitch in events:
        t = compute_tension(
            pitch=pitch,
            chord=tonic_chord,
            home_key_pc=home_key_pc,
            current_key_pc=home_key_pc,
            scale_pcs=scale_pcs,
        )
        tensions.append(t)

    return tensions


# ---------------------------------------------------------------------------
# Target tension curves
# ---------------------------------------------------------------------------

def target_curve_sonata(n_points: int) -> list[float]:
    """Sonata form tension curve: low -> build -> peak at development -> release at recap.

    Exposition (0-38%): moderate build 0.2 -> 0.5
    Development (38-62%): high tension 0.5 -> 0.9
    Recapitulation (62-90%): release 0.9 -> 0.3
    Coda (90-100%): final settling 0.3 -> 0.1
    """
    curve: list[float] = []
    for i in range(n_points):
        t = i / max(1, n_points - 1)
        if t < 0.38:
            # Exposition: gradual build.
            curve.append(0.2 + 0.3 * (t / 0.38))
        elif t < 0.62:
            # Development: high tension peak.
            dev_t = (t - 0.38) / 0.24
            curve.append(0.5 + 0.4 * math.sin(dev_t * math.pi))
        elif t < 0.90:
            # Recapitulation: release.
            recap_t = (t - 0.62) / 0.28
            curve.append(0.9 - 0.6 * recap_t)
        else:
            # Coda: settle.
            coda_t = (t - 0.90) / 0.10
            curve.append(0.3 - 0.2 * coda_t)
    return curve


def target_curve_arch(n_points: int) -> list[float]:
    """Arch tension curve: gradual build to golden section, then release.

    Peak at phi-inverse (~61.8%) of the way through.
    """
    peak_pos = PHI_INVERSE  # 0.618
    curve: list[float] = []
    for i in range(n_points):
        t = i / max(1, n_points - 1)
        if t <= peak_pos:
            # Build: sine curve to peak.
            curve.append(0.1 + 0.8 * math.sin(0.5 * math.pi * t / peak_pos))
        else:
            # Release: cosine decay.
            release_t = (t - peak_pos) / (1.0 - peak_pos)
            curve.append(0.9 * math.cos(0.5 * math.pi * release_t) + 0.0)
    return [max(0.0, min(1.0, v)) for v in curve]


def target_curve_ramp(n_points: int) -> list[float]:
    """Continuous build to climax at the end.

    Exponential ramp: gentle start, accelerating toward the final climax.
    """
    curve: list[float] = []
    for i in range(n_points):
        t = i / max(1, n_points - 1)
        # Exponential curve for natural-feeling build.
        curve.append(0.1 + 0.85 * (t ** 1.8))
    return curve


# ---------------------------------------------------------------------------
# Tension-aware pitch adjustment
# ---------------------------------------------------------------------------

def shape_to_tension(
    pitches: list[int],
    durations: list[float],
    target: list[float],
    scale_pitches: list[int],
    home_key_pc: int,
) -> list[int]:
    """Adjust pitches to better match a target tension curve.

    Where actual tension is too low: shift toward chromatic/higher pitches.
    Where actual tension is too high: shift toward chord tones / tonic / centre.

    Parameters
    ----------
    pitches : Original MIDI pitches.
    durations : Beat durations (negative = rest).
    target : Target tension values (same length as pitches).
    scale_pitches : All valid scale MIDI pitches.
    home_key_pc : Root pitch class of the home key.

    Returns
    -------
    Adjusted list of MIDI pitches.
    """
    if not pitches or not target:
        return list(pitches)

    # Ensure target matches length.
    if len(target) < len(pitches):
        # Interpolate target to match pitch count.
        target = _interpolate(target, len(pitches))
    elif len(target) > len(pitches):
        target = target[:len(pitches)]

    tonic_pcs = [(home_key_pc + iv) % 12 for iv in (0, 4, 7)]
    scale_pcs = [(home_key_pc + iv) % 12 for iv in SCALES.get("major", SCALES["major"])]
    scale_set = set(scale_pitches)

    result: list[int] = []
    for i, (p, dur) in enumerate(zip(pitches, durations)):
        if dur < 0 or p < 0:
            result.append(p)
            continue

        actual = compute_tension(
            pitch=p, chord=None,
            home_key_pc=home_key_pc, current_key_pc=home_key_pc,
            scale_pcs=scale_pcs,
        )
        error = target[i] - actual

        if abs(error) < 0.05:
            # Close enough.
            result.append(p)
            continue

        if error > 0:
            # Need MORE tension: move away from chord tones, toward extremes.
            new_p = p
            # Try shifting up (increases register tension and possibly dissonance).
            for shift in range(1, 8):
                candidate = p + shift
                if 0 <= candidate <= 127:
                    cand_tension = compute_tension(
                        candidate, None, home_key_pc, home_key_pc, scale_pcs,
                    )
                    if abs(target[i] - cand_tension) < abs(error):
                        new_p = candidate
                        break
            result.append(new_p)
        else:
            # Need LESS tension: move toward chord tones in centre register.
            best_p = p
            best_err = abs(error)
            # Search nearby scale pitches.
            for candidate in range(max(0, p - 7), min(128, p + 8)):
                if candidate in scale_set or (candidate % 12) in tonic_pcs:
                    cand_tension = compute_tension(
                        candidate, None, home_key_pc, home_key_pc, scale_pcs,
                    )
                    cand_err = abs(target[i] - cand_tension)
                    if cand_err < best_err:
                        best_err = cand_err
                        best_p = candidate
            result.append(best_p)

    return result


def _interpolate(values: list[float], n: int) -> list[float]:
    """Linearly interpolate a list of floats to length n."""
    if n <= 1:
        return [values[0]] if values else [0.0]
    result: list[float] = []
    for i in range(n):
        t = i / (n - 1) * (len(values) - 1)
        lo = int(t)
        hi = min(lo + 1, len(values) - 1)
        frac = t - lo
        result.append(values[lo] * (1.0 - frac) + values[hi] * frac)
    return result
