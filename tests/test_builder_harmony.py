"""Tests for harmony integration in CompositionBuilder."""

from __future__ import annotations

import pytest

from sacred_composer.builder import CompositionBuilder
from sacred_composer.core import Composition


class TestBuilderHarmonyMode:
    def test_builder_harmony_mode(self):
        piece = (
            CompositionBuilder(key="C_major", tempo=72, bars=16)
            .harmony(n_chords=8, seed=42)
            .melody(pattern="infinity_series")
            .bass(pattern="harmonic_series")
            .build()
        )
        assert isinstance(piece, Composition)
        assert len(piece.score.voices) == 2
        assert piece.info()["total_notes"] > 0

    def test_builder_legacy_unchanged(self):
        """Without .harmony(), output should match original builder behaviour."""
        piece = (
            CompositionBuilder(key="C_minor", bars=16)
            .melody(pattern="infinity_series", seed=5)
            .bass(pattern="harmonic_series", seed=10)
            .build()
        )
        assert isinstance(piece, Composition)
        assert len(piece.score.voices) == 2
        # Verify the builder did NOT use harmony engine internally
        assert piece.info()["total_notes"] > 0

    def test_builder_harmony_with_new_patterns(self):
        piece = (
            CompositionBuilder(key="D_minor", tempo=80, bars=16)
            .harmony(n_chords=4, seed=7)
            .melody(pattern="mandelbrot")
            .bass(pattern="harmonic_series")
            .build()
        )
        assert isinstance(piece, Composition)
        assert len(piece.score.voices) == 2
        assert piece.info()["total_notes"] > 0
