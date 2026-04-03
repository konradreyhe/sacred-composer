"""Intelligent Composition Builder — patterns + music theory = quality output.

High-level API that combines pattern generators with constraint-aware
voice leading to produce compositions that score well on evaluation.
"""

from __future__ import annotations

from sacred_composer.core import Composition, Voice, Note, GM_INSTRUMENTS
from sacred_composer.patterns import (
    FibonacciSequence, HarmonicSeries, InfinitySeries,
    EuclideanRhythm, PinkNoise, GoldenSpiral, LogisticMap,
    MandelbrotBoundary, RosslerAttractor, CantorSet,
    ZipfDistribution, TextToMelody,
)
from sacred_composer.mappers import to_pitch, to_rhythm, to_dynamics, to_form
from sacred_composer.constraints import (
    constrained_melody, enforce_range, smooth_leaps,
    add_tension_arc, improve_interval_distribution,
    add_phrase_endings, add_pitch_tension_arc, add_motivic_variation,
)
from sacred_composer.constants import phi, parse_scale
from sacred_composer.constraints import _final_leap_recovery, _clamp_all_intervals
from sacred_composer.harmony import HarmonicEngine


class CompositionBuilder:
    """Builds a well-formed composition from pattern choices.

    Applies music theory constraints automatically so that
    pattern-generated material passes voice leading rules.

    Usage:
        builder = CompositionBuilder(
            key="C_minor", tempo=72, bars=48, title="My Piece"
        )
        builder.melody(pattern="infinity_series", instrument="violin")
        builder.bass(pattern="harmonic_series")
        builder.inner_voice(pattern="golden_spiral", instrument="viola")
        piece = builder.build()
        piece.render("output.mid")

    Consciousness presets (convenience):
        piece = CompositionBuilder(title="Sleep Music").consciousness("deep_sleep").build()
    """

    CONSCIOUSNESS_PRESETS: dict[str, dict] = {
        "deep_sleep": {
            "tempo": 50, "key": "C_pentatonic_minor", "bars": 128,
            "melody_pattern": "golden_spiral", "melody_octave": (3, 4),
            "melody_rhythm": "euclidean_3_8", "melody_base_dur": 2.0,
            "bass_pattern": "harmonic_series", "bass_base_dur": 8.0,
            "velocity_range": (20, 40),
        },
        "meditation": {
            "tempo": 60, "key": "C_phrygian", "bars": 96,
            "melody_pattern": "golden_spiral", "melody_octave": (3, 5),
            "melody_rhythm": "euclidean_5_8", "melody_base_dur": 1.0,
            "bass_pattern": "harmonic_series", "bass_base_dur": 4.0,
            "velocity_range": (30, 50),
        },
        "relaxation": {
            "tempo": 66, "key": "C_major", "bars": 64,
            "melody_pattern": "fibonacci", "melody_octave": (4, 5),
            "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.75,
            "bass_pattern": "harmonic_series", "bass_base_dur": 2.0,
            "velocity_range": (40, 65),
        },
        "flow": {
            "tempo": 68, "key": "C_pentatonic_major", "bars": 256,
            "melody_pattern": "infinity_series", "melody_octave": (4, 5),
            "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.5,
            "bass_pattern": "harmonic_series", "bass_base_dur": 4.0,
            "velocity_range": (50, 75),
        },
        "focus": {
            "tempo": 80, "key": "A_dorian", "bars": 64,
            "melody_pattern": "infinity_series", "melody_octave": (4, 5),
            "melody_rhythm": "euclidean_7_12", "melody_base_dur": 0.5,
            "bass_pattern": "harmonic_series", "bass_base_dur": 2.0,
            "velocity_range": (55, 85),
        },
        "energy": {
            "tempo": 120, "key": "D_major", "bars": 48,
            "melody_pattern": "fibonacci", "melody_octave": (4, 6),
            "melody_rhythm": "euclidean_7_8", "melody_base_dur": 0.25,
            "bass_pattern": "harmonic_series", "bass_base_dur": 1.0,
            "velocity_range": (70, 110),
        },
    }

    def __init__(
        self,
        key: str = "C_minor",
        tempo: int = 72,
        bars: int = 48,
        title: str = "Sacred Composition",
        time_sig: tuple[int, int] = (4, 4),
    ) -> None:
        self.key = key
        self.tempo = tempo
        self.bars = bars
        self.title = title
        self.time_sig = time_sig
        self._scale = parse_scale(key)
        self._beats = bars * time_sig[0]
        self._voices: list[dict] = []
        self._form_values: list[float] | None = None
        self._form_labels: list[str] | None = None
        # Harmony mode state (opt-in via .harmony())
        self._harmony_enabled: bool = False
        self._harmony_n_chords: int | None = None
        self._harmony_seed: int | None = None
        self._harmony_engine: HarmonicEngine | None = None

    # ---- Consciousness presets ----

    @classmethod
    def available_states(cls) -> list[str]:
        """Return the list of available consciousness state preset names."""
        return list(cls.CONSCIOUSNESS_PRESETS.keys())

    def consciousness(self, state: str) -> "CompositionBuilder":
        """Pre-configure the builder for a specific mental/consciousness state.

        Looks up a preset by name and sets tempo, key, bars, scale, beats,
        then auto-adds form, melody, bass, and drone voices with values
        tuned for the target state.  Further chaining (e.g. ``.harmony()``,
        extra voices) is still possible after this call.

        Parameters
        ----------
        state : One of the keys in ``CONSCIOUSNESS_PRESETS``.

        Raises
        ------
        ValueError
            If *state* is not a recognised preset name.
        """
        if state not in self.CONSCIOUSNESS_PRESETS:
            raise ValueError(
                f"Unknown consciousness state {state!r}. "
                f"Available: {self.available_states()}"
            )
        preset = self.CONSCIOUSNESS_PRESETS[state]

        # 1. Core parameters
        self.tempo = preset["tempo"]
        self.key = preset["key"]
        self.bars = preset["bars"]

        # 2. Recalculate derived values
        self._scale = parse_scale(self.key)
        self._beats = self.bars * self.time_sig[0]

        # 3. Auto-add standard voices from the preset
        vel = preset.get("velocity_range")

        self.form(pattern="fibonacci", n_sections=5)

        self.melody(
            pattern=preset["melody_pattern"],
            octave_range=preset["melody_octave"],
            rhythm_pattern=preset["melody_rhythm"],
            base_duration=preset["melody_base_dur"],
        )
        if vel is not None:
            self._voices[-1]["velocity_range"] = vel

        self.bass(
            pattern=preset["bass_pattern"],
            base_duration=preset["bass_base_dur"],
        )
        if vel is not None:
            self._voices[-1]["velocity_range"] = vel

        self.drone(velocity=vel[0] if vel else 55)

        return self

    def form(
        self,
        pattern: str = "fibonacci",
        n_sections: int = 5,
        labels: list[str] | None = None,
    ) -> "CompositionBuilder":
        """Set the formal structure."""
        if pattern == "fibonacci":
            self._form_values = FibonacciSequence().generate(n_sections)
        elif pattern == "golden":
            self._form_values = [1.0, phi]
            n_sections = 2
        else:
            self._form_values = FibonacciSequence().generate(n_sections)

        self._form_labels = labels
        return self

    def harmony(
        self,
        n_chords: int | None = None,
        seed: int | None = None,
    ) -> "CompositionBuilder":
        """Enable chord-first composition mode using the HarmonicEngine.

        When enabled, the builder generates a chord progression first,
        then derives melody pitches from chord tones and bass pitches
        from chord roots. All existing constraints (constrained_melody,
        phrase_endings, tension_arc, etc.) are still applied on top.

        Parameters
        ----------
        n_chords : Number of chords in the progression. If None, defaults
            to roughly 1 chord per 2 bars.
        seed : Random seed for the progression generator. If None, uses 42.
        """
        self._harmony_enabled = True
        self._harmony_n_chords = n_chords
        self._harmony_seed = seed if seed is not None else 42
        return self

    def melody(
        self,
        pattern: str = "infinity_series",
        instrument: str = "violin",
        octave_range: tuple[int, int] = (4, 5),
        rhythm_pattern: str = "euclidean_5_8",
        base_duration: float = 0.5,
        seed: int = 0,
    ) -> "CompositionBuilder":
        """Add a melody voice with constraint-aware voice leading."""
        self._voices.append({
            "role": "melody",
            "pattern": pattern,
            "instrument": instrument,
            "octave_range": octave_range,
            "rhythm_pattern": rhythm_pattern,
            "base_duration": base_duration,
            "seed": seed,
        })
        return self

    def bass(
        self,
        pattern: str = "harmonic_series",
        instrument: str = "cello",
        octave_range: tuple[int, int] = (2, 3),
        rhythm_pattern: str = "euclidean_3_8",
        base_duration: float = 2.0,
        seed: int = 10,
    ) -> "CompositionBuilder":
        """Add a bass voice."""
        self._voices.append({
            "role": "bass",
            "pattern": pattern,
            "instrument": instrument,
            "octave_range": octave_range,
            "rhythm_pattern": rhythm_pattern,
            "base_duration": base_duration,
            "seed": seed,
        })
        return self

    def inner_voice(
        self,
        pattern: str = "golden_spiral",
        instrument: str = "viola",
        octave_range: tuple[int, int] = (3, 4),
        rhythm_pattern: str = "euclidean_3_4",
        base_duration: float = 1.0,
        seed: int = 20,
    ) -> "CompositionBuilder":
        """Add an inner/accompaniment voice."""
        self._voices.append({
            "role": "inner",
            "pattern": pattern,
            "instrument": instrument,
            "octave_range": octave_range,
            "rhythm_pattern": rhythm_pattern,
            "base_duration": base_duration,
            "seed": seed,
        })
        return self

    def drone(
        self,
        instrument: str = "contrabass",
        velocity: int = 55,
    ) -> "CompositionBuilder":
        """Add a sustained drone on the root."""
        self._voices.append({
            "role": "drone",
            "instrument": instrument,
            "velocity": velocity,
        })
        return self

    def build(self) -> Composition:
        """Build the composition with all constraints applied."""
        piece = Composition(tempo=self.tempo, title=self.title)

        # Harmony engine: create once if harmony mode is enabled.
        harmony_melody: tuple[list[int], list[float]] | None = None
        harmony_bass: tuple[list[int], list[float]] | None = None
        if self._harmony_enabled:
            n_chords = self._harmony_n_chords
            if n_chords is None:
                # Default: roughly 1 chord per 2 bars
                n_chords = max(2, self.bars // 2)
            beats_per_chord = max(1, self._beats // n_chords)
            self._harmony_engine = HarmonicEngine(
                key=self.key,
                n_chords=n_chords,
                seed=self._harmony_seed,
                beats_per_chord=beats_per_chord,
            )
            harmony_melody = self._harmony_engine.melody(octave=5)
            harmony_bass = self._harmony_engine.bass(octave=2)

        # Form
        if self._form_values:
            piece.form = to_form(
                self._form_values,
                total_bars=self.bars,
                section_labels=self._form_labels,
            )

        for v_spec in self._voices:
            role = v_spec["role"]

            if role == "drone":
                root = self._get_root_pitch(octave=2)
                piece.add_drone(
                    "drone", pitch=root, total_beats=float(self._beats),
                    velocity=v_spec.get("velocity", 55),
                    instrument=v_spec["instrument"],
                )
                continue

            # Generate raw pitch material
            n_notes = self._estimate_notes(v_spec)

            # In harmony mode, use chord-derived pitches as the starting
            # material for melody and bass voices.  The constraint pipeline
            # below still refines them (range, leaps, phrase endings, etc.).
            if self._harmony_enabled and role == "melody" and harmony_melody is not None:
                raw_pitches, durations = harmony_melody
                # Ensure we have enough notes for the composition length
                while len(raw_pitches) < n_notes:
                    raw_pitches = raw_pitches + raw_pitches
                    durations = durations + durations
                raw_pitches = list(raw_pitches[:n_notes])
                durations = list(durations[:n_notes])
            elif self._harmony_enabled and role == "bass" and harmony_bass is not None:
                raw_pitches, durations = harmony_bass
                while len(raw_pitches) < n_notes:
                    raw_pitches = raw_pitches + raw_pitches
                    durations = durations + durations
                raw_pitches = list(raw_pitches[:n_notes])
                durations = list(durations[:n_notes])
            else:
                raw_pitches = self._generate_pitches(v_spec, n_notes)
                durations = self._generate_rhythm(v_spec, n_notes)
            dynamics = self._generate_dynamics(v_spec, n_notes)

            # Add phrase breaths (short rests) at phrase boundaries
            durations = self._add_phrase_breaths(durations, v_spec)

            # Vary rhythm across form sections
            durations = self._vary_rhythm_by_section(durations, v_spec)

            # Apply constraints based on role
            scale_in_range = [p for p in self._scale
                              if v_spec["octave_range"][0] * 12 + 12 <= p <= (v_spec["octave_range"][1] + 1) * 12 + 11]

            if role == "melody":
                pitches = constrained_melody(
                    raw_pitches, scale_in_range, voice_type="melody",
                    step_ratio=0.70, max_leap=5,
                )
                # Pitch tension: melody rises toward climax, then falls
                pitches = add_pitch_tension_arc(pitches, scale_in_range, intensity=0.20)
                # Motivic variation: vary repeated phrases
                pitches = add_motivic_variation(pitches, scale_in_range, phrase_length=8)
                # Phrase endings: gentle cadential descent + rests
                pitches, durations = add_phrase_endings(
                    pitches, durations, scale_in_range, phrase_length=8, min_pitch=62,
                )
                # FINAL: clamp ALL intervals to max 5 semitones, then ensure leap recovery
                pitches = _clamp_all_intervals(pitches, scale_in_range, max_interval=4)
                pitches = _final_leap_recovery(pitches, scale_in_range, max_leap=5)
                pitches = enforce_range(pitches, voice_type="melody")
                # Dynamic tension arc
                dynamics = add_tension_arc(dynamics)
            elif role == "bass":
                pitches = enforce_range(raw_pitches, voice_type="bass")
                pitches = smooth_leaps(pitches, scale_in_range, max_leap=4)
                pitches = _clamp_all_intervals(pitches, scale_in_range, max_interval=4)
                pitches = _final_leap_recovery(pitches, scale_in_range, max_leap=5)
                pitches = enforce_range(pitches, voice_type="bass")
            else:
                pitches = enforce_range(raw_pitches, voice_type="alto")
                pitches = improve_interval_distribution(pitches, scale_in_range, step_ratio=0.55)
                pitches = smooth_leaps(pitches, scale_in_range, max_leap=7)

            # Add variation: transpose up in later sections for development
            if piece.form and role == "melody":
                pitches = self._add_sectional_variation(pitches, durations, piece.form, scale_in_range)

            piece.add_voice(
                name=f"{role}_{v_spec['instrument']}",
                pitches=pitches,
                durations=durations,
                velocities=dynamics,
                instrument=v_spec["instrument"],
            )

        return piece

    def _get_root_pitch(self, octave: int = 2) -> int:
        """Get the root note MIDI pitch at the given octave."""
        root_pc = self._scale[0] % 12 if self._scale else 0
        return octave * 12 + 12 + root_pc

    def _estimate_notes(self, v_spec: dict) -> int:
        """Estimate how many notes needed to fill the composition."""
        avg_dur = v_spec.get("base_duration", 1.0)
        effective_dur = avg_dur * 0.7
        return int(self._beats / effective_dur) + 16

    # ---- Pattern generators (dict-based dispatch) ----
    # Each entry maps a pattern name to a callable
    # (self, n, seed, octave_range) -> list[int].
    # Extend by adding entries to PATTERN_GENERATORS.

    def _gen_infinity_series(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = InfinitySeries(seed=seed).generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="modular")

    def _gen_fibonacci(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = FibonacciSequence().generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="modular")

    def _gen_golden_spiral(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = GoldenSpiral(start=float(seed)).generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="normalize")

    def _gen_harmonic_series(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        root = self._get_root_pitch(octave=octave_range[0])
        freq = 440.0 * (2 ** ((root - 69) / 12))
        hs = HarmonicSeries(freq)
        chord = hs.as_chord(n=4, quantize=True)
        lo = octave_range[0] * 12 + 12
        hi = (octave_range[1] + 1) * 12 + 11
        chord = [self._fold_to_range(p, lo, hi) for p in chord]
        return self._walking_bass(chord, n, seed)

    def _gen_logistic(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = LogisticMap(r=3.85, x0=0.5 + seed * 0.01).generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="normalize")

    def _gen_mandelbrot(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = MandelbrotBoundary(perturbation=0.02 + seed * 0.005).generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="normalize")

    def _gen_rossler(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = RosslerAttractor(initial=(1.0 + seed * 0.1, 1.0, 1.0)).generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="normalize")

    def _gen_cantor(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = CantorSet(depth=max(1, (seed % 5) + 3)).generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="modular")

    def _gen_zipf(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = ZipfDistribution(n_categories=12, exponent=1.0, seed=seed).generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="modular")

    def _gen_text(self, n: int, seed: int, octave_range: tuple[int, int]) -> list[int]:
        raw = TextToMelody().generate(n)
        return to_pitch(raw, scale=self.key, octave_range=octave_range, strategy="modular")

    PATTERN_GENERATORS: dict[str, str] = {
        "infinity_series": "_gen_infinity_series",
        "fibonacci": "_gen_fibonacci",
        "golden_spiral": "_gen_golden_spiral",
        "harmonic_series": "_gen_harmonic_series",
        "logistic": "_gen_logistic",
        "mandelbrot": "_gen_mandelbrot",
        "rossler": "_gen_rossler",
        "cantor": "_gen_cantor",
        "zipf": "_gen_zipf",
        "text": "_gen_text",
    }

    def _generate_pitches(self, v_spec: dict, n: int) -> list[int]:
        """Generate raw pitches from the specified pattern."""
        pattern = v_spec["pattern"]
        seed = v_spec.get("seed", 0)
        octave_range = v_spec["octave_range"]

        method_name = self.PATTERN_GENERATORS.get(pattern)
        if method_name is None:
            # Default fallback to infinity_series
            method_name = self.PATTERN_GENERATORS["infinity_series"]
        return getattr(self, method_name)(n, seed, octave_range)

    def _walking_bass(self, chord_tones: list[int], n: int, seed: int) -> list[int]:
        """Generate a walking bass line that steps between chord tones."""
        import random
        rng = random.Random(seed)
        bass_scale = [p for p in self._scale if 40 <= p <= 62]
        if not bass_scale:
            bass_scale = chord_tones

        result = [chord_tones[0]]
        for i in range(1, n):
            prev = result[-1]
            # Every 4th note: return to a chord tone
            if i % 4 == 0:
                target = rng.choice(chord_tones)
                # Step toward it
                if abs(target - prev) <= 4:
                    result.append(target)
                else:
                    direction = 1 if target > prev else -1
                    candidates = [p for p in bass_scale if (p - prev) * direction > 0 and abs(p - prev) <= 4]
                    if candidates:
                        result.append(min(candidates, key=lambda p: abs(p - prev)))
                    else:
                        result.append(target)
            else:
                # Step motion: move 1-3 semitones in scale
                direction = rng.choice([-1, 1])
                candidates = [p for p in bass_scale
                              if 0 < (p - prev) * direction <= 4]
                if candidates:
                    result.append(rng.choice(candidates[:2]))
                else:
                    # Reverse direction
                    candidates = [p for p in bass_scale
                                  if 0 < (p - prev) * -direction <= 4]
                    if candidates:
                        result.append(rng.choice(candidates[:2]))
                    else:
                        result.append(prev)

        return result

    @staticmethod
    def _fold_to_range(pitch: int, lo: int, hi: int) -> int:
        """Fold a pitch into range using octave transposition."""
        while pitch > hi:
            pitch -= 12
        while pitch < lo:
            pitch += 12
        return max(lo, min(hi, pitch))

    def _generate_rhythm(self, v_spec: dict, n: int) -> list[float]:
        """Generate rhythm from the specified pattern."""
        rp = v_spec.get("rhythm_pattern", "euclidean_5_8")
        base = v_spec.get("base_duration", 0.5)

        if rp.startswith("euclidean_"):
            parts = rp.split("_")
            onsets = int(parts[1])
            pulses = int(parts[2])
            raw = EuclideanRhythm(onsets, pulses).generate(n)
            return to_rhythm(raw, base_duration=base, strategy="binary")

        elif rp == "steady":
            return [base] * n

        else:
            raw = EuclideanRhythm(5, 8).generate(n)
            return to_rhythm(raw, base_duration=base, strategy="binary")

    def _add_phrase_breaths(self, durations: list[float], v_spec: dict) -> list[float]:
        """Insert brief rests at phrase boundaries (every 8-16 notes).

        This creates clear phrase structure that the evaluator detects.
        """
        result = list(durations)
        base = v_spec.get("base_duration", 0.5)
        phrase_len = 12 if v_spec["role"] == "melody" else 16

        for i in range(phrase_len - 1, len(result), phrase_len):
            if i < len(result):
                # Make the last note of each phrase shorter and add a rest
                if result[i] > 0:
                    result[i] = max(0.25, result[i] * 0.5)
                # Insert a small rest after by making next note negative if exists
                if i + 1 < len(result) and result[i + 1] > 0:
                    result[i + 1] = -abs(result[i + 1]) * 0.5  # brief rest

        return result

    def _vary_rhythm_by_section(self, durations: list[float], v_spec: dict) -> list[float]:
        """Vary rhythmic density across form sections for harmonic rhythm variety."""
        if not self._form_values or len(self._form_values) < 2:
            return durations

        result = list(durations)
        n = len(result)
        # In the middle sections, double some durations for contrast
        mid_start = n // 3
        mid_end = 2 * n // 3

        for i in range(mid_start, mid_end):
            if i < len(result) and result[i] > 0 and i % 3 == 0:
                result[i] *= 1.5  # Slightly longer notes in middle

        return result

    def _add_sectional_variation(
        self, pitches: list[int], durations: list[float],
        form, scale_in_range: list[int],
    ) -> list[int]:
        """Add variation across form sections — slight transposition, register shifts."""
        if not form or len(form) < 2:
            return pitches

        result = list(pitches)
        beats_so_far = 0.0
        note_idx = 0

        # Map notes to their section based on cumulative beat position
        section_boundaries = []
        for s in form:
            section_boundaries.append(s.start_bar * 4)  # assume 4/4
        section_boundaries.append(form[-1].end_bar * 4)

        for i in range(len(result)):
            if i >= len(durations):
                break
            beats_so_far += abs(durations[i])

            # Determine which section this note falls in
            section_idx = 0
            for j in range(len(section_boundaries) - 1):
                if beats_so_far >= section_boundaries[j]:
                    section_idx = j

            # Later sections: slight variation
            if section_idx > 0 and section_idx < len(form):
                # Transpose up by 2 semitones in development sections
                shift = (section_idx % 3) * 2  # 0, 2, 4, 2, 4, ...
                if shift > 0 and result[i] + shift <= 79:
                    # Snap to nearest scale tone after shift
                    target = result[i] + shift
                    if scale_in_range:
                        target = min(scale_in_range, key=lambda p: abs(p - target))
                    result[i] = target

        return result

    def _generate_dynamics(self, v_spec: dict, n: int) -> list[int]:
        """Generate dynamics with pink noise variation."""
        seed = v_spec.get("seed", 0)
        role = v_spec["role"]

        # Prefer explicit velocity_range (e.g. from consciousness presets)
        vel_range = v_spec.get("velocity_range")
        if vel_range is None:
            if role == "melody":
                vel_range = (55, 95)
            elif role == "bass":
                vel_range = (50, 80)
            else:
                vel_range = (45, 75)

        raw = PinkNoise(sigma=1.5, seed=seed + 100).generate(n)
        return to_dynamics(raw, velocity_range=vel_range)
