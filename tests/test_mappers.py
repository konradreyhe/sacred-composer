"""Tests for sacred_composer.mappers."""

from __future__ import annotations

import math

import pytest

from sacred_composer.mappers import (
    to_pitch,
    to_pitch_microtonal,
    to_rhythm,
    to_dynamics,
    to_form,
    FormSection,
)
from sacred_composer.constants import parse_scale


# ── to_pitch ─────────────────────────────────────────────────

class TestToPitch:
    def test_output_length(self, c_major_scale):
        values = [0.0, 1.0, 2.0, 3.0, 4.0]
        result = to_pitch(values, scale="C_major", octave_range=(4, 5))
        assert len(result) == 5

    def test_modular_strategy_wraps(self):
        values = list(range(20))
        result = to_pitch([float(v) for v in values], scale="C_major", octave_range=(4, 4), strategy="modular")
        # All results should be in C major within octave 4
        c_major_oct4 = [n for n in parse_scale("C_major") if 60 <= n <= 83]
        for p in result:
            assert p in c_major_oct4

    def test_normalize_strategy_spans_range(self):
        values = [0.0, 50.0, 100.0]
        result = to_pitch(values, scale="C_major", octave_range=(4, 5), strategy="normalize")
        # First should be lowest, last should be highest
        assert result[0] <= result[2]

    def test_nearest_strategy(self):
        # Value 61 should map to nearest C major note (either 60 C or 62 D)
        result = to_pitch([61.0], scale="C_major", octave_range=(4, 5), strategy="nearest")
        assert result[0] in (60, 62)

    def test_pitch_set_override(self):
        result = to_pitch([0.0, 1.0, 2.0], pitch_set=[60, 67, 72], strategy="modular")
        assert all(p in (60, 67, 72) for p in result)

    def test_empty_input(self):
        assert to_pitch([], scale="C_major") == []

    def test_range_clamping(self):
        """All pitches must fall within the specified octave range."""
        values = [float(v) for v in range(50)]
        result = to_pitch(values, scale="C_major", octave_range=(3, 6), strategy="modular")
        lo = 3 * 12 + 12  # 48
        hi = (6 + 1) * 12 + 11  # 95
        for p in result:
            assert lo <= p <= hi

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown pitch strategy"):
            to_pitch([1.0], strategy="bogus")


# ── to_pitch_microtonal ─────────────────────────────────────

class TestToPitchMicrotonal:
    def test_a440_is_midi_69(self):
        result = to_pitch_microtonal([440.0])
        assert result[0] == pytest.approx(69.0)

    def test_zero_frequency(self):
        result = to_pitch_microtonal([0.0])
        assert result[0] == -1.0

    def test_negative_frequency(self):
        result = to_pitch_microtonal([-100.0])
        assert result[0] == -1.0

    def test_output_length(self):
        freqs = [220.0, 440.0, 880.0]
        assert len(to_pitch_microtonal(freqs)) == 3

    def test_octave_doubles_frequency(self):
        result = to_pitch_microtonal([220.0, 440.0])
        assert result[1] - result[0] == pytest.approx(12.0)


# ── to_rhythm ────────────────────────────────────────────────

class TestToRhythm:
    def test_proportional_output_length(self):
        values = [1.0, 2.0, 0.5, 3.0]
        result = to_rhythm(values, strategy="proportional")
        assert len(result) == 4

    def test_binary_onset_or_rest(self):
        values = [0.0, 0.3, 0.6, 1.0]
        result = to_rhythm(values, base_duration=1.0, strategy="binary")
        # 0.0 and 0.3 <= 0.5 -> rest (-1.0), 0.6 and 1.0 > 0.5 -> 1.0
        assert result[0] < 0  # rest
        assert result[1] < 0  # rest
        assert result[2] > 0  # onset
        assert result[3] > 0  # onset

    def test_proportional_minimum_duration(self):
        # Very small value should be clamped to 0.125
        result = to_rhythm([0.001], base_duration=1.0, strategy="proportional")
        assert result[0] >= 0.125

    def test_quantize_snaps_to_standard(self):
        result = to_rhythm([0.9], base_duration=1.0, strategy="quantize")
        standard = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
        assert result[0] in standard

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown rhythm strategy"):
            to_rhythm([1.0], strategy="invalid")

    def test_empty_input(self):
        assert to_rhythm([], strategy="binary") == []


# ── to_dynamics ──────────────────────────────────────────────

class TestToDynamics:
    def test_normalize_within_range(self):
        values = [0.0, 5.0, 10.0]
        result = to_dynamics(values, velocity_range=(40, 110), strategy="normalize")
        assert all(40 <= v <= 110 for v in result)

    def test_normalize_min_maps_to_low(self):
        values = [0.0, 5.0, 10.0]
        result = to_dynamics(values, velocity_range=(40, 110), strategy="normalize")
        assert result[0] == 40
        assert result[2] == 110

    def test_threshold_produces_two_levels(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = to_dynamics(values, velocity_range=(40, 100), strategy="threshold")
        assert set(result).issubset({40, 100})

    def test_absolute_clamps_to_1_127(self):
        values = [0.0, 50.0, 200.0]
        result = to_dynamics(values, strategy="absolute")
        assert result[0] == 1  # clamped up from 0
        assert result[1] == 50
        assert result[2] == 127  # clamped down from 200

    def test_empty_input(self):
        assert to_dynamics([], strategy="normalize") == []

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown dynamics strategy"):
            to_dynamics([1.0], strategy="bad")


# ── to_form ──────────────────────────────────────────────────

class TestToForm:
    def test_bar_sum_equals_total(self):
        values = [5.0, 8.0, 13.0, 8.0, 5.0]
        sections = to_form(values, total_bars=39)
        total = sum(s.bars for s in sections)
        assert total == 39

    def test_correct_number_of_sections(self):
        values = [1.0, 2.0, 3.0]
        sections = to_form(values, total_bars=30)
        assert len(sections) == 3

    def test_section_labels_auto(self):
        sections = to_form([1.0, 2.0, 3.0], total_bars=12)
        labels = [s.label for s in sections]
        assert labels == ["A", "B", "C"]

    def test_custom_labels(self):
        sections = to_form([1.0, 1.0], total_bars=10, section_labels=["Intro", "Main"])
        assert sections[0].label == "Intro"
        assert sections[1].label == "Main"

    def test_sections_are_contiguous(self):
        sections = to_form([3.0, 5.0, 8.0], total_bars=32)
        for i in range(1, len(sections)):
            assert sections[i].start_bar == sections[i - 1].end_bar

    def test_empty_values(self):
        sections = to_form([], total_bars=20)
        assert len(sections) == 1
        assert sections[0].bars == 20

    def test_minimum_one_bar_per_section(self):
        # Very small weight should still get at least 1 bar
        sections = to_form([0.001, 100.0], total_bars=10)
        assert all(s.bars >= 1 for s in sections)
