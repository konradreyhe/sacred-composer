"""Tests for CompositionBuilder consciousness presets."""

from __future__ import annotations

import pytest

from sacred_composer.builder import CompositionBuilder
from sacred_composer.core import Composition


class TestAvailableStates:
    def test_returns_list_of_six(self):
        states = CompositionBuilder.available_states()
        assert isinstance(states, list)
        assert len(states) == 6

    def test_contains_expected_states(self):
        states = CompositionBuilder.available_states()
        for name in ["deep_sleep", "meditation", "relaxation", "flow", "focus", "energy"]:
            assert name in states


class TestConsciousnessPresets:
    @pytest.mark.parametrize("state", CompositionBuilder.available_states())
    def test_all_states_produce_valid_compositions(self, state):
        piece = CompositionBuilder(title=f"Test {state}").consciousness(state).build()
        assert isinstance(piece, Composition)
        assert piece.info()["total_notes"] > 0

    def test_each_state_has_different_tempo(self):
        tempos = {}
        for state in CompositionBuilder.available_states():
            preset = CompositionBuilder.CONSCIOUSNESS_PRESETS[state]
            tempos[state] = preset["tempo"]
        # All tempos should be unique
        assert len(set(tempos.values())) == len(tempos)

    def test_deep_sleep_is_slowest(self):
        presets = CompositionBuilder.CONSCIOUSNESS_PRESETS
        deep_sleep_tempo = presets["deep_sleep"]["tempo"]
        for name, preset in presets.items():
            if name != "deep_sleep":
                assert preset["tempo"] >= deep_sleep_tempo

    def test_energy_is_fastest(self):
        presets = CompositionBuilder.CONSCIOUSNESS_PRESETS
        energy_tempo = presets["energy"]["tempo"]
        for name, preset in presets.items():
            if name != "energy":
                assert preset["tempo"] <= energy_tempo


class TestInvalidState:
    def test_raises_value_error(self):
        builder = CompositionBuilder(title="Test")
        with pytest.raises(ValueError, match="Unknown consciousness state"):
            builder.consciousness("nonexistent_state")

    def test_error_lists_available_states(self):
        builder = CompositionBuilder(title="Test")
        with pytest.raises(ValueError, match="Available"):
            builder.consciousness("invalid")
