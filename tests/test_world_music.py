"""Tests for sacred_composer.world_music — non-Western music systems."""

from __future__ import annotations

import pytest

from sacred_composer.world_music import (
    Raga,
    RAGA_PRESETS,
    maqam_scale,
    MAQAMAT,
    gamelan_to_midi,
    GAMELAN_TUNINGS,
    cross_rhythm,
    kotekan_split,
)


# ── Raga ────────────────────────────────────────────────────

class TestRaga:
    def test_bhairav_scale_intervals(self):
        bhairav = RAGA_PRESETS["bhairav"]
        assert bhairav.arohana == (0, 1, 4, 5, 7, 8, 11)

    def test_generate_melody_within_scale(self):
        bhairav = RAGA_PRESETS["bhairav"]
        pattern = [0.1, 0.5, 1.2, 0.8, 2.3, 1.0, 0.3, 0.0]
        melody = bhairav.generate_melody(pattern, root=60, octave_range=2)
        assert len(melody) == len(pattern)
        for p in melody:
            assert 0 <= p <= 127

    def test_melody_respects_midi_bounds(self):
        raga = RAGA_PRESETS["yaman"]
        pattern = [float(i * 100) for i in range(20)]
        melody = raga.generate_melody(pattern, root=60, octave_range=2)
        for p in melody:
            assert 0 <= p <= 127

    def test_from_melakarta(self):
        raga = Raga.from_melakarta(29)
        assert raga.name == "melakarta_29"
        assert raga.arohana[0] == 0   # Sa
        assert raga.arohana[4] == 7   # Pa


# ── Maqam ───────────────────────────────────────────────────

class TestMaqam:
    def test_quarter_tone_pitches_are_fractional(self):
        # Bayati has neutral seconds (quarter tones)
        scale = maqam_scale("bayati", root_midi=60)
        has_fractional = any(p != int(p) for p in scale)
        assert has_fractional, "Bayati should contain quarter-tone (fractional) pitches"

    def test_rast_starts_at_root(self):
        scale = maqam_scale("rast", root_midi=60)
        assert scale[0] == 60

    def test_scale_is_ascending(self):
        scale = maqam_scale("hijaz", root_midi=60)
        for i in range(1, len(scale)):
            assert scale[i] > scale[i - 1]


# ── Gamelan ─────────────────────────────────────────────────

class TestGamelan:
    def test_slendro_has_5_notes(self):
        cents = GAMELAN_TUNINGS["slendro_solo"]
        assert len(cents) == 5

    def test_pelog_has_7_notes(self):
        cents = GAMELAN_TUNINGS["pelog_solo"]
        assert len(cents) == 7

    def test_gamelan_to_midi_length(self):
        pitches = gamelan_to_midi("slendro_solo", root_midi=60, octaves=2)
        assert len(pitches) == 5 * 2  # 5 notes * 2 octaves

    def test_gamelan_pitches_are_fractional(self):
        pitches = gamelan_to_midi("slendro_solo", root_midi=60, octaves=1)
        # Gamelan tuning is not equal temperament; some pitches are fractional
        has_fractional = any(p != int(p) for p in pitches)
        assert has_fractional


# ── Polyrhythm ──────────────────────────────────────────────

class TestPolyrhythm:
    def test_cross_rhythm_3_4(self):
        sa, sb = cross_rhythm(3, 4, 12)
        assert len(sa) == 12
        assert len(sb) == 12
        assert sum(sa) == 3
        assert sum(sb) == 4

    def test_cross_rhythm_values_are_binary(self):
        sa, sb = cross_rhythm(5, 7, 35)
        for v in sa + sb:
            assert v in (0, 1)


# ── Kotekan ─────────────────────────────────────────────────

class TestKotekan:
    def test_split_produces_two_parts(self):
        melody = [60, 62, 64, 65, 67, 69, 71, 72]
        durs = [0.5] * 8
        pp, pd, sp, sd = kotekan_split(melody, durs, style="norot")
        assert len(pp) == len(melody)
        assert len(sp) == len(melody)
        assert len(pd) == len(melody)
        assert len(sd) == len(melody)

    def test_ubit_ubitan_complementary(self):
        melody = [60, 62, 64, 65]
        durs = [1.0] * 4
        pp, pd, sp, sd = kotekan_split(melody, durs, style="ubit-ubitan")
        # Even indices: polos plays, sangsih rests
        assert pp[0] == 60
        assert sp[0] == -1  # rest
        # Odd indices: polos rests, sangsih plays
        assert pp[1] == -1  # rest
        assert sp[1] == 62 + 1  # step above
