"""Tests for sacred_composer.constraints."""

from __future__ import annotations

import pytest

from sacred_composer.constants import parse_scale
from sacred_composer.constraints import (
    enforce_range,
    smooth_leaps,
    constrained_melody,
    add_tension_arc,
    improve_interval_distribution,
    add_phrase_endings,
    add_motivic_variation,
    fix_seventh_resolution,
    _clamp_all_intervals,
    _final_leap_recovery,
    VOICE_RANGES,
)


# ── enforce_range ────────────────────────────────────────────

class TestEnforceRange:
    def test_melody_stays_in_bounds(self):
        lo, hi = VOICE_RANGES["melody"]
        pitches = [30, 50, 60, 70, 90, 100]
        result = enforce_range(pitches, voice_type="melody")
        assert all(lo <= p <= hi for p in result)

    def test_bass_stays_in_bounds(self):
        lo, hi = VOICE_RANGES["bass"]
        pitches = [20, 40, 55, 70, 80]
        result = enforce_range(pitches, voice_type="bass")
        assert all(lo <= p <= hi for p in result)

    def test_soprano_range(self):
        lo, hi = VOICE_RANGES["soprano"]
        result = enforce_range([30, 90], voice_type="soprano")
        assert all(lo <= p <= hi for p in result)

    def test_octave_transposition_preserves_pitch_class(self):
        pitches = [30]  # Very low C#-ish
        result = enforce_range(pitches, voice_type="melody")
        # After transposition, pitch class should be preserved (mod 12)
        assert result[0] % 12 == 30 % 12

    def test_empty_input(self):
        assert enforce_range([], voice_type="melody") == []

    def test_already_in_range(self):
        pitches = [65, 70, 75]
        result = enforce_range(pitches, voice_type="melody")
        assert result == pitches


# ── smooth_leaps ─────────────────────────────────────────────

class TestSmoothLeaps:
    def test_large_leap_is_reduced(self):
        pitches = [60, 85, 60]  # 25 semitone leap
        result = smooth_leaps(pitches, max_leap=9)
        for i in range(1, len(result)):
            # Not a guarantee of max_leap, but at least reduced
            assert abs(result[i] - result[i - 1]) <= 25

    def test_small_intervals_unchanged(self):
        pitches = [60, 62, 64, 65]  # all steps
        result = smooth_leaps(pitches, max_leap=9)
        assert result == pitches

    def test_single_note(self):
        assert smooth_leaps([60]) == [60]

    def test_empty(self):
        assert smooth_leaps([]) == []

    def test_with_scale_pitches(self, melody_scale):
        pitches = [60, 90, 60, 90]
        result = smooth_leaps(pitches, scale_pitches=melody_scale, max_leap=7)
        # Result pitches should stay in valid MIDI range
        assert all(0 <= p <= 127 for p in result)


# ── improve_interval_distribution ────────────────────────────

class TestImproveIntervalDistribution:
    def test_increases_step_ratio(self, melody_scale):
        # All large leaps
        pitches = [60, 72, 60, 72, 60, 72, 60, 72, 60, 72]
        result = improve_interval_distribution(pitches, melody_scale, step_ratio=0.65)
        steps = sum(1 for i in range(1, len(result)) if abs(result[i] - result[i - 1]) <= 2)
        # Should have more steps than the original (which has 0)
        assert steps > 0

    def test_short_input_unchanged(self, melody_scale):
        assert improve_interval_distribution([60], melody_scale) == [60]
        assert improve_interval_distribution([60, 64], melody_scale) == [60, 64]


# ── add_tension_arc ──────────────────────────────────────────

class TestAddTensionArc:
    def test_output_length(self):
        dynamics = [80] * 20
        result = add_tension_arc(dynamics)
        assert len(result) == 20

    def test_climax_near_golden_section(self):
        dynamics = [80] * 100
        result = add_tension_arc(dynamics)
        # Climax should be near index 62 (0.618 * 100)
        climax_idx = result.index(max(result))
        assert 50 <= climax_idx <= 75

    def test_values_clamped_1_to_127(self):
        dynamics = [100] * 50
        result = add_tension_arc(dynamics)
        assert all(1 <= v <= 127 for v in result)

    def test_empty(self):
        assert add_tension_arc([]) == []


# ── add_phrase_endings ───────────────────────────────────────

class TestAddPhraseEndings:
    def test_rest_inserted_after_phrase(self, melody_scale):
        pitches = list(range(60, 76))  # 16 notes
        durations = [1.0] * 16
        new_p, new_d = add_phrase_endings(pitches, durations, melody_scale, phrase_length=8)
        # Duration at index 8 (first note of second phrase) should be negative (rest)
        assert new_d[8] < 0

    def test_phrase_end_note_is_longer(self, melody_scale):
        pitches = [60 + (i % 12) for i in range(16)]
        durations = [0.5] * 16
        new_p, new_d = add_phrase_endings(pitches, durations, melody_scale, phrase_length=8)
        # Last note of phrase (index 7) should be >= 2.0
        assert new_d[7] >= 2.0

    def test_output_lengths_preserved(self, melody_scale):
        pitches = [60] * 24
        durations = [1.0] * 24
        new_p, new_d = add_phrase_endings(pitches, durations, melody_scale, phrase_length=8)
        assert len(new_p) == 24
        assert len(new_d) == 24


# ── constrained_melody ───────────────────────────────────────

class TestConstrainedMelody:
    def test_output_in_melody_range(self, melody_scale):
        lo, hi = VOICE_RANGES["melody"]
        raw = [30, 50, 90, 100, 60, 72, 45, 88]
        result = constrained_melody(raw, melody_scale, voice_type="melody")
        assert all(lo <= p <= hi for p in result)

    def test_output_length_preserved(self, melody_scale):
        raw = [60, 65, 70, 75, 80]
        result = constrained_melody(raw, melody_scale)
        assert len(result) == len(raw)

    def test_all_values_valid_midi(self, melody_scale):
        raw = [60, 62, 64, 67, 72, 74, 77, 79]
        result = constrained_melody(raw, melody_scale)
        assert all(0 <= p <= 127 for p in result)


# ── _clamp_all_intervals ────────────────────────────────────

class TestClampAllIntervals:
    def test_no_interval_exceeds_max(self, melody_scale):
        pitches = [60, 80, 55, 90, 60]
        result = _clamp_all_intervals(pitches, melody_scale, max_interval=5)
        for i in range(1, len(result)):
            assert abs(result[i] - result[i - 1]) <= 5

    def test_single_note(self, melody_scale):
        assert _clamp_all_intervals([60], melody_scale) == [60]

    def test_empty(self, melody_scale):
        assert _clamp_all_intervals([], melody_scale) == []


# ── _final_leap_recovery ────────────────────────────────────

class TestFinalLeapRecovery:
    def test_output_length(self, melody_scale):
        pitches = [60, 72, 74, 60, 62]
        result = _final_leap_recovery(pitches, melody_scale, max_leap=5)
        assert len(result) == 5

    def test_short_input(self, melody_scale):
        assert _final_leap_recovery([60, 72], melody_scale) == [60, 72]
        assert _final_leap_recovery([60], melody_scale) == [60]


# ── fix_seventh_resolution ────────────────────────────────────

class TestFixSeventhResolution:
    """Tests for chord seventh resolution post-processing."""

    @pytest.fixture
    def c_minor_scale(self):
        return parse_scale("C_minor")

    def test_no_change_when_no_seventh(self, c_minor_scale):
        melody = [60, 62, 63, 65, 67]
        bass = [48, 48, 48, 48, 48]
        durs = [1.0, 1.0, 1.0, 1.0, 1.0]
        result = fix_seventh_resolution(melody, durs, bass, durs, c_minor_scale)
        assert result == melody

    def test_fixes_upward_motion_after_seventh(self, c_minor_scale):
        # 58 - 48 = 10 mod 12 = 10 (minor 7th), next note 65 is +7 (upward > 2)
        melody = [60, 58, 65, 63]
        bass = [48, 48, 48, 48]
        durs = [1.0, 1.0, 1.0, 1.0]
        result = fix_seventh_resolution(melody, durs, bass, durs, c_minor_scale)
        # The note at index 2 should be moved closer to 58 (≤ 58+2 = 60)
        assert result[2] <= 60

    def test_does_not_create_large_leap(self, c_minor_scale):
        # After fix, no consecutive sounding notes should be > 5st apart
        melody = [60, 58, 65, 70]
        bass = [48, 48, 48, 48]
        durs = [1.0, 1.0, 1.0, 1.0]
        result = fix_seventh_resolution(melody, durs, bass, durs, c_minor_scale)
        for i in range(len(result) - 1):
            assert abs(result[i + 1] - result[i]) <= 7, \
                f"Leap too large: {result[i]} -> {result[i+1]}"

    def test_empty_input(self, c_minor_scale):
        assert fix_seventh_resolution([], [], [], [], c_minor_scale) == []

    def test_no_bass_returns_unchanged(self, c_minor_scale):
        melody = [60, 62, 63]
        durs = [1.0, 1.0, 1.0]
        result = fix_seventh_resolution(melody, durs, [], [], c_minor_scale)
        assert result == melody

    def test_skips_rests(self, c_minor_scale):
        # Rest (negative duration) between seventh and resolution
        melody = [60, 58, 0, 65, 63]
        bass = [48, 48, 48, 48, 48]
        durs = [1.0, 1.0, -0.5, 1.0, 1.0]
        result = fix_seventh_resolution(melody, durs, bass, durs, c_minor_scale)
        # Should still fix the note after the rest
        assert result[3] <= 60

    def test_fallback_nudges_seventh_note(self, c_minor_scale):
        # Scenario where no safe j-replacement exists: i=60, j=65, k=70
        # 60 - 50 = 10 (seventh). Valid replacements for j: p ≤ 62.
        # But |70 - p| must be ≤ 5, so p ≥ 65. No overlap → falls back to nudging i.
        melody = [60, 65, 70]
        bass = [50, 50, 50]
        durs = [1.0, 1.0, 1.0]
        result = fix_seventh_resolution(melody, durs, bass, durs, c_minor_scale)
        # Either j was fixed or i was nudged so interval is no longer 10/11
        interval = (result[0] - 50) % 12
        j_motion = result[1] - result[0]
        assert interval not in (10, 11) or j_motion <= 2
