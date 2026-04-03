"""Tests for sacred_composer.builder — CompositionBuilder."""

from __future__ import annotations

import os

import pytest

from sacred_composer.builder import CompositionBuilder
from sacred_composer.core import Composition


class TestCompositionBuilder:
    def test_basic_build(self):
        builder = CompositionBuilder(key="C_minor", tempo=72, bars=16, title="Test")
        builder.melody(pattern="infinity_series")
        piece = builder.build()
        assert isinstance(piece, Composition)
        assert piece.tempo == 72
        assert len(piece.score.voices) == 1

    def test_fluent_api(self):
        piece = (
            CompositionBuilder(key="C_major", bars=16)
            .melody(pattern="infinity_series")
            .bass(pattern="harmonic_series")
            .build()
        )
        assert len(piece.score.voices) == 2

    def test_with_form(self):
        piece = (
            CompositionBuilder(key="C_minor", bars=32)
            .form(pattern="fibonacci", n_sections=5)
            .melody()
            .build()
        )
        assert len(piece.form) == 5

    def test_drone_voice(self):
        piece = (
            CompositionBuilder(key="C_minor", bars=8)
            .drone(instrument="contrabass")
            .build()
        )
        assert len(piece.score.voices) == 1
        voice = piece.score.voices[0]
        assert len(voice.notes) == 1  # single sustained note

    def test_inner_voice(self):
        piece = (
            CompositionBuilder(key="D_dorian", bars=16)
            .inner_voice(pattern="golden_spiral", instrument="viola")
            .build()
        )
        assert len(piece.score.voices) == 1

    def test_full_ensemble(self):
        piece = (
            CompositionBuilder(key="A_minor", tempo=80, bars=24, title="Ensemble Test")
            .form(pattern="fibonacci", n_sections=3)
            .melody(pattern="infinity_series", instrument="violin")
            .bass(pattern="harmonic_series", instrument="cello")
            .inner_voice(pattern="golden_spiral", instrument="viola")
            .drone(instrument="contrabass")
            .build()
        )
        assert len(piece.score.voices) == 4
        assert piece.title == "Ensemble Test"
        info = piece.info()
        assert info["total_notes"] > 0
        assert info["duration_beats"] > 0

    def test_different_keys(self):
        for key in ["C_major", "F#_harmonic_minor", "Eb_dorian", "A_pentatonic_minor"]:
            piece = (
                CompositionBuilder(key=key, bars=8)
                .melody(pattern="infinity_series")
                .build()
            )
            assert len(piece.score.voices) >= 1

    def test_different_melody_patterns(self):
        for pat in ["infinity_series", "fibonacci", "golden_spiral", "logistic"]:
            piece = (
                CompositionBuilder(key="C_minor", bars=8)
                .melody(pattern=pat)
                .build()
            )
            assert piece.info()["total_notes"] > 0

    def test_render_output(self, tmp_path):
        midi_path = str(tmp_path / "builder_test.mid")
        piece = (
            CompositionBuilder(key="C_minor", bars=8)
            .melody()
            .build()
        )
        piece.render(midi_path)
        assert os.path.exists(midi_path)
        assert os.path.getsize(midi_path) > 0

    def test_seed_determinism(self):
        def make_piece():
            return (
                CompositionBuilder(key="C_minor", bars=8)
                .melody(pattern="infinity_series", seed=42)
                .build()
            )
        p1 = make_piece()
        p2 = make_piece()
        notes1 = [(n.pitch, n.duration) for n in p1.score.voices[0].notes]
        notes2 = [(n.pitch, n.duration) for n in p2.score.voices[0].notes]
        assert notes1 == notes2

    def test_bars_affects_note_count(self):
        short = CompositionBuilder(key="C_minor", bars=4).melody().build()
        long = CompositionBuilder(key="C_minor", bars=64).melody().build()
        short_notes = short.info()["total_notes"]
        long_notes = long.info()["total_notes"]
        assert long_notes > short_notes
