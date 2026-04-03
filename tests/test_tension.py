"""Tests for sacred_composer.tension — tonal tension model."""

from __future__ import annotations

import pytest

from sacred_composer.tension import (
    fifth_distance,
    surface_dissonance,
    tonal_distance,
    compute_tension,
    target_curve_sonata,
    target_curve_arch,
    target_curve_ramp,
)
from sacred_composer.harmony import Chord


# ── fifth_distance ─────────────────────────────────────────────

class TestFifthDistance:
    def test_c_to_g_is_1(self):
        # C=0, G=7 -> 1 step on circle of fifths
        assert fifth_distance(0, 7) == 1

    def test_c_to_fsharp_is_6(self):
        # C=0, F#=6 -> tritone = 6 steps
        assert fifth_distance(0, 6) == 6

    def test_same_note_is_0(self):
        for pc in range(12):
            assert fifth_distance(pc, pc) == 0

    def test_symmetric(self):
        for a in range(12):
            for b in range(12):
                assert fifth_distance(a, b) == fifth_distance(b, a)

    def test_max_distance_is_6(self):
        for a in range(12):
            for b in range(12):
                assert fifth_distance(a, b) <= 6


# ── surface_dissonance ─────────────────────────────────────────

class TestSurfaceDissonance:
    def test_chord_tone_is_zero(self):
        # C major chord: C=0, E=4, G=7
        assert surface_dissonance(60, [0, 4, 7]) == 0.0  # C4
        assert surface_dissonance(64, [0, 4, 7]) == 0.0  # E4

    def test_scale_tone_is_half(self):
        # D (pitch class 2) is a scale tone but not a chord tone of C major
        assert surface_dissonance(62, [0, 4, 7]) == 0.5

    def test_chromatic_tone_is_one(self):
        # C# (pitch class 1) is chromatic against C major chord/scale
        assert surface_dissonance(61, [0, 4, 7]) == 1.0

    def test_explicit_scale_pcs(self):
        # Provide a custom scale with only C and E
        assert surface_dissonance(62, [0, 4, 7], scale_pcs=[0, 4]) == 1.0
        assert surface_dissonance(62, [0, 4, 7], scale_pcs=[0, 2, 4]) == 0.5


# ── tonal_distance ─────────────────────────────────────────────

class TestTonalDistance:
    def test_same_key_is_zero(self):
        assert tonal_distance(0, 0) == 0.0
        assert tonal_distance(7, 7) == 0.0

    def test_dominant_less_than_tritone(self):
        # C to G (dominant) should be less than C to F# (tritone)
        dom = tonal_distance(0, 7)
        tritone = tonal_distance(0, 6)
        assert dom < tritone

    def test_positive_values(self):
        for a in range(12):
            for b in range(12):
                assert tonal_distance(a, b) >= 0.0


# ── compute_tension ────────────────────────────────────────────

class TestComputeTension:
    def test_tonic_chord_tone_low_tension(self):
        # C4 against C major chord in C major — should be very low
        chord = Chord(root=0, quality="major", pitch_classes=(0, 4, 7), roman="I")
        t = compute_tension(60, chord, home_key_pc=0, current_key_pc=0)
        assert t < 0.15

    def test_chromatic_high_tension(self):
        # C#4 (61) against C major — chromatic, should be high
        chord = Chord(root=0, quality="major", pitch_classes=(0, 4, 7), roman="I")
        t = compute_tension(61, chord, home_key_pc=0, current_key_pc=0)
        assert t > 0.3

    def test_range_0_to_1(self):
        chord = Chord(root=0, quality="major", pitch_classes=(0, 4, 7), roman="I")
        for pitch in range(21, 108):
            t = compute_tension(pitch, chord, home_key_pc=0, current_key_pc=0)
            assert 0.0 <= t <= 1.0

    def test_rest_returns_zero(self):
        assert compute_tension(-1, None, home_key_pc=0, current_key_pc=0) == 0.0

    def test_distant_key_increases_tension(self):
        chord = Chord(root=0, quality="major", pitch_classes=(0, 4, 7), roman="I")
        t_home = compute_tension(60, chord, home_key_pc=0, current_key_pc=0)
        t_far = compute_tension(60, chord, home_key_pc=0, current_key_pc=6)
        assert t_far > t_home


# ── Target curves ──────────────────────────────────────────────

class TestTargetCurves:
    @pytest.mark.parametrize("curve_fn", [target_curve_sonata, target_curve_arch, target_curve_ramp])
    def test_correct_length(self, curve_fn):
        for n in (1, 10, 50, 100):
            assert len(curve_fn(n)) == n

    @pytest.mark.parametrize("curve_fn", [target_curve_sonata, target_curve_arch, target_curve_ramp])
    def test_values_in_0_1(self, curve_fn):
        curve = curve_fn(100)
        for v in curve:
            assert -0.01 <= v <= 1.01, f"Value {v} out of range for {curve_fn.__name__}"

    def test_arch_peaks_near_golden_section(self):
        curve = target_curve_arch(100)
        peak_idx = curve.index(max(curve))
        peak_pos = peak_idx / 99
        # Peak should be near phi inverse (~0.618)
        assert 0.5 < peak_pos < 0.75

    def test_ramp_increases(self):
        curve = target_curve_ramp(50)
        # Overall trend should be increasing: last value > first value
        assert curve[-1] > curve[0]

    def test_sonata_ends_low(self):
        curve = target_curve_sonata(100)
        # Coda should settle low
        assert curve[-1] < 0.2
