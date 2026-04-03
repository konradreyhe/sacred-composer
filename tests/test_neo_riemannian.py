"""Tests for neo-Riemannian operations in sacred_composer.harmony."""

from __future__ import annotations

import pytest

from sacred_composer.harmony import (
    Chord,
    parallel,
    leading_tone,
    relative,
    tonnetz_distance,
    tonnetz_path,
    neo_riemannian_progression,
)


def _make(root: int, quality: str) -> Chord:
    """Helper to build a triad Chord for testing."""
    intervals = {"major": (0, 4, 7), "minor": (0, 3, 7)}
    pcs = tuple((root + iv) % 12 for iv in intervals[quality])
    return Chord(root=root % 12, quality=quality, pitch_classes=pcs)


# ── PLR operations ─────────────────────────────────────────────

class TestPLR:
    def test_parallel_major_to_minor(self):
        c_maj = _make(0, "major")
        result = parallel(c_maj)
        assert result.root == 0
        assert result.quality == "minor"

    def test_parallel_minor_to_major(self):
        c_min = _make(0, "minor")
        result = parallel(c_min)
        assert result.root == 0
        assert result.quality == "major"

    def test_parallel_involution(self):
        # P(P(x)) == x
        for root in range(12):
            for q in ("major", "minor"):
                ch = _make(root, q)
                assert parallel(parallel(ch)).root == ch.root
                assert parallel(parallel(ch)).quality == ch.quality

    def test_leading_tone_c_major_to_e_minor(self):
        c_maj = _make(0, "major")
        result = leading_tone(c_maj)
        assert result.root == 4  # E
        assert result.quality == "minor"

    def test_leading_tone_e_minor_to_c_major(self):
        e_min = _make(4, "minor")
        result = leading_tone(e_min)
        assert result.root == 0  # C
        assert result.quality == "major"

    def test_leading_tone_involution(self):
        # L(L(x)) == x
        for root in range(12):
            for q in ("major", "minor"):
                ch = _make(root, q)
                result = leading_tone(leading_tone(ch))
                assert result.root == ch.root
                assert result.quality == ch.quality

    def test_relative_c_major_to_a_minor(self):
        c_maj = _make(0, "major")
        result = relative(c_maj)
        assert result.root == 9  # A
        assert result.quality == "minor"

    def test_relative_a_minor_to_c_major(self):
        a_min = _make(9, "minor")
        result = relative(a_min)
        assert result.root == 0  # C
        assert result.quality == "major"

    def test_relative_involution(self):
        # R(R(x)) == x
        for root in range(12):
            for q in ("major", "minor"):
                ch = _make(root, q)
                result = relative(relative(ch))
                assert result.root == ch.root
                assert result.quality == ch.quality


# ── Tonnetz distance ───────────────────────────────────────────

class TestTonnetz:
    def test_distance_to_self_is_zero(self):
        for root in range(12):
            for q in ("major", "minor"):
                ch = _make(root, q)
                assert tonnetz_distance(ch, ch) == 0

    def test_c_major_to_c_minor_is_1(self):
        assert tonnetz_distance(_make(0, "major"), _make(0, "minor")) == 1

    def test_symmetric(self):
        pairs = [
            (_make(0, "major"), _make(4, "minor")),
            (_make(7, "major"), _make(2, "minor")),
            (_make(5, "minor"), _make(9, "major")),
        ]
        for a, b in pairs:
            assert tonnetz_distance(a, b) == tonnetz_distance(b, a)

    def test_max_distance_at_most_5(self):
        # The Tonnetz graph has 24 nodes; BFS max distance is at most ~4-5
        for r1 in range(12):
            for q1 in ("major", "minor"):
                for r2 in range(12):
                    for q2 in ("major", "minor"):
                        d = tonnetz_distance(_make(r1, q1), _make(r2, q2))
                        assert d <= 5, f"Distance {d} for ({r1},{q1})->({r2},{q2})"

    def test_adjacent_chords_distance_1(self):
        c_maj = _make(0, "major")
        # All three PLR neighbors should be at distance 1
        assert tonnetz_distance(c_maj, parallel(c_maj)) == 1
        assert tonnetz_distance(c_maj, leading_tone(c_maj)) == 1
        assert tonnetz_distance(c_maj, relative(c_maj)) == 1


# ── Tonnetz path ───────────────────────────────────────────────

class TestTonnetzPath:
    def test_path_length_equals_distance(self):
        a = _make(0, "major")
        b = _make(6, "minor")
        path = tonnetz_path(a, b)
        dist = tonnetz_distance(a, b)
        assert len(path) == dist

    def test_each_step_is_valid_plr(self):
        path = tonnetz_path(_make(0, "major"), _make(9, "minor"))
        for op_name, _chord in path:
            assert op_name in ("P", "L", "R")

    def test_identical_chords_empty_path(self):
        ch = _make(5, "major")
        assert tonnetz_path(ch, ch) == []

    def test_path_reaches_target(self):
        a = _make(0, "major")
        b = _make(7, "minor")
        path = tonnetz_path(a, b)
        if path:
            final = path[-1][1]
            assert final.root == b.root
            assert final.quality == b.quality


# ── Neo-Riemannian progression ─────────────────────────────────

class TestNeoProgression:
    def test_correct_length(self):
        start = _make(0, "major")
        end = _make(7, "minor")
        for n in (2, 4, 6, 8):
            prog = neo_riemannian_progression(start, end, n_steps=n, seed=42)
            assert len(prog) == n

    def test_starts_with_start_chord(self):
        start = _make(0, "major")
        end = _make(9, "minor")
        prog = neo_riemannian_progression(start, end, n_steps=5, seed=0)
        assert prog[0].root == start.root
        assert prog[0].quality == start.quality

    def test_ends_with_end_chord(self):
        start = _make(0, "major")
        end = _make(9, "minor")
        prog = neo_riemannian_progression(start, end, n_steps=5, seed=0)
        assert prog[-1].root == end.root
        assert prog[-1].quality == end.quality

    def test_minimum_length_is_2(self):
        start = _make(0, "major")
        end = _make(7, "major")
        prog = neo_riemannian_progression(start, end, n_steps=1, seed=0)
        assert len(prog) >= 2

    def test_all_chords_are_major_or_minor(self):
        start = _make(0, "major")
        end = _make(6, "minor")
        prog = neo_riemannian_progression(start, end, n_steps=8, seed=42)
        for chord in prog:
            assert chord.quality in ("major", "minor")
