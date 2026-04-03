"""Adaptive music engine — real-time parameter-driven composition.

Converts external system state (games, installations, interactive apps)
into musical parameters, generating deterministic soundtrack chunks that
respond to danger, energy, environment, time-of-day, health, and speed.

No open-source competitor exists for parameter-driven adaptive composition
built on sacred geometry patterns.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from sacred_composer.core import Composition
from sacred_composer.patterns import (
    LogisticMap, CellularAutomata, EuclideanRhythm,
    InfinitySeries, GoldenSpiral, PinkNoise, HarmonicSeries,
)
from sacred_composer.mappers import to_pitch, to_rhythm, to_dynamics
from sacred_composer.constants import parse_scale


# ---------------------------------------------------------------------------
# Game state representation
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Represents the current state of an external system.

    All float fields are normalised 0.0-1.0 unless noted otherwise.
    """
    danger: float = 0.0         # 0.0 = safe, 1.0 = max danger
    energy: float = 0.5         # 0.0 = calm, 1.0 = intense
    environment: str = "forest" # biome/setting
    time_of_day: float = 12.0   # 0-24 hours
    health: float = 1.0         # 0.0 = dying, 1.0 = full
    speed: float = 0.5          # movement speed 0.0-1.0
    custom: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Environment-to-scale mapping
# ---------------------------------------------------------------------------

ENVIRONMENT_SCALES: dict[str, str] = {
    "forest": "A_minor",
    "desert": "A_phrygian",
    "ocean": "C_lydian",
    "cave": "D_minor",
    "mountain": "G_major",
    "city": "Bb_mixolydian",
    "space": "C_whole_tone",
    "temple": "C_dorian",
}


# ---------------------------------------------------------------------------
# State-to-parameters conversion
# ---------------------------------------------------------------------------

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation clamped to [a, b]."""
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def state_to_params(state: GameState) -> dict:
    """Convert a GameState into CompositionBuilder-compatible parameters.

    Returns a dict with keys: scale, tempo, r_value, consonance,
    note_density, active_layers.
    """
    # Scale from environment
    scale = ENVIRONMENT_SCALES.get(state.environment, "A_minor")

    # Tempo: energy maps 50-140 bpm, with time-of-day curve
    base_tempo = _lerp(50.0, 140.0, state.energy)
    # Morning (6-10) slightly faster, night (22-4) slower
    hour = state.time_of_day % 24.0
    tod_factor = 1.0 + 0.1 * math.sin((hour - 6.0) * math.pi / 12.0)
    tempo = int(round(base_tempo * tod_factor))
    tempo = max(40, min(180, tempo))

    # Danger -> logistic map r value (2.5 calm -> 3.99 chaos)
    r_value = _lerp(2.5, 3.99, state.danger)

    # Health -> consonance (1.0 = full consonant, 0.0 = dissonant)
    consonance = state.health

    # Speed -> note density (notes per beat)
    note_density = _lerp(1.0, 4.0, state.speed)

    # Layer activation
    layers = ["bass"]
    if state.energy > 0.2:
        layers.append("harmony")
    if state.energy > 0.3:
        layers.append("melody")
    if state.danger > 0.4:
        layers.append("texture")
    if state.danger > 0.7:
        layers.append("tension")

    return {
        "scale": scale,
        "tempo": tempo,
        "r_value": r_value,
        "consonance": consonance,
        "note_density": note_density,
        "active_layers": layers,
    }


# ---------------------------------------------------------------------------
# Adaptive Composer
# ---------------------------------------------------------------------------

class AdaptiveComposer:
    """Generates music chunks that adapt to a changing GameState.

    Pre-composes five layers (bass, harmony, melody, texture, tension)
    and activates them based on the current state. Deterministic: same
    seed + same state sequence = identical output.

    Parameters
    ----------
    layers : Number of pre-composed layers (default 5).
    seed : Random seed for deterministic output.
    """

    LAYER_NAMES = ("bass", "harmony", "melody", "texture", "tension")
    LAYER_INSTRUMENTS = ("cello", "strings", "violin", "vibraphone", "piano")
    LAYER_OCTAVES = ((2, 3), (3, 4), (4, 5), (4, 6), (3, 5))

    def __init__(self, layers: int = 5, seed: int = 42) -> None:
        self._n_layers = min(layers, len(self.LAYER_NAMES))
        self._seed = seed
        self._rng = random.Random(seed)
        self._params: dict = state_to_params(GameState())
        self._beat_cursor: float = 0.0

    def update(self, state: GameState) -> None:
        """Map game state to musical parameters for the next chunk."""
        self._params = state_to_params(state)

    @property
    def active_layers(self) -> list[str]:
        """Which layers are currently sounding."""
        return list(self._params.get("active_layers", ["bass"]))

    def render_chunk(self, beats: int = 8) -> Composition:
        """Generate the next *beats* of music based on current state.

        Returns a Composition that can be rendered to MIDI/WAV.
        """
        p = self._params
        piece = Composition(tempo=p["tempo"], title="Adaptive Chunk")
        scale = p["scale"]
        active = set(p["active_layers"])
        density = p["note_density"]
        cursor = self._beat_cursor

        for idx in range(self._n_layers):
            name = self.LAYER_NAMES[idx]
            if name not in active:
                continue

            instrument = self.LAYER_INSTRUMENTS[idx]
            octave_range = self.LAYER_OCTAVES[idx]
            layer_seed = self._seed + idx * 1000 + int(cursor)
            n_notes = max(4, int(beats * density))

            pitches, durations, velocities = self._generate_layer(
                name, n_notes, beats, scale, octave_range, layer_seed, p,
            )

            piece.add_voice(
                name=name,
                pitches=pitches,
                durations=durations,
                velocities=velocities,
                instrument=instrument,
            )

        self._beat_cursor += beats
        return piece

    # ------------------------------------------------------------------
    # Private layer generators
    # ------------------------------------------------------------------

    def _generate_layer(
        self,
        name: str,
        n_notes: int,
        beats: int,
        scale: str,
        octave_range: tuple[int, int],
        seed: int,
        params: dict,
    ) -> tuple[list[int], list[float], list[int]]:
        """Generate pitches, durations, and velocities for one layer."""

        if name == "bass":
            return self._gen_bass(n_notes, beats, scale, octave_range, seed, params)
        elif name == "harmony":
            return self._gen_harmony(n_notes, beats, scale, octave_range, seed, params)
        elif name == "melody":
            return self._gen_melody(n_notes, beats, scale, octave_range, seed, params)
        elif name == "texture":
            return self._gen_texture(n_notes, beats, scale, octave_range, seed, params)
        elif name == "tension":
            return self._gen_tension(n_notes, beats, scale, octave_range, seed, params)
        else:
            return self._gen_bass(n_notes, beats, scale, octave_range, seed, params)

    def _gen_bass(self, n: int, beats: int, scale: str, octs: tuple[int, int],
                  seed: int, params: dict) -> tuple[list[int], list[float], list[int]]:
        raw = GoldenSpiral(start=float(seed % 360)).generate(n)
        pitches = to_pitch(raw, scale=scale, octave_range=octs, strategy="normalize")
        dur_each = beats / max(n, 1)
        durations = [dur_each] * n
        vel_base = int(_lerp(50, 75, params.get("consonance", 1.0)))
        velocities = [vel_base] * n
        return pitches, durations, velocities

    def _gen_harmony(self, n: int, beats: int, scale: str, octs: tuple[int, int],
                     seed: int, params: dict) -> tuple[list[int], list[float], list[int]]:
        raw = InfinitySeries(seed=seed).generate(n)
        pitches = to_pitch(raw, scale=scale, octave_range=octs, strategy="modular")
        dur_each = beats / max(n, 1)
        durations = [dur_each] * n
        vel = int(_lerp(40, 65, params.get("consonance", 1.0)))
        velocities = [vel] * n
        return pitches, durations, velocities

    def _gen_melody(self, n: int, beats: int, scale: str, octs: tuple[int, int],
                    seed: int, params: dict) -> tuple[list[int], list[float], list[int]]:
        raw = InfinitySeries(seed=seed).generate(n)
        pitches = to_pitch(raw, scale=scale, octave_range=octs, strategy="modular")
        euc = EuclideanRhythm(max(1, n * 2 // 3), n).generate(n)
        durations = to_rhythm(euc, base_duration=beats / max(n, 1), strategy="binary")
        pink = PinkNoise(sigma=1.5, seed=seed).generate(n)
        velocities = to_dynamics(pink, velocity_range=(55, 95))
        return pitches, durations, velocities

    def _gen_texture(self, n: int, beats: int, scale: str, octs: tuple[int, int],
                     seed: int, params: dict) -> tuple[list[int], list[float], list[int]]:
        ca = CellularAutomata(rule=110, width=max(4, n), initial_state=None)
        raw = ca.generate(n)
        pitches = to_pitch(raw, scale=scale, octave_range=octs, strategy="modular")
        dur_each = beats / max(n, 1)
        durations: list[float] = []
        for v in raw:
            durations.append(dur_each if v > 0.5 else -dur_each)
        vel = int(_lerp(35, 55, 1.0 - params.get("consonance", 1.0)))
        velocities = [vel] * n
        return pitches, durations, velocities

    def _gen_tension(self, n: int, beats: int, scale: str, octs: tuple[int, int],
                     seed: int, params: dict) -> tuple[list[int], list[float], list[int]]:
        r = params.get("r_value", 3.99)
        lm = LogisticMap(r=r, x0=0.5 + (seed % 100) * 0.001)
        raw = lm.generate(n)
        # Use chromatic scale for maximum tension
        pitches = to_pitch(raw, scale=scale.split("_")[0] + "_chromatic",
                           octave_range=octs, strategy="normalize")
        dur_each = beats / max(n, 1)
        durations = [dur_each * 0.75] * n
        vel = int(_lerp(60, 100, params.get("r_value", 3.0) / 4.0))
        velocities = [vel] * n
        return pitches, durations, velocities


# ---------------------------------------------------------------------------
# Full soundtrack generation
# ---------------------------------------------------------------------------

def generate_soundtrack(
    states: list[tuple[float, GameState]],
    chunk_beats: int = 8,
    seed: int = 42,
) -> Composition:
    """Generate a complete soundtrack from a sequence of (timestamp, GameState) pairs.

    Timestamps are in beats. Each chunk covers *chunk_beats* beats.
    States are interpolated linearly between timestamps for smooth
    transitions. Deterministic: same inputs = same output.

    Parameters
    ----------
    states : List of (beat_timestamp, GameState) pairs, sorted by timestamp.
    chunk_beats : Beats per generated chunk.
    seed : Random seed for determinism.
    """
    if not states:
        return Composition(tempo=72, title="Empty Adaptive Soundtrack")

    # Determine total duration
    last_ts = max(ts for ts, _ in states)
    total_beats = max(chunk_beats, int(math.ceil(last_ts / chunk_beats) * chunk_beats + chunk_beats))

    composer = AdaptiveComposer(seed=seed)
    all_voices: dict[str, tuple[list[int], list[float], list[int]]] = {}

    beat = 0.0
    while beat < total_beats:
        # Find the interpolated state at this beat
        state = _interpolate_state(states, beat)
        composer.update(state)
        chunk = composer.render_chunk(beats=chunk_beats)

        # Accumulate voices by name
        for voice in chunk.score.voices:
            pitches = [n.pitch for n in voice.notes]
            durations = [n.duration if not n.is_rest else -n.duration for n in voice.notes]
            velocities = [n.velocity for n in voice.notes]
            if voice.name not in all_voices:
                all_voices[voice.name] = ([], [], [])
            p, d, v = all_voices[voice.name]
            p.extend(pitches)
            d.extend(durations)
            v.extend(velocities)

        beat += chunk_beats

    # Assemble final composition using the last known tempo
    final_state = _interpolate_state(states, total_beats - 1)
    final_params = state_to_params(final_state)
    piece = Composition(tempo=final_params["tempo"], title="Adaptive Soundtrack")

    layer_instrument_map = dict(zip(AdaptiveComposer.LAYER_NAMES, AdaptiveComposer.LAYER_INSTRUMENTS))

    for name, (pitches, durations, velocities) in all_voices.items():
        instrument = layer_instrument_map.get(name, "piano")
        piece.add_voice(
            name=name,
            pitches=pitches,
            durations=durations,
            velocities=velocities,
            instrument=instrument,
        )

    return piece


def _interpolate_state(states: list[tuple[float, GameState]], beat: float) -> GameState:
    """Linearly interpolate between the two nearest states at the given beat."""
    if len(states) == 1:
        return states[0][1]

    # Find surrounding states
    before = states[0]
    after = states[-1]
    for i in range(len(states) - 1):
        if states[i][0] <= beat <= states[i + 1][0]:
            before = states[i]
            after = states[i + 1]
            break
    else:
        # beat is beyond all states — clamp to last
        if beat >= states[-1][0]:
            return states[-1][1]
        return states[0][1]

    ts_a, st_a = before
    ts_b, st_b = after
    span = ts_b - ts_a
    if span <= 0:
        return st_a

    t = (beat - ts_a) / span

    return GameState(
        danger=_lerp(st_a.danger, st_b.danger, t),
        energy=_lerp(st_a.energy, st_b.energy, t),
        environment=st_a.environment if t < 0.5 else st_b.environment,
        time_of_day=_lerp(st_a.time_of_day, st_b.time_of_day, t),
        health=_lerp(st_a.health, st_b.health, t),
        speed=_lerp(st_a.speed, st_b.speed, t),
        custom={**st_a.custom, **st_b.custom},
    )
