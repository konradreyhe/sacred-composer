"""Tests for sacred_composer.adaptive — adaptive music engine."""

from __future__ import annotations

import pytest

from sacred_composer.adaptive import (
    GameState,
    state_to_params,
    AdaptiveComposer,
    generate_soundtrack,
    ENVIRONMENT_SCALES,
)
from sacred_composer.core import Composition


# ── GameState ───────────────────────────────────────────────

class TestGameState:
    def test_default_values(self):
        gs = GameState()
        assert gs.danger == 0.0
        assert gs.energy == 0.5
        assert gs.environment == "forest"
        assert gs.time_of_day == 12.0
        assert gs.health == 1.0
        assert gs.speed == 0.5
        assert gs.custom == {}

    def test_custom_values(self):
        gs = GameState(danger=0.8, energy=0.9, environment="desert", speed=1.0)
        assert gs.danger == 0.8
        assert gs.energy == 0.9
        assert gs.environment == "desert"
        assert gs.speed == 1.0

    def test_danger_range(self):
        low = GameState(danger=0.0)
        high = GameState(danger=1.0)
        assert low.danger == 0.0
        assert high.danger == 1.0

    def test_custom_dict(self):
        gs = GameState(custom={"weather": "rain", "npc_count": 5})
        assert gs.custom["weather"] == "rain"
        assert gs.custom["npc_count"] == 5


# ── state_to_params ─────────────────────────────────────────

class TestStateToParams:
    def test_forest_maps_to_a_minor(self):
        gs = GameState(environment="forest")
        params = state_to_params(gs)
        assert params["scale"] == "A_minor"

    def test_unknown_environment_falls_back(self):
        gs = GameState(environment="volcano")
        params = state_to_params(gs)
        assert params["scale"] == "A_minor"

    def test_danger_maps_to_r_value(self):
        low = state_to_params(GameState(danger=0.0))
        high = state_to_params(GameState(danger=1.0))
        assert low["r_value"] == pytest.approx(2.5, abs=0.01)
        assert high["r_value"] == pytest.approx(3.99, abs=0.01)

    def test_energy_maps_to_tempo(self):
        calm = state_to_params(GameState(energy=0.0))
        intense = state_to_params(GameState(energy=1.0))
        assert calm["tempo"] < intense["tempo"]

    def test_tempo_within_bounds(self):
        for energy in [0.0, 0.5, 1.0]:
            params = state_to_params(GameState(energy=energy))
            assert 40 <= params["tempo"] <= 180

    def test_bass_always_in_layers(self):
        params = state_to_params(GameState(energy=0.0, danger=0.0))
        assert "bass" in params["active_layers"]


# ── AdaptiveComposer ────────────────────────────────────────

class TestAdaptiveComposer:
    def test_creates_valid_chunk(self):
        ac = AdaptiveComposer(seed=42)
        chunk = ac.render_chunk(beats=8)
        assert isinstance(chunk, Composition)
        assert len(chunk.score.voices) >= 1

    def test_bass_always_active(self):
        ac = AdaptiveComposer(seed=42)
        ac.update(GameState(energy=0.0, danger=0.0))
        assert "bass" in ac.active_layers

    def test_tension_only_at_high_danger(self):
        ac = AdaptiveComposer(seed=42)
        ac.update(GameState(danger=0.1))
        assert "tension" not in ac.active_layers
        ac.update(GameState(danger=0.8))
        assert "tension" in ac.active_layers

    def test_determinism_with_seed(self):
        def make_chunk():
            ac = AdaptiveComposer(seed=99)
            ac.update(GameState(danger=0.5, energy=0.7))
            return ac.render_chunk(beats=8)

        c1 = make_chunk()
        c2 = make_chunk()
        notes1 = [(n.pitch, n.duration) for n in c1.score.voices[0].notes]
        notes2 = [(n.pitch, n.duration) for n in c2.score.voices[0].notes]
        assert notes1 == notes2

    def test_chunk_has_notes(self):
        ac = AdaptiveComposer(seed=42)
        ac.update(GameState(energy=0.8, danger=0.5))
        chunk = ac.render_chunk(beats=16)
        total_notes = sum(len(v.notes) for v in chunk.score.voices)
        assert total_notes > 0


# ── generate_soundtrack ─────────────────────────────────────

class TestGenerateSoundtrack:
    def test_produces_valid_composition(self):
        states = [
            (0.0, GameState(danger=0.0, energy=0.3)),
            (16.0, GameState(danger=0.5, energy=0.7)),
            (32.0, GameState(danger=0.9, energy=1.0)),
        ]
        piece = generate_soundtrack(states, chunk_beats=8, seed=42)
        assert isinstance(piece, Composition)
        assert len(piece.score.voices) >= 1
        assert piece.info()["total_notes"] > 0

    def test_handles_single_state(self):
        states = [(0.0, GameState())]
        piece = generate_soundtrack(states, chunk_beats=8, seed=42)
        assert isinstance(piece, Composition)
        assert len(piece.score.voices) >= 1

    def test_empty_states_returns_empty(self):
        piece = generate_soundtrack([], chunk_beats=8, seed=42)
        assert isinstance(piece, Composition)
        assert piece.title == "Empty Adaptive Soundtrack"
