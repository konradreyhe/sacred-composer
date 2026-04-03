"""Developing variation — Schoenberg's technique of ordered motif transformation.

Transforms a basic motif through augmentation, diminution, inversion,
retrograde, interval expansion/contraction, fragmentation, and liquidation.
Provides a drop-in replacement for add_motivic_variation in constraints.py
that targets the repetition_variation evaluator metric.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Motif:
    """A short melodic idea represented as intervals + durations."""

    intervals: list[int]  # semitone intervals between consecutive notes
    durations: list[float]  # beat durations

    @classmethod
    def from_pitches(cls, pitches: list[int], durations: list[float]) -> "Motif":
        """Extract motif from absolute pitches."""
        intervals = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]
        return cls(intervals=intervals, durations=durations[: len(intervals) + 1])

    def to_pitches(self, start_pitch: int = 60) -> list[int]:
        """Realize motif as absolute pitches from a starting note."""
        pitches = [start_pitch]
        for iv in self.intervals:
            pitches.append(pitches[-1] + iv)
        return pitches

    @property
    def n_notes(self) -> int:
        """Number of notes in this motif."""
        return len(self.intervals) + 1

    def copy(self) -> "Motif":
        return Motif(intervals=list(self.intervals), durations=list(self.durations))


# ---------------------------------------------------------------------------
# 7 transformation functions + liquidate
# ---------------------------------------------------------------------------


def augment(motif: Motif, factor: float = 2.0) -> Motif:
    """Double (or scale) all durations."""
    return Motif(
        intervals=list(motif.intervals),
        durations=[d * factor for d in motif.durations],
    )


def diminish(motif: Motif, factor: float = 0.5) -> Motif:
    """Halve (or scale) all durations."""
    return Motif(
        intervals=list(motif.intervals),
        durations=[d * factor for d in motif.durations],
    )


def invert(motif: Motif) -> Motif:
    """Negate all intervals (mirror around axis)."""
    return Motif(
        intervals=[-iv for iv in motif.intervals],
        durations=list(motif.durations),
    )


def retrograde(motif: Motif) -> Motif:
    """Reverse the order of intervals and durations."""
    return Motif(
        intervals=list(reversed(motif.intervals)),
        durations=list(reversed(motif.durations)),
    )


def expand_intervals(motif: Motif, factor: float = 1.5) -> Motif:
    """Multiply all intervals by factor (widen leaps)."""
    return Motif(
        intervals=[int(round(iv * factor)) for iv in motif.intervals],
        durations=list(motif.durations),
    )


def contract_intervals(motif: Motif, factor: float = 0.5) -> Motif:
    """Multiply all intervals by factor (narrow leaps), round to int."""
    return Motif(
        intervals=[int(round(iv * factor)) for iv in motif.intervals],
        durations=list(motif.durations),
    )


def fragment(motif: Motif, n_notes: int = 3) -> Motif:
    """Take only the first n_notes of the motif."""
    n_notes = max(2, min(n_notes, motif.n_notes))
    return Motif(
        intervals=list(motif.intervals[: n_notes - 1]),
        durations=list(motif.durations[:n_notes]),
    )


def liquidate(motif: Motif, steps: int = 1) -> Motif:
    """Schoenberg's liquidation: progressively replace characteristic intervals with steps.

    *steps* controls how many of the largest intervals are replaced.
    steps=1 replaces the single largest interval, steps=2 the two largest, etc.
    Replacement intervals are 1 or 2 semitones, preserving direction.
    """
    if not motif.intervals:
        return motif.copy()

    new_intervals = list(motif.intervals)
    # Indices sorted by descending absolute interval size
    ranked = sorted(range(len(new_intervals)), key=lambda i: abs(new_intervals[i]), reverse=True)

    for k in range(min(steps, len(ranked))):
        idx = ranked[k]
        iv = new_intervals[idx]
        if iv == 0:
            continue
        direction = 1 if iv > 0 else -1
        # Replace with a step (1 or 2 semitones), keeping direction
        new_intervals[idx] = direction * (2 if abs(iv) > 4 else 1)

    return Motif(intervals=new_intervals, durations=list(motif.durations))


# ---------------------------------------------------------------------------
# Variation distance
# ---------------------------------------------------------------------------


def variation_distance(a: Motif, b: Motif) -> float:
    """Edit distance on interval+duration sequences, normalized 0-1.

    Uses a simple element-wise comparison of intervals and durations,
    padded to equal length. The result is 0 for identical motifs and
    approaches 1 for completely different ones.
    """
    max_len = max(len(a.intervals), len(b.intervals))
    if max_len == 0:
        return 0.0

    # Pad shorter with zeros
    a_iv = list(a.intervals) + [0] * (max_len - len(a.intervals))
    b_iv = list(b.intervals) + [0] * (max_len - len(b.intervals))

    max_dur_len = max(len(a.durations), len(b.durations))
    a_dur = list(a.durations) + [0.0] * (max_dur_len - len(a.durations))
    b_dur = list(b.durations) + [0.0] * (max_dur_len - len(b.durations))

    # Interval distance: normalized by 12 (octave)
    iv_dist = sum(abs(ai - bi) / 12.0 for ai, bi in zip(a_iv, b_iv)) / max_len

    # Duration distance: normalized by max duration present
    max_d = max(max(abs(d) for d in a_dur + b_dur), 0.01)
    dur_dist = sum(abs(ad - bd) / max_d for ad, bd in zip(a_dur, b_dur)) / max_dur_len

    # Weighted combination (intervals matter more for recognizability)
    combined = 0.7 * min(iv_dist, 1.0) + 0.3 * min(dur_dist, 1.0)
    return min(combined, 1.0)


# ---------------------------------------------------------------------------
# Phrase-level developing variation
# ---------------------------------------------------------------------------

# All available transforms with descriptive names
_TRANSFORMS = [
    ("invert", lambda m, rng: invert(m)),
    ("retrograde", lambda m, rng: retrograde(m)),
    ("expand", lambda m, rng: expand_intervals(m, 1.0 + rng.random() * 0.5)),
    ("contract", lambda m, rng: contract_intervals(m, 0.4 + rng.random() * 0.3)),
    ("augment", lambda m, rng: augment(m, 1.2 + rng.random() * 0.6)),
    ("diminish", lambda m, rng: diminish(m, 0.5 + rng.random() * 0.3)),
    ("fragment", lambda m, rng: fragment(m, max(3, m.n_notes - rng.randint(1, max(2, m.n_notes // 2))))),
    ("liquidate1", lambda m, rng: liquidate(m, steps=1)),
    ("liquidate2", lambda m, rng: liquidate(m, steps=2)),
    ("inv+ret", lambda m, rng: retrograde(invert(m))),
    ("inv+expand", lambda m, rng: expand_intervals(invert(m), 1.0 + rng.random() * 0.4)),
    ("frag+inv", lambda m, rng: invert(fragment(m, max(3, m.n_notes - 1)))),
]


def develop_phrase(
    motif: Motif,
    n_phrases: int,
    target_distance: float = 0.4,
    seed: int = 42,
) -> list[Motif]:
    """Generate *n_phrases* variations of *motif*.

    Each variation is selected to be approximately *target_distance* from
    the previous one (sweet spot: 0.3-0.5 for the evaluator). The search
    is deterministic given *seed*.
    """
    rng = random.Random(seed)
    results: list[Motif] = [motif.copy()]
    prev = motif

    for _ in range(n_phrases - 1):
        best: Motif | None = None
        best_err = float("inf")

        # Try every transform, pick the one closest to target_distance
        rng_state = rng.getstate()
        for _name, fn in _TRANSFORMS:
            rng.setstate(rng_state)
            candidate = fn(prev, rng)

            # Pad durations if fragment shortened them
            while len(candidate.durations) < len(motif.durations):
                candidate.durations.append(motif.durations[len(candidate.durations) % len(motif.durations)])
            while len(candidate.intervals) < len(motif.intervals):
                candidate.intervals.append(0)

            dist = variation_distance(prev, candidate)
            err = abs(dist - target_distance)
            if err < best_err:
                best_err = err
                best = candidate

        # Advance RNG state deterministically
        rng.random()
        prev = best  # type: ignore[assignment]
        results.append(prev)

    return results


# ---------------------------------------------------------------------------
# Drop-in replacement for add_motivic_variation
# ---------------------------------------------------------------------------


def apply_developing_variation(
    pitches: list[int],
    durations: list[float],
    phrase_length: int = 8,
    seed: int = 42,
) -> tuple[list[int], list[float]]:
    """Extract the first phrase as motif, then replace subsequent phrases with developed variations.

    Drop-in replacement for the existing ``add_motivic_variation`` in
    ``constraints.py``. Works on raw pitch/duration lists.
    """
    if len(pitches) < phrase_length * 2:
        return list(pitches), list(durations)

    n_phrases = len(pitches) // phrase_length
    first_pitches = pitches[:phrase_length]
    first_durations = durations[:phrase_length]

    motif = Motif.from_pitches(first_pitches, first_durations)
    variations = develop_phrase(motif, n_phrases, target_distance=0.4, seed=seed)

    out_pitches = list(pitches)
    out_durations = list(durations)

    for p_idx in range(1, n_phrases):
        var = variations[p_idx]
        start = p_idx * phrase_length
        start_pitch = pitches[start]  # anchor to original starting pitch

        var_pitches = var.to_pitches(start_pitch)
        var_durations = var.durations

        for j in range(phrase_length):
            idx = start + j
            if idx >= len(out_pitches):
                break
            if j < len(var_pitches):
                # Clamp to valid MIDI range
                out_pitches[idx] = max(0, min(127, var_pitches[j]))
            if j < len(var_durations):
                out_durations[idx] = var_durations[j]

    # Handle any trailing notes beyond the last full phrase
    return out_pitches, out_durations
