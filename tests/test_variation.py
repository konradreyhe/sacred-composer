"""Tests for sacred_composer.variation — developing variation transforms."""

from __future__ import annotations

import pytest

from sacred_composer.variation import (
    Motif,
    augment,
    diminish,
    invert,
    retrograde,
    expand_intervals,
    contract_intervals,
    fragment,
    liquidate,
    variation_distance,
    develop_phrase,
    apply_developing_variation,
)


# ── Motif construction ─────────────────────────────────────────

class TestMotif:
    def test_from_pitches_extracts_correct_intervals(self):
        m = Motif.from_pitches([60, 64, 67, 72], [1.0, 1.0, 1.0, 1.0])
        assert m.intervals == [4, 3, 5]

    def test_from_pitches_preserves_durations(self):
        m = Motif.from_pitches([60, 62], [0.5, 1.0])
        assert m.durations == [0.5, 1.0]

    def test_to_pitches_round_trips(self):
        original = [60, 64, 67, 72]
        m = Motif.from_pitches(original, [1.0] * 4)
        assert m.to_pitches(60) == original

    def test_to_pitches_custom_start(self):
        m = Motif(intervals=[2, 3], durations=[1.0, 1.0, 1.0])
        assert m.to_pitches(48) == [48, 50, 53]

    def test_n_notes(self):
        m = Motif(intervals=[1, 2, 3], durations=[1.0] * 4)
        assert m.n_notes == 4

    def test_copy_is_independent(self):
        m = Motif(intervals=[1, 2], durations=[1.0, 1.0, 1.0])
        c = m.copy()
        c.intervals[0] = 99
        c.durations[0] = 99.0
        assert m.intervals[0] == 1
        assert m.durations[0] == 1.0


# ── Transforms ─────────────────────────────────────────────────

class TestTransforms:
    @pytest.fixture
    def motif(self):
        return Motif(intervals=[4, -3, 5, 2], durations=[1.0, 0.5, 1.0, 0.5, 1.0])

    def test_augment_doubles_durations(self, motif):
        result = augment(motif, factor=2.0)
        assert result.durations == [2.0, 1.0, 2.0, 1.0, 2.0]
        assert result.intervals == motif.intervals

    def test_diminish_halves_durations(self, motif):
        result = diminish(motif, factor=0.5)
        assert result.durations == [0.5, 0.25, 0.5, 0.25, 0.5]

    def test_invert_negates_intervals(self, motif):
        result = invert(motif)
        assert result.intervals == [-4, 3, -5, -2]
        assert result.durations == motif.durations

    def test_retrograde_reverses(self, motif):
        result = retrograde(motif)
        assert result.intervals == list(reversed(motif.intervals))
        assert result.durations == list(reversed(motif.durations))

    def test_expand_scales_intervals(self, motif):
        result = expand_intervals(motif, factor=2.0)
        assert result.intervals == [8, -6, 10, 4]

    def test_contract_narrows_intervals(self, motif):
        result = contract_intervals(motif, factor=0.5)
        assert result.intervals == [2, -2, 2, 1]

    def test_fragment_truncates(self, motif):
        result = fragment(motif, n_notes=3)
        assert len(result.intervals) == 2
        assert len(result.durations) == 3
        assert result.intervals == motif.intervals[:2]

    def test_fragment_clamps_to_min_2(self, motif):
        result = fragment(motif, n_notes=1)
        assert result.n_notes == 2

    def test_liquidate_replaces_largest_with_steps(self, motif):
        # Largest absolute interval is 5 (index 2), so it should become +/-2
        result = liquidate(motif, steps=1)
        assert abs(result.intervals[2]) <= 2
        # Direction preserved
        assert result.intervals[2] > 0  # original was +5

    def test_liquidate_multiple_steps(self, motif):
        result = liquidate(motif, steps=2)
        # Two largest intervals (5 and 4) should be replaced
        replaced_count = sum(
            1 for orig, new in zip(motif.intervals, result.intervals) if orig != new
        )
        assert replaced_count == 2

    def test_liquidate_empty_motif(self):
        m = Motif(intervals=[], durations=[1.0])
        result = liquidate(m, steps=1)
        assert result.intervals == []


# ── Variation distance ─────────────────────────────────────────

class TestVariationDistance:
    def test_identical_motifs_zero_distance(self):
        m = Motif(intervals=[4, -3, 5], durations=[1.0, 1.0, 1.0, 1.0])
        assert variation_distance(m, m) == 0.0

    def test_very_different_motifs_high_distance(self):
        a = Motif(intervals=[0, 0, 0], durations=[1.0, 1.0, 1.0, 1.0])
        b = Motif(intervals=[12, -12, 12], durations=[4.0, 4.0, 4.0, 4.0])
        dist = variation_distance(a, b)
        assert dist > 0.5

    def test_symmetric(self):
        a = Motif(intervals=[4, -3, 5], durations=[1.0, 0.5, 1.0, 0.5])
        b = Motif(intervals=[-2, 7, 1], durations=[2.0, 1.0, 0.5, 1.5])
        assert variation_distance(a, b) == pytest.approx(variation_distance(b, a))

    def test_range_0_to_1(self):
        a = Motif(intervals=[1, 2, 3], durations=[1.0, 1.0, 1.0, 1.0])
        b = Motif(intervals=[-11, 11, -11], durations=[0.1, 10.0, 0.1, 10.0])
        dist = variation_distance(a, b)
        assert 0.0 <= dist <= 1.0


# ── develop_phrase ─────────────────────────────────────────────

class TestDevelopPhrase:
    @pytest.fixture
    def motif(self):
        return Motif.from_pitches([60, 64, 67, 72, 71], [1.0] * 5)

    def test_correct_number_of_phrases(self, motif):
        phrases = develop_phrase(motif, n_phrases=5, seed=0)
        assert len(phrases) == 5

    def test_first_phrase_is_original(self, motif):
        phrases = develop_phrase(motif, n_phrases=4, seed=0)
        assert phrases[0].intervals == motif.intervals
        assert phrases[0].durations == motif.durations

    def test_subsequent_phrases_differ(self, motif):
        phrases = develop_phrase(motif, n_phrases=4, seed=42)
        # At least one subsequent phrase should differ from the original
        any_different = any(
            phrases[i].intervals != motif.intervals or phrases[i].durations != motif.durations
            for i in range(1, len(phrases))
        )
        assert any_different

    def test_determinism(self, motif):
        p1 = develop_phrase(motif, n_phrases=6, seed=42)
        p2 = develop_phrase(motif, n_phrases=6, seed=42)
        for a, b in zip(p1, p2):
            assert a.intervals == b.intervals
            assert a.durations == b.durations


# ── apply_developing_variation ─────────────────────────────────

class TestApplyDevelopingVariation:
    def test_first_phrase_unchanged(self):
        pitches = list(range(60, 76))  # 16 notes
        durations = [1.0] * 16
        out_p, out_d = apply_developing_variation(pitches, durations, phrase_length=8, seed=0)
        assert out_p[:8] == pitches[:8]

    def test_subsequent_phrases_differ(self):
        # Use a motif with varied intervals and durations so transforms produce visible changes
        pitches = [60, 64, 67, 72, 71, 67, 64, 60] * 3  # 24 notes
        durations = [1.0, 0.5, 1.0, 0.5, 1.0, 0.5, 1.0, 0.5] * 3
        out_p, _out_d = apply_developing_variation(pitches, durations, phrase_length=8, seed=42)
        # At least one subsequent phrase should differ
        any_different = any(
            out_p[i * 8:(i + 1) * 8] != pitches[i * 8:(i + 1) * 8]
            for i in range(1, 3)
        )
        assert any_different

    def test_output_length_preserved(self):
        pitches = list(range(60, 84))  # 24 notes
        durations = [1.0] * 24
        out_p, out_d = apply_developing_variation(pitches, durations, phrase_length=8, seed=0)
        assert len(out_p) == 24
        assert len(out_d) == 24

    def test_short_input_returned_unchanged(self):
        pitches = [60, 62, 64]
        durations = [1.0, 1.0, 1.0]
        out_p, out_d = apply_developing_variation(pitches, durations, phrase_length=8, seed=0)
        assert out_p == pitches
        assert out_d == durations

    def test_midi_range_clamped(self):
        # Very high pitches to test clamping
        pitches = [120, 122, 124, 126, 127, 125, 123, 121] * 2
        durations = [1.0] * 16
        out_p, _ = apply_developing_variation(pitches, durations, phrase_length=8, seed=0)
        assert all(0 <= p <= 127 for p in out_p)
