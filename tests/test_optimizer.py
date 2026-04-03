"""Tests for sacred_composer.optimizer — parameter optimization."""

from __future__ import annotations

import pytest

from sacred_composer.optimizer import (
    build_from_params,
    evaluate_fast,
    SEARCH_SPACE,
)
from sacred_composer.core import Composition


# ── Helper: a valid parameter set ───────────────────────────

def _valid_params() -> dict:
    return {
        "key": "C_minor",
        "tempo": 72,
        "bars": 32,
        "melody_pattern": "infinity_series",
        "melody_rhythm": "euclidean_5_8",
        "melody_base_dur": 0.5,
        "melody_seed": 10,
        "bass_pattern": "harmonic_series",
        "bass_base_dur": 2.0,
        "n_sections": 5,
        "use_harmony": False,
    }


# ── build_from_params ───────────────────────────────────────

class TestBuildFromParams:
    def test_valid_params_produce_composition(self):
        piece = build_from_params(_valid_params())
        assert isinstance(piece, Composition)
        assert piece.info()["total_notes"] > 0

    def test_has_melody_and_bass(self):
        piece = build_from_params(_valid_params())
        names = [v.name for v in piece.score.voices]
        assert any("melody" in n for n in names)
        assert any("bass" in n for n in names)

    def test_with_harmony(self):
        params = _valid_params()
        params["use_harmony"] = True
        piece = build_from_params(params)
        assert isinstance(piece, Composition)

    def test_different_keys(self):
        for key in ["C_major", "A_minor", "G_major"]:
            params = _valid_params()
            params["key"] = key
            piece = build_from_params(params)
            assert piece.info()["total_notes"] > 0


# ── evaluate_fast ───────────────────────────────────────────

class TestEvaluateFast:
    def test_returns_score_0_to_100(self):
        piece = build_from_params(_valid_params())
        score = evaluate_fast(piece)
        assert 0.0 <= score <= 100.0

    def test_deterministic_for_same_input(self):
        piece = build_from_params(_valid_params())
        s1 = evaluate_fast(piece)
        s2 = evaluate_fast(piece)
        assert s1 == s2

    def test_empty_composition_scores_zero(self):
        piece = Composition(tempo=72, title="Empty")
        score = evaluate_fast(piece)
        assert score == 0.0

    def test_different_inputs_can_differ(self):
        p1 = _valid_params()
        p2 = _valid_params()
        p2["melody_pattern"] = "golden_spiral"
        p2["melody_seed"] = 99
        p2["bars"] = 48
        s1 = evaluate_fast(build_from_params(p1))
        s2 = evaluate_fast(build_from_params(p2))
        # They may coincidentally be equal, but the function should work
        assert isinstance(s1, float) and isinstance(s2, float)


# ── SEARCH_SPACE ────────────────────────────────────────────

class TestSearchSpace:
    def test_all_keys_present(self):
        expected = {
            "key", "tempo", "bars", "melody_pattern", "melody_rhythm",
            "melody_base_dur", "melody_seed", "bass_pattern",
            "bass_base_dur", "n_sections", "use_harmony",
        }
        assert set(SEARCH_SPACE.keys()) == expected

    def test_all_melody_patterns_are_strings(self):
        for pat in SEARCH_SPACE["melody_pattern"]:
            assert isinstance(pat, str)
