"""Harmonic engine — chord progression generation via weighted state machine.

Implements functional harmony as a directed graph with corpus-derived
transition probabilities (informed by Rohrmeier & Pearce 2018 chord
grammar and Bach chorale analysis). All functions are deterministic
given a seed — uses random.Random(seed), never global state.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from sacred_composer.constants import NOTE_NAMES, SCALES


# ---------------------------------------------------------------------------
# Chord grammar: Roman numeral -> weighted transitions
# Probabilities derived from Bach chorale corpus analysis.
# ---------------------------------------------------------------------------

CHORD_GRAMMAR: dict[str, list[tuple[str, float]]] = {
    "I":   [("IV", 0.25), ("V", 0.30), ("vi", 0.20), ("ii", 0.15), ("iii", 0.10)],
    "ii":  [("V", 0.60), ("vii", 0.20), ("IV", 0.10), ("ii", 0.10)],
    "iii": [("vi", 0.40), ("IV", 0.35), ("ii", 0.25)],
    "IV":  [("V", 0.45), ("I", 0.20), ("ii", 0.15), ("vii", 0.10), ("vi", 0.10)],
    "V":   [("I", 0.55), ("vi", 0.25), ("IV", 0.10), ("V", 0.10)],
    "vi":  [("ii", 0.35), ("IV", 0.30), ("V", 0.20), ("iii", 0.15)],
    "vii": [("I", 0.55), ("iii", 0.25), ("vi", 0.20)],
}

# Semitone offsets from scale root for each Roman numeral (major-key basis).
# Lowercase = minor triad, uppercase = major triad, vii = diminished.
_ROMAN_SCALE_DEGREE: dict[str, int] = {
    "I": 0, "ii": 1, "iii": 2, "IV": 3, "V": 4, "vi": 5, "vii": 6,
}

# Quality implied by each Roman numeral in a major key.
_ROMAN_QUALITY: dict[str, str] = {
    "I": "major", "ii": "minor", "iii": "minor", "IV": "major",
    "V": "major", "vi": "minor", "vii": "dim",
}

# Interval templates (semitones from root) for chord qualities.
_QUALITY_INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (0, 4, 7),
    "minor": (0, 3, 7),
    "dim":   (0, 3, 6),
}


# ---------------------------------------------------------------------------
# Chord dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Chord:
    """A chord defined by root pitch class, quality, and pitch classes."""

    root: int                          # pitch class 0-11
    quality: str                       # 'major', 'minor', 'dim'
    pitch_classes: tuple[int, ...]     # pitch classes 0-11
    roman: str = ""                    # original Roman numeral label

    def to_midi_pitches(self, octave: int = 4) -> list[int]:
        """Return MIDI note numbers for a close-position voicing.

        Parameters
        ----------
        octave : Base octave for the root (C4 = octave 4 = MIDI 60).
        """
        base = octave * 12 + 12  # MIDI convention: octave 4 -> 60
        intervals = _QUALITY_INTERVALS[self.quality]
        return [base + self.root + iv for iv in intervals]

    def __repr__(self) -> str:
        label = self.roman or f"pc{self.root}"
        return f"Chord({label}, {self.quality}, pcs={list(self.pitch_classes)})"


# ---------------------------------------------------------------------------
# Roman numeral -> Chord resolution
# ---------------------------------------------------------------------------

def roman_to_chord(numeral: str, key: str) -> Chord:
    """Resolve a Roman numeral chord symbol in a given key.

    Parameters
    ----------
    numeral : One of 'I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii'.
    key : Scale name such as 'C_major', 'D_minor', 'A_harmonic_minor'.

    Returns
    -------
    Chord with concrete pitch classes.
    """
    parts = key.split("_", 1)
    root_name = parts[0]
    scale_type = parts[1] if len(parts) > 1 else "major"

    key_root_pc = NOTE_NAMES.get(root_name, 0)
    intervals = SCALES.get(scale_type, SCALES["major"])

    degree = _ROMAN_SCALE_DEGREE[numeral]
    # The chord root is the scale degree's pitch class.
    if degree < len(intervals):
        chord_root_pc = (key_root_pc + intervals[degree]) % 12
    else:
        chord_root_pc = (key_root_pc + degree * 2) % 12  # fallback

    quality = _ROMAN_QUALITY[numeral]
    chord_intervals = _QUALITY_INTERVALS[quality]
    pitch_classes = tuple((chord_root_pc + iv) % 12 for iv in chord_intervals)

    return Chord(
        root=chord_root_pc,
        quality=quality,
        pitch_classes=pitch_classes,
        roman=numeral,
    )


# ---------------------------------------------------------------------------
# Progression generation
# ---------------------------------------------------------------------------

def _weighted_choice(transitions: list[tuple[str, float]], rng: random.Random) -> str:
    """Pick a chord symbol from weighted transitions."""
    r = rng.random()
    cumulative = 0.0
    for symbol, weight in transitions:
        cumulative += weight
        if r <= cumulative:
            return symbol
    # Floating-point safety: return the last option.
    return transitions[-1][0]


def generate_progression(
    n_chords: int = 8,
    key: str = "C_major",
    seed: int = 42,
    start: str = "I",
) -> list[Chord]:
    """Walk the chord grammar graph stochastically for *n_chords* steps.

    Forces a V-I authentic cadence at the end.

    Parameters
    ----------
    n_chords : Total number of chords (minimum 2 for the cadence).
    key : Scale key such as 'C_major' or 'D_minor'.
    seed : Random seed for reproducibility.
    start : Starting chord symbol.

    Returns
    -------
    List of Chord objects forming the progression.
    """
    if n_chords < 2:
        n_chords = 2

    rng = random.Random(seed)

    if n_chords == 2:
        # Minimal cadence only.
        return [roman_to_chord("V", key), roman_to_chord("I", key)]

    symbols: list[str] = [start]
    current = start

    # Generate interior chords, reserving the last 2 slots for the cadence.
    for _ in range(n_chords - 3):
        transitions = CHORD_GRAMMAR.get(current, CHORD_GRAMMAR["I"])
        current = _weighted_choice(transitions, rng)
        symbols.append(current)

    # Force authentic cadence: V -> I
    symbols.append("V")
    symbols.append("I")

    return [roman_to_chord(s, key) for s in symbols]


# ---------------------------------------------------------------------------
# Voice leading
# ---------------------------------------------------------------------------

def voice_lead(current_voicing: list[int], next_chord: Chord) -> list[int]:
    """Find the voicing of *next_chord* that minimises total voice movement.

    Each voice moves to the nearest available chord tone (any octave).
    Voices are assigned greedily from smallest to largest movement.

    Parameters
    ----------
    current_voicing : List of MIDI note numbers (one per voice).
    next_chord : The target Chord.

    Returns
    -------
    List of MIDI note numbers for the new voicing (same length as input).
    """
    pcs = next_chord.pitch_classes

    # Build candidate pitches across a wide range around the current voicing.
    if current_voicing:
        center = sum(current_voicing) // len(current_voicing)
    else:
        center = 60
    candidates: list[int] = []
    for pc in pcs:
        for octave_midi in range(center - 18, center + 19):
            note = (octave_midi // 12) * 12 + pc
            if 24 <= note <= 108 and abs(note - center) <= 18:
                candidates.append(note)
    candidates = sorted(set(candidates))

    if not candidates:
        return list(current_voicing)

    # Greedy assignment: for each voice, pick the closest unused candidate.
    result = [0] * len(current_voicing)
    used: set[int] = set()

    # Sort voices by how constrained they are (smallest movement first).
    voice_order = sorted(
        range(len(current_voicing)),
        key=lambda i: min(abs(c - current_voicing[i]) for c in candidates),
    )

    for vi in voice_order:
        target = current_voicing[vi]
        best = min(candidates, key=lambda c: (abs(c - target), c in used))
        result[vi] = best
        used.add(best)

    return result


# ---------------------------------------------------------------------------
# Melody from chord progression
# ---------------------------------------------------------------------------

def melody_from_chords(
    progression: list[Chord],
    scale_pitches: list[int],
    beats_per_chord: int = 4,
    seed: int = 42,
    octave: int = 5,
) -> tuple[list[int], list[float]]:
    """Generate a melody guided by a chord progression.

    Strategy: chord tones on strong beats (1, 3), scale steps on
    weak beats (2, 4). Returns both pitches and durations.

    Parameters
    ----------
    progression : List of Chord objects.
    scale_pitches : All valid MIDI pitches in the scale (from parse_scale).
    beats_per_chord : How many beats each chord lasts.
    seed : Random seed.
    octave : Target octave for the melody.

    Returns
    -------
    (pitches, durations) — lists of MIDI note numbers and beat durations.
    """
    rng = random.Random(seed)
    lo = octave * 12 + 12
    hi = lo + 14  # roughly one octave + a step
    melody_scale = [p for p in scale_pitches if lo <= p <= hi]
    if not melody_scale:
        melody_scale = [p for p in scale_pitches if 60 <= p <= 84]
    if not melody_scale:
        melody_scale = list(range(lo, hi + 1))

    pitches: list[int] = []
    durations: list[float] = []
    prev_pitch = melody_scale[len(melody_scale) // 2]

    for chord in progression:
        # Chord tones in the melody octave.
        chord_tones_in_range = []
        for pc in chord.pitch_classes:
            for candidate in melody_scale:
                if candidate % 12 == pc:
                    chord_tones_in_range.append(candidate)
        if not chord_tones_in_range:
            chord_tones_in_range = melody_scale[:3]

        for beat in range(beats_per_chord):
            is_strong = (beat % 2 == 0)

            if is_strong:
                # Strong beat: pick a chord tone near the previous pitch.
                candidates = sorted(chord_tones_in_range, key=lambda p: abs(p - prev_pitch))
                pitch = candidates[0] if candidates else prev_pitch
            else:
                # Weak beat: stepwise motion in the scale.
                idx_candidates = [
                    i for i, p in enumerate(melody_scale)
                    if abs(p - prev_pitch) <= 3
                ]
                if idx_candidates:
                    idx = rng.choice(idx_candidates)
                    pitch = melody_scale[idx]
                else:
                    pitch = min(melody_scale, key=lambda p: abs(p - prev_pitch))

            pitches.append(pitch)
            durations.append(1.0)
            prev_pitch = pitch

    return pitches, durations


# ---------------------------------------------------------------------------
# Bass line from progression
# ---------------------------------------------------------------------------

def bass_from_chords(
    progression: list[Chord],
    beats_per_chord: int = 4,
    octave: int = 2,
) -> tuple[list[int], list[float]]:
    """Generate a bass line using chord roots.

    Root on beat 1, held or repeated on remaining beats.

    Parameters
    ----------
    progression : List of Chord objects.
    beats_per_chord : Beats per chord.
    octave : Bass octave.

    Returns
    -------
    (pitches, durations)
    """
    pitches: list[int] = []
    durations: list[float] = []

    for chord in progression:
        root_midi = octave * 12 + 12 + chord.root
        # Beat 1: root, full duration.
        pitches.append(root_midi)
        durations.append(float(beats_per_chord))

    return pitches, durations


# ---------------------------------------------------------------------------
# HarmonicEngine — top-level orchestrator
# ---------------------------------------------------------------------------

class HarmonicEngine:
    """Combines chord grammar, voice leading, melody, and bass generation.

    Usage::

        engine = HarmonicEngine(key="D_minor", n_chords=16, seed=7)
        progression = engine.progression
        melody_pitches, melody_durs = engine.melody()
        bass_pitches, bass_durs = engine.bass()

        # Or apply directly to a CompositionBuilder:
        builder = CompositionBuilder(key="D_minor", bars=64)
        engine.apply_to_builder(builder)
        piece = builder.build()
    """

    def __init__(
        self,
        key: str = "C_major",
        n_chords: int = 8,
        seed: int = 42,
        beats_per_chord: int = 4,
    ) -> None:
        self.key = key
        self.n_chords = n_chords
        self.seed = seed
        self.beats_per_chord = beats_per_chord

        self.progression: list[Chord] = generate_progression(
            n_chords=n_chords, key=key, seed=seed,
        )

        # Pre-compute voice-led inner voicings.
        self._voicings: list[list[int]] = self._compute_voicings()

    def _compute_voicings(self) -> list[list[int]]:
        """Compute voice-led chord voicings for the whole progression."""
        if not self.progression:
            return []
        voicings: list[list[int]] = []
        current = self.progression[0].to_midi_pitches(octave=4)
        voicings.append(current)
        for chord in self.progression[1:]:
            current = voice_lead(current, chord)
            voicings.append(current)
        return voicings

    def melody(self, octave: int = 5) -> tuple[list[int], list[float]]:
        """Generate a melody over the progression."""
        from sacred_composer.constants import parse_scale
        scale_pitches = parse_scale(self.key)
        return melody_from_chords(
            self.progression,
            scale_pitches,
            beats_per_chord=self.beats_per_chord,
            seed=self.seed + 1,
            octave=octave,
        )

    def bass(self, octave: int = 2) -> tuple[list[int], list[float]]:
        """Generate a bass line from chord roots."""
        return bass_from_chords(
            self.progression,
            beats_per_chord=self.beats_per_chord,
            octave=octave,
        )

    def voicings(self) -> list[list[int]]:
        """Return the voice-led inner voicings."""
        return list(self._voicings)

    def apply_to_builder(self, builder) -> None:
        """Add harmony-driven voices to a CompositionBuilder.

        Adds melody, inner harmony, and bass voices to the builder's
        underlying Composition. Call this *before* ``builder.build()``,
        then the builder's own voices layer on top.

        Parameters
        ----------
        builder : A ``CompositionBuilder`` instance.
        """
        from sacred_composer.core import Composition

        mel_pitches, mel_durs = self.melody()
        bass_pitches, bass_durs = self.bass()

        # Store voices as pre-built specs so build() includes them.
        # We inject directly into the builder's voice list as raw dicts
        # with a special role that build() will pass through.
        builder._harmony_voices = {
            "melody": (mel_pitches, mel_durs),
            "bass": (bass_pitches, bass_durs),
            "voicings": self._voicings,
            "progression": self.progression,
            "beats_per_chord": self.beats_per_chord,
        }

    def to_composition(
        self,
        title: str = "Harmonic Composition",
        tempo: int = 72,
        melody_instrument: str = "violin",
        bass_instrument: str = "cello",
        inner_instrument: str = "viola",
    ) -> "Composition":
        """Build a standalone Composition from this engine's output.

        A convenience method when you don't need the full builder.
        """
        from sacred_composer.core import Composition

        piece = Composition(tempo=tempo, title=title)

        # Melody
        mel_pitches, mel_durs = self.melody()
        piece.add_voice(
            name="harmony_melody",
            pitches=mel_pitches,
            durations=mel_durs,
            instrument=melody_instrument,
        )

        # Inner voices (from voice-led voicings).
        if self._voicings:
            inner_pitches: list[int] = []
            inner_durs: list[float] = []
            for voicing in self._voicings:
                # Use the middle note of each voicing.
                mid = voicing[len(voicing) // 2] if voicing else 60
                inner_pitches.append(mid)
                inner_durs.append(float(self.beats_per_chord))
            piece.add_voice(
                name="harmony_inner",
                pitches=inner_pitches,
                durations=inner_durs,
                instrument=inner_instrument,
            )

        # Bass
        bass_pitches, bass_durs = self.bass()
        piece.add_voice(
            name="harmony_bass",
            pitches=bass_pitches,
            durations=bass_durs,
            instrument=bass_instrument,
        )

        return piece

    def info(self) -> dict:
        """Return a summary of the harmonic plan."""
        return {
            "key": self.key,
            "n_chords": self.n_chords,
            "seed": self.seed,
            "beats_per_chord": self.beats_per_chord,
            "total_beats": self.n_chords * self.beats_per_chord,
            "progression": [c.roman for c in self.progression],
            "cadence": (
                f"{self.progression[-2].roman}-{self.progression[-1].roman}"
                if len(self.progression) >= 2 else "none"
            ),
        }

    def __repr__(self) -> str:
        symbols = " ".join(c.roman for c in self.progression)
        return f"HarmonicEngine(key={self.key!r}, [{symbols}])"


# ---------------------------------------------------------------------------
# Neo-Riemannian Theory — PLR operations on the Tonnetz
# ---------------------------------------------------------------------------

def _make_triad(root: int, quality: str) -> Chord:
    """Helper: build a Chord from root pitch class and quality."""
    intervals = _QUALITY_INTERVALS[quality]
    pcs = tuple((root + iv) % 12 for iv in intervals)
    return Chord(root=root % 12, quality=quality, pitch_classes=pcs)


def _triad_key(chord: Chord) -> tuple[int, str]:
    """Return a hashable identifier (root, quality) for a major/minor triad."""
    return (chord.root % 12, chord.quality)


def parallel(chord: Chord) -> Chord:
    """P operation: flip major/minor by moving the third by one semitone.

    C major (0,4,7) -> C minor (0,3,7)
    C minor (0,3,7) -> C major (0,4,7)

    For diminished chords, returns the chord unchanged.
    """
    if chord.quality == "major":
        return _make_triad(chord.root, "minor")
    elif chord.quality == "minor":
        return _make_triad(chord.root, "major")
    return chord  # diminished — no P transform defined


def leading_tone(chord: Chord) -> Chord:
    """L operation: move the root down a semitone for major, fifth up for minor.

    C major (0,4,7) -> E minor (4,7,11)
    E minor (4,7,11) -> C major (0,4,7)

    For a major triad, the root drops by one semitone and becomes the new
    fifth of a minor triad.  For a minor triad, the fifth rises by one
    semitone and becomes the new root of a major triad.
    """
    if chord.quality == "major":
        # Root descends a semitone -> becomes fifth of new minor triad.
        # New triad: root = major third, quality = minor.
        new_root = (chord.root + 4) % 12  # the major third
        return _make_triad(new_root, "minor")
    elif chord.quality == "minor":
        # Fifth ascends a semitone -> becomes root of new major triad.
        # Minor fifth is root+7; ascending gives root+8, but the new major
        # triad has that as... let's derive: minor (r, r+3, r+7).
        # L sends it to major with root = (r+7+1) - 7 = r+1?  No.
        # Standard L: C major <-> E minor.  E minor = (4,7,11).
        # From E minor: fifth = 11, raise to 0.  New triad has notes {4,7,0}.
        # That's C major (0,4,7).  Root of the new major = 0 = (11+1)%12.
        # So new_root = (minor_fifth + 1) % 12, where minor_fifth = (root+7).
        new_root = (chord.root + 7 + 1) % 12
        return _make_triad(new_root, "major")
    return chord


def relative(chord: Chord) -> Chord:
    """R operation: relative major/minor transformation.

    C major (0,4,7) -> A minor (9,0,4)
    A minor (9,0,4) -> C major (0,4,7)

    For major, the fifth rises a whole step to become root of the relative
    minor. For minor, the root drops a whole step to become the fifth of
    the relative major.
    """
    if chord.quality == "major":
        # Major -> relative minor: new root is a minor third below the root,
        # i.e. root - 3 (= root + 9).  C major -> A minor.
        new_root = (chord.root + 9) % 12
        return _make_triad(new_root, "minor")
    elif chord.quality == "minor":
        # Minor -> relative major: new root is a minor third above,
        # i.e. root + 3.  A minor -> C major.
        new_root = (chord.root + 3) % 12
        return _make_triad(new_root, "major")
    return chord


# ---------------------------------------------------------------------------
# Tonnetz graph — BFS navigation
# ---------------------------------------------------------------------------

# The 24 PLR operations for all major/minor triads.
_PLR_OPS: list[tuple[str, callable]] = [
    ("P", parallel),
    ("L", leading_tone),
    ("R", relative),
]


def _build_tonnetz_graph() -> dict[tuple[int, str], list[tuple[str, tuple[int, str]]]]:
    """Build adjacency list for the 24-node Tonnetz graph.

    Each node is (root_pc, quality).  Each edge is labelled with the
    operation name ('P', 'L', or 'R').
    """
    graph: dict[tuple[int, str], list[tuple[str, tuple[int, str]]]] = {}
    for root in range(12):
        for quality in ("major", "minor"):
            node = (root, quality)
            chord = _make_triad(root, quality)
            neighbors = []
            for name, op in _PLR_OPS:
                result = op(chord)
                neighbors.append((name, _triad_key(result)))
            graph[node] = neighbors
    return graph


# Pre-compute the graph at module load time (24 nodes, 72 edges — tiny).
_TONNETZ_GRAPH = _build_tonnetz_graph()


def tonnetz_distance(chord_a: Chord, chord_b: Chord) -> int:
    """Minimum number of PLR operations to transform chord_a into chord_b.

    Uses BFS on the 24-node Tonnetz graph.  Returns -1 if either chord is
    not a major or minor triad (e.g. diminished).

    Parameters
    ----------
    chord_a, chord_b : Source and target triads.

    Returns
    -------
    int : Minimum PLR distance (0 if identical, max 4 for any pair).
    """
    start = _triad_key(chord_a)
    goal = _triad_key(chord_b)

    if start not in _TONNETZ_GRAPH or goal not in _TONNETZ_GRAPH:
        return -1
    if start == goal:
        return 0

    from collections import deque
    visited: set[tuple[int, str]] = {start}
    queue: deque[tuple[tuple[int, str], int]] = deque([(start, 0)])

    while queue:
        node, dist = queue.popleft()
        for _, neighbor in _TONNETZ_GRAPH[node]:
            if neighbor == goal:
                return dist + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return -1  # unreachable in a connected graph, but safety


def tonnetz_path(chord_a: Chord, chord_b: Chord) -> list[tuple[str, Chord]]:
    """Return the shortest PLR path from chord_a to chord_b.

    Each element is (operation_name, resulting_chord) after applying that
    operation.  Returns an empty list if chords are identical or not
    major/minor triads.

    Parameters
    ----------
    chord_a, chord_b : Source and target triads.

    Returns
    -------
    list of (str, Chord) : The sequence of operations and intermediate chords.
    """
    start = _triad_key(chord_a)
    goal = _triad_key(chord_b)

    if start not in _TONNETZ_GRAPH or goal not in _TONNETZ_GRAPH:
        return []
    if start == goal:
        return []

    from collections import deque
    visited: dict[tuple[int, str], tuple[tuple[int, str], str]] = {start: (start, "")}
    queue: deque[tuple[int, str]] = deque([start])

    found = False
    while queue:
        node = queue.popleft()
        for op_name, neighbor in _TONNETZ_GRAPH[node]:
            if neighbor not in visited:
                visited[neighbor] = (node, op_name)
                if neighbor == goal:
                    found = True
                    break
                queue.append(neighbor)
        if found:
            break

    if not found:
        return []

    # Reconstruct path.
    path_keys: list[tuple[str, tuple[int, str]]] = []
    current = goal
    while current != start:
        parent, op_name = visited[current]
        path_keys.append((op_name, current))
        current = parent
    path_keys.reverse()

    return [(op, _make_triad(root, qual)) for op, (root, qual) in path_keys]


# ---------------------------------------------------------------------------
# Neo-Riemannian progression generation
# ---------------------------------------------------------------------------

def neo_riemannian_progression(
    start_chord: Chord,
    end_chord: Chord,
    n_steps: int,
    seed: int = 42,
) -> list[Chord]:
    """Generate a smooth chord progression from start to end using PLR operations.

    Uses the shortest Tonnetz path as the backbone.  When more steps are
    requested than the shortest path length, inserts musically interesting
    detours (random PLR side-steps that return to the path).

    Parameters
    ----------
    start_chord : Starting triad.
    end_chord : Target triad.
    n_steps : Desired number of chords in the output (including start and end).
    seed : Random seed for detour selection.

    Returns
    -------
    list of Chord : The progression from start_chord to end_chord.
    """
    if n_steps < 2:
        n_steps = 2

    shortest = tonnetz_path(start_chord, end_chord)
    # Build the backbone: start -> ...path chords... -> end
    backbone = [start_chord] + [ch for _, ch in shortest]

    # If we already have enough or more chords than requested, trim.
    if len(backbone) >= n_steps:
        # Keep start, evenly spaced intermediates, and end.
        if n_steps == 2:
            return [backbone[0], backbone[-1]]
        step = (len(backbone) - 1) / (n_steps - 1)
        indices = [round(i * step) for i in range(n_steps)]
        return [backbone[i] for i in indices]

    # We need more chords — insert detours.
    rng = random.Random(seed)
    result = list(backbone)
    ops = [parallel, leading_tone, relative]

    while len(result) < n_steps:
        # Pick a random insertion point (not the last chord).
        if len(result) <= 2:
            insert_idx = 1
        else:
            insert_idx = rng.randint(1, len(result) - 1)

        anchor = result[insert_idx - 1]
        # Apply a random PLR op as a side-step, then return.
        op = rng.choice(ops)
        detour = op(anchor)

        # Only insert if it's different from its neighbors to avoid stasis.
        prev_key = _triad_key(result[insert_idx - 1])
        next_key = _triad_key(result[insert_idx]) if insert_idx < len(result) else None
        detour_key = _triad_key(detour)

        if detour_key != prev_key and detour_key != next_key:
            result.insert(insert_idx, detour)
        else:
            # Try another op.
            for alt_op in ops:
                detour = alt_op(anchor)
                detour_key = _triad_key(detour)
                if detour_key != prev_key and detour_key != next_key:
                    result.insert(insert_idx, detour)
                    break
            else:
                # All ops produce duplicates; just insert anyway to reach n_steps.
                result.insert(insert_idx, detour)

    return result


def generate_progression_neo(
    n_chords: int,
    key: str,
    seed: int = 42,
    modulation_target: str | None = None,
) -> list[Chord]:
    """Generate a chord progression using neo-Riemannian transitions for modulation.

    Behaves like ``generate_progression`` for diatonic motion within a key.
    When *modulation_target* is specified, the progression smoothly modulates
    from *key* to the target key using PLR operations on the Tonnetz, then
    cadences in the target key.

    Parameters
    ----------
    n_chords : Total number of chords (minimum 4 when modulating).
    key : Starting key, e.g. ``'C_major'``.
    seed : Random seed for reproducibility.
    modulation_target : Target key for modulation, e.g. ``'F#_minor'``.
        If ``None``, falls back to ``generate_progression``.

    Returns
    -------
    list of Chord : The full progression.
    """
    if modulation_target is None:
        return generate_progression(n_chords=n_chords, key=key, seed=seed)

    if n_chords < 4:
        n_chords = 4

    # Allocate: opening in home key, neo-Riemannian bridge, cadence in target.
    opening_len = max(2, n_chords // 3)
    cadence_len = 2  # V-I in target key
    bridge_len = n_chords - opening_len - cadence_len
    if bridge_len < 1:
        bridge_len = 1
        opening_len = n_chords - bridge_len - cadence_len

    # 1. Opening: diatonic in home key.
    opening = generate_progression(n_chords=opening_len, key=key, seed=seed)

    # 2. Bridge: neo-Riemannian path from last chord of opening to I of target.
    tonic_home = opening[-1]
    tonic_target = roman_to_chord("I", modulation_target)
    bridge = neo_riemannian_progression(
        start_chord=tonic_home,
        end_chord=tonic_target,
        n_steps=bridge_len + 2,  # +2 because start/end overlap with neighbors
        seed=seed,
    )
    # Remove the first (duplicate of opening's last) and last (duplicate of
    # target tonic which appears in the cadence).
    bridge = bridge[1:-1] if len(bridge) > 2 else bridge[:bridge_len]

    # 3. Cadence: V-I in target key.
    cadence = [
        roman_to_chord("V", modulation_target),
        roman_to_chord("I", modulation_target),
    ]

    progression = opening + bridge + cadence

    # Trim or pad to exactly n_chords.
    if len(progression) > n_chords:
        # Keep opening and cadence, trim bridge.
        progression = opening + bridge[:n_chords - opening_len - cadence_len] + cadence
    elif len(progression) < n_chords:
        # Extend bridge with detours.
        extra = n_chords - len(progression)
        rng = random.Random(seed + 99)
        for _ in range(extra):
            insert_pos = opening_len + rng.randint(0, len(bridge))
            anchor = progression[max(0, insert_pos - 1)]
            op = rng.choice([parallel, leading_tone, relative])
            progression.insert(insert_pos, op(anchor))

    return progression[:n_chords]
