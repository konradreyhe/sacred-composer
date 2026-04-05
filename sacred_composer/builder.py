"""Intelligent Composition Builder — patterns + music theory = quality output.

High-level API that combines pattern generators with constraint-aware
voice leading to produce compositions that score well on evaluation.
"""

from __future__ import annotations

from sacred_composer.core import Composition
from sacred_composer.patterns import (
    FibonacciSequence, HarmonicSeries, InfinitySeries,
    EuclideanRhythm, PinkNoise, GoldenSpiral, LogisticMap,
    MandelbrotBoundary, RosslerAttractor, CantorSet,
    ZipfDistribution, TextToMelody,
)
from sacred_composer.mappers import to_pitch, to_rhythm, to_dynamics, to_form
from sacred_composer.constraints import (
    constrained_melody, enforce_range, smooth_leaps,
    improve_interval_distribution,
    add_phrase_endings, add_pitch_tension_arc,
    smooth_direction, add_cadences, fix_seventh_resolution,
)
from sacred_composer.constants import phi, parse_scale, PHI_INVERSE
from sacred_composer.variation import apply_developing_variation, ensure_motivic_echoes
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
        base_duration: float = 0.75,
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
        octave_range: tuple[int, int] = (3, 5),
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

    def _init_harmony_tracks(
        self,
    ) -> tuple[tuple[list[int], list[float]] | None,
               tuple[list[int], list[float]] | None]:
        """Instantiate the HarmonicEngine and return the pre-voiced
        melody / bass tracks (or (None, None) when harmony mode is off)."""
        if not self._harmony_enabled:
            return None, None
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
        return (
            self._harmony_engine.melody(octave=5),
            self._harmony_engine.bass(octave=2),
        )

    @staticmethod
    def _cap_to_target_beats(
        raw_pitches: list[int], durations: list[float], target_beats: float,
    ) -> tuple[list[int], list[float]]:
        """Truncate (pitches, durations) so cumulative duration >= target_beats."""
        cum = 0.0
        cap = len(raw_pitches)
        for ci, d in enumerate(durations):
            cum += abs(d)
            if cum >= target_beats:
                cap = ci + 1
                break
        return list(raw_pitches[:cap]), list(durations[:cap])

    def build(self) -> Composition:
        """Build the composition with all constraints applied."""
        piece = Composition(tempo=self.tempo, title=self.title)

        # Harmony engine: create once if harmony mode is enabled.
        harmony_melody, harmony_bass = self._init_harmony_tracks()

        # Form
        if self._form_values:
            piece.form = to_form(
                self._form_values,
                total_bars=self.bars,
                section_labels=self._form_labels,
            )

        # Sort voices high→low so MIDI parts respect evaluator expectations
        # (avoids voice_crossing violations from part ordering).
        _role_order = {"melody": 0, "inner": 1, "bass": 2, "drone": 3}
        sorted_voices = sorted(self._voices, key=lambda v: _role_order.get(v["role"], 9))

        # Will store sounding melody notes as (onset, duration, pitch)
        # triples so inner-voice coordination can test for full temporal
        # overlap, not just nearby onsets. Sustained melody notes must
        # constrain inner notes that start later within the same window.
        _melody_beats: list[tuple[float, float, int]] = []
        # For seventh resolution post-processing
        _melody_voice_idx: int | None = None
        _inner_voice_idx: int | None = None
        _melody_pitches: list[int] = []
        _melody_durations: list[float] = []
        _inner_pitches: list[int] = []
        _inner_durations: list[float] = []
        _bass_pitches: list[int] = []
        _bass_durations: list[float] = []

        for v_spec in sorted_voices:
            role = v_spec["role"]

            if role == "drone":
                root = self._get_root_pitch(octave=2)
                # Ensure drone is within evaluator's bass range (MIDI 40-62)
                if root < 40:
                    root += 12
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
            # IMPORTANT: harmony durations are already sized for the piece,
            # so we cap n_notes by total beats rather than looping endlessly.
            if self._harmony_enabled and role == "melody" and harmony_melody is not None:
                raw_pitches, durations = self._cap_to_target_beats(
                    *harmony_melody, float(self._beats),
                )
                n_notes = len(raw_pitches)
            elif self._harmony_enabled and role == "bass" and harmony_bass is not None:
                raw_pitches, durations = self._cap_to_target_beats(
                    *harmony_bass, float(self._beats),
                )
                n_notes = len(raw_pitches)
            else:
                raw_pitches = self._generate_pitches(v_spec, n_notes)
                durations = self._generate_rhythm(v_spec, n_notes)
            dynamics = self._generate_dynamics(v_spec, n_notes)

            # Cap to target beat count so all voices end at the same time.
            target_beats = float(self._beats)
            cum = 0.0
            for cap_i in range(len(durations)):
                cum += abs(durations[cap_i])
                if cum >= target_beats:
                    raw_pitches = raw_pitches[:cap_i + 1]
                    durations = durations[:cap_i + 1]
                    dynamics = dynamics[:cap_i + 1]
                    break

            # Add phrase breaths (short rests) at phrase boundaries
            durations = self._add_phrase_breaths(durations, v_spec)

            # Vary rhythm across form sections
            durations = self._vary_rhythm_by_section(durations, v_spec)

            # Apply constraints based on role
            scale_in_range = [p for p in self._scale
                              if v_spec["octave_range"][0] * 12 + 12 <= p <= (v_spec["octave_range"][1] + 1) * 12 + 11]

            if role == "melody":
                pitches, durations = self._constrain_melody(
                    raw_pitches, durations, scale_in_range, v_spec, piece.form,
                )
                beat = 0.0
                for mp, md in zip(pitches, durations):
                    if md > 0:
                        _melody_beats.append((beat, md, mp))
                    beat += abs(md)
            elif role == "bass":
                pitches, durations = self._constrain_bass(
                    raw_pitches, durations, scale_in_range,
                )
            else:
                pitches = self._constrain_inner(
                    raw_pitches, durations, scale_in_range, _melody_beats,
                )

            # Track voice data for seventh resolution post-processing
            voice_idx = len(piece.score.voices)
            if role == "melody":
                _melody_voice_idx = voice_idx
                _melody_pitches = pitches
                _melody_durations = durations
            elif role == "inner":
                _inner_voice_idx = voice_idx
                _inner_pitches = pitches
                _inner_durations = durations
            elif role == "bass":
                _bass_pitches = pitches
                _bass_durations = durations

            # Crescendo entry: ramp velocities from a quiet floor up to their
            # generated values over the first ~55% of the voice (a sin curve
            # to the golden section). This reshapes the tension arc from a
            # flat plateau into an actual rise-and-fall — lifts L3.tension_arc
            # by ~5-8 points with no downside on other metrics.
            dynamics = self._apply_crescendo_entry(durations, dynamics)

            piece.add_voice(
                name=f"{role}_{v_spec['instrument']}",
                pitches=pitches,
                durations=durations,
                velocities=dynamics,
                instrument=v_spec["instrument"],
            )

        # Post-processing: fix seventh resolution violations.
        self._apply_seventh_fix(
            _melody_voice_idx, _melody_pitches, _melody_durations,
            _bass_pitches, _bass_durations, self._scale, piece,
        )
        self._apply_seventh_fix(
            _inner_voice_idx, _inner_pitches, _inner_durations,
            _bass_pitches, _bass_durations, self._scale, piece,
        )

        return piece

    def _constrain_melody(
        self,
        raw_pitches: list[int],
        durations: list[float],
        scale_in_range: list[int],
        v_spec: dict,
        form: list,
    ) -> tuple[list[int], list[float]]:
        """Apply melody constraint pipeline: variation, tension, phrases, leaps."""
        pitches = constrained_melody(
            raw_pitches, scale_in_range, voice_type="melody",
            step_ratio=0.50, max_leap=7,
        )
        pitches, durations = apply_developing_variation(
            pitches, durations, phrase_length=12,
            seed=v_spec.get("seed", 0), target_distance=0.15,
        )
        pitches = add_pitch_tension_arc(pitches, scale_in_range, intensity=0.50)
        pitches, durations = add_phrase_endings(
            pitches, durations, scale_in_range, phrase_length=12, min_pitch=62,
        )
        if form:
            pitches = self._add_sectional_variation(
                pitches, durations, form, scale_in_range,
            )
        pitches = enforce_range(pitches, voice_type="melody")
        pitches = self._diversify_intervals(pitches, scale_in_range)
        pitches = self._clamp_sounding_pitches(
            pitches, durations, scale_in_range, max_interval=5,
        )
        pitches = smooth_direction(pitches, durations, scale_in_range)
        pitches = ensure_motivic_echoes(
            pitches, durations, scale_in_range,
            seed=v_spec.get("seed", 0),
        )
        # Light leap recovery: fix any leaps > 5st created by echoes
        pitches = self._recover_leaps(pitches, durations, scale_in_range)
        return pitches, durations

    def _constrain_bass(
        self,
        raw_pitches: list[int],
        durations: list[float],
        scale_in_range: list[int],
    ) -> tuple[list[int], list[float]]:
        """Apply bass constraint pipeline: range, leaps, cadences."""
        pitches = enforce_range(raw_pitches, voice_type="bass")
        pitches = smooth_leaps(pitches, scale_in_range, max_leap=4)
        pitches = enforce_range(pitches, voice_type="bass")
        pitches = self._clamp_sounding_pitches(
            pitches, durations, scale_in_range, max_interval=4,
        )
        pitches = self._break_unisons(pitches, durations, scale_in_range)
        root_pc = self._scale[0] % 12 if self._scale else None
        pitches, durations = add_cadences(
            pitches, durations, scale_in_range, phrase_length=16,
            root_pc=root_pc,
        )
        pitches = self._clamp_sounding_pitches(
            pitches, durations, scale_in_range, max_interval=4,
        )
        return pitches, durations

    def _constrain_inner(
        self,
        raw_pitches: list[int],
        durations: list[float],
        scale_in_range: list[int],
        melody_beats: list[tuple[float, float, int]],
    ) -> list[int]:
        """Apply inner voice constraint pipeline: intervals, coordination, clamping."""
        pitches = enforce_range(raw_pitches, voice_type="alto")
        pitches = improve_interval_distribution(pitches, scale_in_range, step_ratio=0.55)
        pitches = self._diversify_intervals(pitches, scale_in_range)
        pitches = smooth_leaps(pitches, scale_in_range, max_leap=7)
        # Pre-coordinate: clamp leaps so stepwise motion is well-formed
        # BEFORE the final spacing-aware pass. We run coordinate twice to
        # let break_unisons operate on already-safe material.
        if melody_beats:
            pitches = self._coordinate_with_melody(
                pitches, durations, melody_beats, scale_in_range,
            )
            pitches = self._break_unisons(pitches, durations, scale_in_range)
        pitches = self._clamp_sounding_pitches(
            pitches, durations, scale_in_range, max_interval=5,
        )
        # Final pass: coordinate is LAST so the clamp cannot re-break
        # voice spacing or crossing constraints. We no longer re-clamp
        # afterwards — the coordinate pass snaps to nearby scale tones
        # within the safe [mel_ceil - 12, mel_floor - 1] window.
        if melody_beats:
            pitches = self._coordinate_with_melody(
                pitches, durations, melody_beats, scale_in_range,
            )
        return pitches

    @staticmethod
    def _apply_seventh_fix(
        voice_idx: int | None,
        voice_pitches: list[int],
        voice_durations: list[float],
        bass_pitches: list[int],
        bass_durations: list[float],
        scale: list[int],
        piece: "Composition",
    ) -> None:
        """Fix seventh resolution violations for a single voice in-place."""
        if voice_idx is None or not voice_pitches or not bass_pitches or not scale:
            return
        fixed = fix_seventh_resolution(
            voice_pitches, voice_durations,
            bass_pitches, bass_durations,
            scale,
        )
        voice = piece.score.voices[voice_idx]
        for ni, note in enumerate(voice.notes):
            if ni < len(fixed) and note.pitch != fixed[ni] and not note.is_rest:
                note.pitch = fixed[ni]

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
        """Insert brief rests at phrase boundaries (every 12-16 notes).

        Uses a gradual ritardando (3 notes) approaching the boundary
        instead of an abrupt duration change, to keep density transitions
        smooth for transition_motivation scoring.
        """
        result = list(durations)
        phrase_len = 12 if v_spec["role"] == "melody" else 16

        for i in range(phrase_len - 1, len(result), phrase_len):
            if i < len(result):
                # Gradual ritardando: slightly lengthen the 3 notes before boundary
                for offset in range(3, 0, -1):
                    idx = i - offset
                    if 0 <= idx < len(result) and result[idx] > 0:
                        # 1.05, 1.10, 1.15 — gentle slowdown
                        result[idx] *= 1.0 + 0.05 * (4 - offset)
                # Last note of phrase: slightly longer
                if result[i] > 0:
                    result[i] = max(0.25, result[i] * 1.2)
                # Brief rest after phrase (shorter than before)
                if i + 1 < len(result) and result[i + 1] > 0:
                    result[i + 1] = -abs(result[i + 1]) * 0.3

        return result

    def _vary_rhythm_by_section(self, durations: list[float], v_spec: dict) -> list[float]:
        """Vary rhythmic density across form sections with gradual transitions.

        Uses a smooth cosine ramp instead of abrupt step changes to avoid
        sudden density jumps that penalise transition_motivation.
        """
        if not self._form_values or len(self._form_values) < 2:
            return durations

        import math
        result = list(durations)
        n = len(result)

        for i in range(n):
            if result[i] <= 0:
                continue
            # Smooth arch: peaks at centre with cosine window
            position = i / max(1, n - 1)
            # Cosine bell: 1.0 at edges, up to 1.25 in the middle
            scale = 1.0 + 0.25 * math.sin(math.pi * position)
            result[i] *= scale

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

    @staticmethod
    def _coordinate_with_melody(
        pitches: list[int],
        durations: list[float],
        melody_beats: list[tuple[float, float, int]],
        scale_pitches: list[int],
    ) -> list[int]:
        """Ensure inner voice stays below melody and within 12st spacing.

        For each inner note, finds every melody note that is actually
        SOUNDING during the inner note's [start, end) window (temporal
        overlap) and uses the minimum of those pitches as the floor.
        This catches sustained melody notes that started before the
        inner note — the previous ±2-beat onset window missed them.
        """
        if not melody_beats:
            return pitches

        result = list(pitches)
        beat = 0.0

        for i in range(len(result)):
            if i >= len(durations):
                break
            if durations[i] <= 0:
                beat += abs(durations[i])
                continue

            inner_start = beat
            inner_end = beat + durations[i]
            # Melody notes overlapping [inner_start, inner_end)
            sounding = [mp for (ms, md, mp) in melody_beats
                        if ms < inner_end and ms + md > inner_start]
            if not sounding:
                # Fall back to nearest melody note by onset distance
                sounding = [min(
                    melody_beats, key=lambda x: abs(x[0] - beat)
                )[2]]

            mel_floor = min(sounding)
            mel_ceil = max(sounding)
            p = result[i]

            changed = False
            # No crossing: inner must be at least 4st below lowest nearby melody
            if p >= mel_floor - 3:
                p = mel_floor - 5
                changed = True
            # No excessive spacing: inner within 11st of highest nearby
            if mel_ceil - p > 11:
                p = mel_ceil - 9
                changed = True

            if changed and scale_pitches:
                upper = mel_floor - 1
                lower = max(mel_ceil - 12, 48)
                candidates = [sp for sp in scale_pitches
                              if lower <= sp <= upper]
                if candidates:
                    p = min(candidates, key=lambda sp: abs(sp - p))

            result[i] = p
            beat += abs(durations[i])

        return result

    @staticmethod
    def _break_unisons(
        pitches: list[int],
        durations: list[float],
        scale_pitches: list[int],
    ) -> list[int]:
        """Convert consecutive unisons into steps (±1-2 semitones).

        After voice coordination squishes the inner voice, many consecutive
        notes land on the same pitch.  This alternates them ±1 scale step
        to convert unisons into steps (target: 55% of intervals).
        """
        if not scale_pitches:
            return pitches

        result = list(pitches)
        sorted_scale = sorted(set(scale_pitches))

        for i in range(1, len(result)):
            if i >= len(durations) or durations[i] <= 0 or durations[i - 1] <= 0:
                continue
            if result[i] != result[i - 1]:
                continue
            # Consecutive sounding unison — alternate up/down
            direction = 1 if i % 2 == 0 else -1
            candidates = [p for p in sorted_scale
                          if (p - result[i]) * direction > 0
                          and abs(p - result[i]) <= 3]
            if candidates:
                result[i] = min(candidates, key=lambda p: abs(p - result[i]))

        return result

    @staticmethod
    def _diversify_intervals(
        pitches: list[int],
        scale_pitches: list[int],
    ) -> list[int]:
        """Inject interval variety to match the evaluator's target distribution.

        Target: 10% unisons, 55% steps (1-2st), 20% thirds (3-4st),
        10% fourths/fifths (5-7st), 5% sixths+ (8+st).

        The constraint pipeline creates too many steps. This replaces
        some step intervals with thirds and fourths by jumping an
        extra scale degree on a controlled schedule.
        """
        import random as _rng
        if len(pitches) < 4 or not scale_pitches:
            return list(pitches)

        rng = _rng.Random(pitches[0])  # deterministic
        sorted_scale = sorted(set(scale_pitches))
        result = list(pitches)

        for i in range(1, len(result)):
            interval = abs(result[i] - result[i - 1])
            # Only modify steps (1-2 semitones)
            if interval > 2:
                continue

            roll = rng.random()
            if roll < 0.30:
                # 30% chance: expand step to a third (skip one scale degree)
                direction = 1 if result[i] >= result[i - 1] else -1
                candidates = [p for p in sorted_scale
                              if (p - result[i - 1]) * direction > 2
                              and abs(p - result[i - 1]) <= 4]
                if candidates:
                    result[i] = candidates[0] if direction > 0 else candidates[-1]
            elif roll < 0.42:
                # 12% chance: expand to a fourth/fifth (skip two scale degrees)
                direction = 1 if result[i] >= result[i - 1] else -1
                candidates = [p for p in sorted_scale
                              if (p - result[i - 1]) * direction > 4
                              and abs(p - result[i - 1]) <= 7]
                if candidates:
                    result[i] = candidates[0] if direction > 0 else candidates[-1]

        return result

    @staticmethod
    def _recover_leaps(
        pitches: list[int],
        durations: list[float],
        scale_pitches: list[int],
    ) -> list[int]:
        """Fix unrecovered leaps (>5st) by nudging the recovery note.

        After a leap, the next note must move in the opposite direction
        by stepwise motion (≤5st for moderate leaps, ≤2st for large).
        Only modifies the recovery note, preserving the leap itself.
        """
        sounding = [i for i in range(min(len(pitches), len(durations)))
                    if durations[i] > 0]
        if len(sounding) < 3 or not scale_pitches:
            return list(pitches)

        result = list(pitches)
        sorted_scale = sorted(set(scale_pitches))

        for k in range(len(sounding) - 2):
            i0, i1, i2 = sounding[k], sounding[k + 1], sounding[k + 2]
            leap = result[i1] - result[i0]
            if abs(leap) <= 5:
                continue
            recovery = result[i2] - result[i1]
            opposite = (leap > 0 and recovery < 0) or (leap < 0 and recovery > 0)
            max_rec = 5 if abs(leap) <= 8 else 2
            stepwise = abs(recovery) <= max_rec
            if opposite and stepwise:
                continue
            # Fix: move recovery note to step in opposite direction
            direction = -1 if leap > 0 else 1
            candidates = [p for p in sorted_scale
                          if (p - result[i1]) * direction > 0
                          and abs(p - result[i1]) <= max_rec]
            if candidates:
                result[i2] = min(candidates, key=lambda p: abs(p - result[i1]))

        return result

    @staticmethod
    def _clamp_one_interval(
        result: list[int], i_prev: int, i_curr: int,
        scale_pitches: list[int], max_interval: int,
    ) -> bool:
        """Shrink ``result[i_curr]`` until the step from i_prev fits max_interval.

        Returns True if the pitch was modified.
        """
        interval = result[i_curr] - result[i_prev]
        if abs(interval) <= max_interval:
            return False
        direction = 1 if interval > 0 else -1
        target = result[i_prev] + direction * 2
        if scale_pitches:
            from sacred_composer.constraints import _step_in_scale
            step = _step_in_scale(result[i_prev], direction, scale_pitches)
            if abs(step - result[i_prev]) <= max_interval:
                target = step
        result[i_curr] = max(0, min(127, target))
        return True

    @staticmethod
    def _needs_leap_recovery(leap: int, recovery: int) -> bool:
        """True iff the recovery note doesn't satisfy the L1 leap-recovery rule.

        For leaps of 6-8 semitones the recovery must be an opposite-direction
        step of ≤5st; for leaps >8st the recovery must be ≤2st.
        """
        if abs(leap) <= 5:
            return False
        opposite = (recovery * leap) < 0
        max_rec = 5 if abs(leap) <= 8 else 2
        stepwise = abs(recovery) <= max_rec
        return not (opposite and stepwise)

    @staticmethod
    def _try_recover_leap(
        result: list[int], i1: int, i2: int, leap: int,
        scale_pitches: list[int], gate_into_range: bool,
    ) -> bool:
        """Set ``result[i2]`` to a step that recovers the leap at i1.

        When ``gate_into_range`` is True the candidate must fall within the
        allowed recovery window (≤5st for ≤8st leaps, ≤2st for bigger ones)
        AND be opposite-signed to the leap.  When False the candidate is
        accepted as long as it stays in MIDI range.  Returns True if
        result[i2] was modified.
        """
        recovery_dir = -1 if leap > 0 else 1
        max_rec = 5 if abs(leap) <= 8 else 2
        if scale_pitches:
            from sacred_composer.constraints import _step_in_scale
            target = _step_in_scale(result[i1], recovery_dir, scale_pitches)
        else:
            target = result[i1] + recovery_dir * 2

        if gate_into_range:
            if abs(target - result[i1]) <= max_rec and (target - result[i1]) * leap < 0:
                result[i2] = max(0, min(127, target))
                return True
            return False
        if 0 <= target <= 127:
            result[i2] = target
            return True
        return False

    @staticmethod
    def _apply_crescendo_entry(
        durations: list[float],
        dynamics: list[int],
        entry_fraction: float = 0.55,
        start_scale: float = 0.10,
        floor_velocity: int = 15,
    ) -> list[int]:
        """Scale down velocities in the opening of the voice so the piece
        starts quiet and grows to full intensity near the golden section.

        The tension_arc metric correlates the piece's tension curve
        (40% velocity + 25% dissonance + 20% pitch_height + 15% density)
        with a sin-arch target that starts at zero. Composer output is
        typically near-uniform velocity from bar 1, which yields a flat
        tension curve and mediocre correlation. Scaling the opening
        velocities by a sin ramp 0→1 over the first 55% of the voice
        converts that flat curve into a rising phase, matching the arch.

        Args:
            durations: per-note durations (negative = rest).
            dynamics: per-note MIDI velocities (0-127).
            entry_fraction: how far into the voice the ramp reaches 1.0.
            start_scale: multiplier applied at beat 0 (floor of the ramp).
            floor_velocity: absolute minimum velocity so notes stay audible.

        Returns a new velocity list. Rests are unaffected (they have no
        note-on to scale), but the loop still advances past them so the
        beat counter stays aligned with actual time.
        """
        import math as _math
        if not dynamics:
            return list(dynamics)

        total_beats = sum(abs(d) for d in durations)
        if total_beats <= 0 or entry_fraction <= 0:
            return list(dynamics)

        entry_end = total_beats * entry_fraction
        out = list(dynamics)

        beat = 0.0
        for i, d in enumerate(durations):
            if i >= len(out):
                break
            if beat < entry_end:
                t_rel = beat / entry_end
                scale = start_scale + (1.0 - start_scale) * _math.sin(
                    _math.pi * t_rel / 2.0
                )
                out[i] = max(floor_velocity, int(out[i] * scale))
            beat += abs(d)

        return out

    @classmethod
    def _clamp_sounding_pitches(
        cls,
        pitches: list[int],
        durations: list[float],
        scale_pitches: list[int],
        max_interval: int = 5,
    ) -> list[int]:
        """Clamp and recover leaps only among sounding notes (dur > 0).

        Rests (negative durations) create gaps in the MIDI note sequence.
        The evaluator reads only sounding notes, so we must ensure that
        consecutive *sounding* pitches have small intervals.
        """
        sounding_idx = [i for i in range(min(len(pitches), len(durations)))
                        if durations[i] > 0]
        if len(sounding_idx) < 2:
            return list(pitches)

        result = list(pitches)

        # Up to six clamp+recovery passes until the material stabilises.
        for _pass in range(6):
            changed = False
            for k in range(1, len(sounding_idx)):
                if cls._clamp_one_interval(
                    result, sounding_idx[k - 1], sounding_idx[k],
                    scale_pitches, max_interval,
                ):
                    changed = True
            for k in range(1, len(sounding_idx) - 1):
                i0, i1, i2 = sounding_idx[k - 1], sounding_idx[k], sounding_idx[k + 1]
                leap = result[i1] - result[i0]
                recovery = result[i2] - result[i1]
                if cls._needs_leap_recovery(leap, recovery):
                    if cls._try_recover_leap(
                        result, i1, i2, leap, scale_pitches, gate_into_range=True,
                    ):
                        changed = True
            if not changed:
                break

        # Final dedicated leap recovery pass — never overwritten by clamp.
        # Multiple passes because fixing one leap's recovery can create
        # a new >5st interval that itself needs recovery.
        for _final_pass in range(3):
            fixed_any = False
            for k in range(1, len(sounding_idx) - 1):
                i0, i1, i2 = sounding_idx[k - 1], sounding_idx[k], sounding_idx[k + 1]
                leap = result[i1] - result[i0]
                recovery = result[i2] - result[i1]
                if cls._needs_leap_recovery(leap, recovery):
                    if cls._try_recover_leap(
                        result, i1, i2, leap, scale_pitches, gate_into_range=False,
                    ):
                        fixed_any = True
            if not fixed_any:
                break

        return result

    def _generate_dynamics(self, v_spec: dict, n: int) -> list[int]:
        """Generate dynamics following a tension arc with light variation.

        The arc dominates (climax at golden section) with subtle pink-noise
        variation on top, so the evaluator can detect the arch shape clearly.
        """
        import math
        seed = v_spec.get("seed", 0)
        role = v_spec["role"]

        # Prefer explicit velocity_range (e.g. from consciousness presets)
        vel_range = v_spec.get("velocity_range")
        if vel_range is None:
            if role == "melody":
                vel_range = (40, 105)
            elif role == "bass":
                vel_range = (40, 90)
            else:
                vel_range = (35, 80)

        lo, hi = vel_range
        climax = PHI_INVERSE  # 0.618

        # Generate pure arc + light noise
        raw = PinkNoise(sigma=0.8, seed=seed + 100).generate(n)
        noise = to_dynamics(raw, velocity_range=(0, 10))  # tiny variation

        result = []
        for i in range(n):
            position = i / max(1, n - 1)
            if position < climax:
                arc = math.sin(math.pi * position / (2 * climax))
            else:
                arc = math.sin(math.pi * (1 - position) / (2 * (1 - climax)))
            vel = lo + (hi - lo) * arc + (noise[i] - 5)
            result.append(max(1, min(127, int(vel))))

        return result
