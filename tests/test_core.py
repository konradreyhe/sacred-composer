"""Tests for sacred_composer.core — Note, Voice, Score, Composition."""

from __future__ import annotations

import os

import pytest

from sacred_composer.core import Note, Voice, Score, Composition, GM_INSTRUMENTS


# ── Note ─────────────────────────────────────────────────────

class TestNote:
    def test_basic_creation(self):
        n = Note(pitch=60, duration=1.0, velocity=80)
        assert n.pitch == 60
        assert n.duration == 1.0
        assert n.velocity == 80

    def test_is_rest_negative_pitch(self):
        n = Note(pitch=-1, duration=1.0, velocity=0)
        assert n.is_rest is True

    def test_is_rest_negative_duration(self):
        n = Note(pitch=60, duration=-1.0, velocity=80)
        assert n.is_rest is True

    def test_is_rest_normal_note(self):
        n = Note(pitch=60, duration=1.0, velocity=80)
        assert n.is_rest is False

    def test_exact_pitch_no_bend(self):
        n = Note(pitch=69, duration=1.0)
        assert n.exact_pitch == 69.0

    def test_exact_pitch_with_bend(self):
        n = Note(pitch=69, duration=1.0, pitch_bend=0.5)
        assert n.exact_pitch == pytest.approx(69.5)

    def test_default_values(self):
        n = Note(pitch=60, duration=1.0)
        assert n.velocity == 80
        assert n.time == 0.0
        assert n.pitch_bend == 0.0


# ── Voice ────────────────────────────────────────────────────

class TestVoice:
    def test_empty_voice_duration(self):
        v = Voice(name="test")
        assert v.duration == 0.0

    def test_append_and_duration(self):
        v = Voice(name="test")
        v.append(60, 1.0, 80)
        v.append(62, 0.5, 80)
        assert v.duration == pytest.approx(1.5)
        assert len(v.notes) == 2

    def test_append_sets_time(self):
        v = Voice(name="test")
        v.append(60, 2.0)
        v.append(64, 1.0)
        assert v.notes[0].time == 0.0
        assert v.notes[1].time == 2.0

    def test_channel_and_instrument(self):
        v = Voice(name="melody", channel=1, instrument=40)
        assert v.channel == 1
        assert v.instrument == 40


# ── Score ────────────────────────────────────────────────────

class TestScore:
    def test_empty_score(self):
        s = Score()
        assert s.duration == 0.0
        assert len(s.voices) == 0

    def test_add_voice(self):
        s = Score()
        v = Voice(name="melody")
        v.append(60, 4.0)
        s.add_voice(v)
        assert len(s.voices) == 1
        assert s.duration == 4.0

    def test_duration_is_longest_voice(self):
        s = Score()
        v1 = Voice(name="short")
        v1.append(60, 2.0)
        v2 = Voice(name="long")
        v2.append(60, 8.0)
        s.add_voice(v1)
        s.add_voice(v2)
        assert s.duration == 8.0


# ── Composition ──────────────────────────────────────────────

class TestComposition:
    def test_creation(self):
        c = Composition(tempo=120, title="Test")
        assert c.tempo == 120
        assert c.title == "Test"
        assert len(c.score.voices) == 0

    def test_add_voice(self, sample_pitches, sample_durations):
        c = Composition()
        voice = c.add_voice("melody", sample_pitches, sample_durations)
        assert voice.name == "melody"
        assert len(c.score.voices) == 1

    def test_voice_note_count(self, sample_pitches, sample_durations):
        c = Composition()
        c.add_voice("test", sample_pitches, sample_durations)
        assert len(c.score.voices[0].notes) == len(sample_pitches)

    def test_add_drone(self):
        c = Composition()
        v = c.add_drone("bass_drone", pitch=36, total_beats=32.0, velocity=60)
        assert len(v.notes) == 1
        assert v.notes[0].pitch == 36

    def test_info(self, simple_composition):
        info = simple_composition.info()
        assert info["title"] == "Test Composition"
        assert info["tempo"] == 120
        assert info["voices"] == 1
        assert info["total_notes"] > 0

    def test_repr(self, simple_composition):
        r = repr(simple_composition)
        assert "Test Composition" in r

    def test_mismatched_lengths_uses_min(self):
        c = Composition()
        pitches = [60, 62, 64]
        durations = [1.0, 1.0]  # shorter
        c.add_voice("test", pitches, durations)
        assert len(c.score.voices[0].notes) == 2

    def test_rest_handling(self):
        c = Composition()
        pitches = [60, 62]
        durations = [1.0, -0.5]  # second is a rest
        c.add_voice("test", pitches, durations)
        notes = c.score.voices[0].notes
        assert notes[1].is_rest is True
        assert notes[1].pitch == -1

    def test_render_midi(self, simple_composition, tmp_midi_path):
        result = simple_composition.render(tmp_midi_path)
        assert result == tmp_midi_path
        assert os.path.exists(tmp_midi_path)
        # Check file is non-empty and starts with MIDI header
        with open(tmp_midi_path, "rb") as f:
            header = f.read(4)
        assert header == b"MThd"

    def test_render_midi_multiple_voices(self, tmp_midi_path):
        c = Composition(tempo=100)
        c.add_voice("v1", [60, 64, 67], [1.0, 1.0, 1.0])
        c.add_voice("v2", [48, 52, 55], [2.0, 2.0, 2.0])
        result = c.render(tmp_midi_path)
        assert os.path.exists(result)

    def test_render_unsupported_format_raises(self, simple_composition):
        with pytest.raises(ValueError, match="Unsupported format"):
            simple_composition.render("output.xyz")

    def test_auto_channel_assignment(self):
        c = Composition()
        c.add_voice("v0", [60], [1.0])
        c.add_voice("v1", [64], [1.0])
        assert c.score.voices[0].channel == 0
        assert c.score.voices[1].channel == 1

    def test_instrument_string_mapping(self):
        c = Composition()
        v = c.add_voice("test", [60], [1.0], instrument="violin")
        assert v.instrument == GM_INSTRUMENTS["violin"]

    def test_add_voice_microtonal(self):
        c = Composition()
        # 69.5 rounds to 70, so bend = 69.5 - 70 = -0.5
        # 69.3 rounds to 69, so bend = 69.3 - 69 = 0.3
        v = c.add_voice_microtonal(
            "micro", pitches=[69.3, 70.25], durations=[1.0, 1.0]
        )
        assert len(v.notes) == 2
        assert v.notes[0].pitch == 69
        assert v.notes[0].pitch_bend == pytest.approx(0.3, abs=0.01)
