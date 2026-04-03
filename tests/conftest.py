"""Shared fixtures for Sacred Composer tests."""

from __future__ import annotations

import os
import tempfile

import pytest

from sacred_composer.constants import parse_scale
from sacred_composer.core import Composition, Note, Voice, Score


@pytest.fixture
def c_major_scale() -> list[int]:
    """All MIDI notes in C major across the full range."""
    return parse_scale("C_major")


@pytest.fixture
def c_minor_scale() -> list[int]:
    """All MIDI notes in C minor across the full range."""
    return parse_scale("C_minor")


@pytest.fixture
def melody_scale(c_major_scale) -> list[int]:
    """C major notes in the melody range (octave 4-5)."""
    return [n for n in c_major_scale if 60 <= n <= 83]


@pytest.fixture
def bass_scale(c_major_scale) -> list[int]:
    """C major notes in the bass range (octave 2-3)."""
    return [n for n in c_major_scale if 36 <= n <= 59]


@pytest.fixture
def sample_pitches() -> list[int]:
    """A short deterministic pitch sequence for testing."""
    return [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 72, 67, 64, 60]


@pytest.fixture
def sample_durations() -> list[float]:
    """Matching durations for sample_pitches."""
    return [1.0, 0.5, 0.5, 1.0, 0.5, 0.5, 1.0, 0.5, 0.5, 1.0, 0.5, 0.5, 1.0, 0.5, 0.5, 1.0]


@pytest.fixture
def sample_velocities() -> list[int]:
    """Matching velocities for sample_pitches."""
    return [80] * 16


@pytest.fixture
def simple_composition(sample_pitches, sample_durations, sample_velocities) -> Composition:
    """A minimal Composition with one voice."""
    piece = Composition(tempo=120, title="Test Composition")
    piece.add_voice(
        "melody",
        pitches=sample_pitches,
        durations=sample_durations,
        velocities=sample_velocities,
        instrument="piano",
    )
    return piece


@pytest.fixture
def tmp_midi_path(tmp_path):
    """Provide a temporary MIDI file path, cleaned up automatically by pytest."""
    return str(tmp_path / "test_output.mid")
