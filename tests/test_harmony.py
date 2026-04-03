"""Tests for sacred_composer.harmony — harmonic engine and chord grammar."""

from __future__ import annotations

import pytest

from sacred_composer.harmony import (
    Chord,
    HarmonicEngine,
    generate_progression,
    melody_from_chords,
    roman_to_chord,
    voice_lead,
)
from sacred_composer.constants import parse_scale


# ── Progression generation ──────────────────────────────────

class TestGenerateProgression:
    def test_generate_progression_length(self):
        for n in (2, 4, 8, 16):
            prog = generate_progression(n_chords=n, key="C_major", seed=0)
            assert len(prog) == n

    def test_progression_ends_with_cadence(self):
        prog = generate_progression(n_chords=8, key="C_major", seed=42)
        assert prog[-2].roman == "V"
        assert prog[-1].roman == "I"

    def test_progression_determinism(self):
        p1 = generate_progression(n_chords=12, key="D_minor", seed=7)
        p2 = generate_progression(n_chords=12, key="D_minor", seed=7)
        assert [c.roman for c in p1] == [c.roman for c in p2]


# ── roman_to_chord ──────────────────────────────────────────

class TestRomanToChord:
    def test_chord_pitch_classes_I_C_major(self):
        chord = roman_to_chord("I", "C_major")
        assert set(chord.pitch_classes) == {0, 4, 7}

    def test_roman_to_chord_V_C_major(self):
        chord = roman_to_chord("V", "C_major")
        # V in C major -> root G (7), major triad -> {7, 11, 2}
        assert chord.quality == "major"
        assert chord.root == 7

    def test_roman_to_chord_ii_C_major(self):
        chord = roman_to_chord("ii", "C_major")
        # ii in C major -> root D (2), minor triad
        assert chord.quality == "minor"
        assert chord.root == 2

    def test_roman_to_chord_different_keys(self):
        # I in D_major -> root D (2)
        chord = roman_to_chord("I", "D_major")
        assert chord.root == 2
        assert chord.quality == "major"

        # I in A_minor -> root A (9)
        chord = roman_to_chord("I", "A_minor")
        assert chord.root == 9


# ── Voice leading ───────────────────────────────────────────

class TestVoiceLead:
    def test_voice_lead_minimal_movement(self):
        # Start with a C major triad: C4, E4, G4
        current = [60, 64, 67]
        # Move to F major: should stay close
        f_chord = roman_to_chord("IV", "C_major")
        new_voicing = voice_lead(current, f_chord)
        assert len(new_voicing) == 3
        # Total movement should be small (each voice moves at most a few semitones)
        total_movement = sum(abs(a - b) for a, b in zip(current, new_voicing))
        assert total_movement <= 12  # reasonable bound for smooth voice leading


# ── Melody from chords ──────────────────────────────────────

class TestMelodyFromChords:
    def test_melody_from_chords_length(self):
        prog = generate_progression(n_chords=4, key="C_major", seed=0)
        scale = parse_scale("C_major")
        pitches, durations = melody_from_chords(prog, scale, beats_per_chord=4)
        assert len(pitches) == 4 * 4  # 4 chords * 4 beats
        assert len(durations) == len(pitches)

    def test_melody_from_chords_strong_beats_are_chord_tones(self):
        prog = generate_progression(n_chords=4, key="C_major", seed=42)
        scale = parse_scale("C_major")
        pitches, _ = melody_from_chords(prog, scale, beats_per_chord=4, seed=42)
        # Check strong beats (0, 2) for each chord
        for chord_idx, chord in enumerate(prog):
            chord_pcs = set(chord.pitch_classes)
            for beat in (0, 2):
                note_idx = chord_idx * 4 + beat
                pitch_class = pitches[note_idx] % 12
                assert pitch_class in chord_pcs, (
                    f"Beat {beat} of chord {chord_idx} ({chord.roman}): "
                    f"pitch class {pitch_class} not in {chord_pcs}"
                )


# ── HarmonicEngine ──────────────────────────────────────────

class TestHarmonicEngine:
    def test_harmonic_engine_creates_composition(self):
        engine = HarmonicEngine(key="C_major", n_chords=8, seed=42)
        piece = engine.to_composition()
        assert len(piece.score.voices) == 3  # melody, inner, bass

    def test_harmonic_engine_determinism(self):
        e1 = HarmonicEngine(key="G_major", n_chords=8, seed=99)
        e2 = HarmonicEngine(key="G_major", n_chords=8, seed=99)
        p1 = e1.to_composition()
        p2 = e2.to_composition()
        for v1, v2 in zip(p1.score.voices, p2.score.voices):
            notes1 = [(n.pitch, n.duration) for n in v1.notes]
            notes2 = [(n.pitch, n.duration) for n in v2.notes]
            assert notes1 == notes2
