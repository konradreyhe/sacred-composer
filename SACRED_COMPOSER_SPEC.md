# Sacred Composer -- Specification Document

> Code as composition. Sacred patterns as source material.

This document specifies `sacred_composer`, a Python library where mathematical and natural patterns ARE the music. There is no prompt, no AI, no randomness-as-default. The composer writes Python. The Python IS the score.

The existing MUSIK! system (composer.py, SYSTEM_ARCHITECTURE.py) is a prompt-driven pipeline: text in, MIDI out. Sacred Composer inverts this. The programmer selects patterns from nature and mathematics, maps them to musical parameters, layers them, and renders. Every note is traceable to a pattern. The code is the composition.

---

## Design Philosophy

1. **Patterns are first-class objects.** A Fibonacci sequence, a Lorenz attractor, a cellular automaton -- each is a generator that yields values. These values have no musical meaning yet. They are pure pattern.

2. **Mappers give patterns musical meaning.** `to_pitch()` maps values to MIDI notes. `to_rhythm()` maps values to durations. The same pattern can become melody, rhythm, dynamics, or form.

3. **Composition is assembly.** The `Composition` object collects mapped patterns into voices, layers them in time, and renders to output formats.

4. **No hidden randomness.** Every note is deterministic given its pattern and parameters. If you want randomness, you choose a chaotic pattern (Lorenz, logistic map). Randomness is a pattern choice, not a default.

5. **Interoperability with existing system.** Sacred Composer can emit `PerformanceNote` and `PerformanceIR` objects from SYSTEM_ARCHITECTURE.py, allowing use of the existing MIDI rendering and humanization infrastructure.

---

## Architecture Overview

```
Pattern Generators     Mappers          Combiners        Renderers
==================    =========        ==========       ==========
fibonacci_sequence -> to_pitch ----\
golden_spiral ------> to_rhythm ---+--> layer --------> to_midi
infinity_series ----> to_dynamics -/    canon            to_lilypond
harmonic_series                         phase            to_wav
cellular_automata                       fractal_form     to_performance_ir
lorenz_attractor
euclidean_rhythm
digits_of
stern_brocot
```

The data flow is always: **generate -> map -> combine -> render.**

---

## Module: `sacred_composer.constants`

Mathematical constants used throughout the system.

```python
"""Sacred and mathematical constants."""

import math

# The golden ratio
phi: float  # (1 + math.sqrt(5)) / 2 = 1.6180339887...

# The golden angle in degrees (360 / phi^2)
golden_angle: float  # 137.5077640...

# Fibonacci semitone intervals (Bartok's vocabulary)
fibonacci_intervals: tuple[int, ...]  # (1, 1, 2, 3, 5, 8, 13)

# Common sacred/significant numbers
sacred_numbers: dict[str, float]  # {"phi": phi, "pi": math.pi, "e": math.e, ...}
```

---

## Module: `sacred_composer.patterns`

### Core Protocol

All pattern generators conform to this protocol:

```python
from typing import Protocol, Iterator, Sequence

class Pattern(Protocol):
    """Any object that can produce a sequence of numeric values."""

    def generate(self, n: int) -> list[float]:
        """Return exactly n values from this pattern."""
        ...

    def __iter__(self) -> Iterator[float]:
        """Yield values lazily (may be infinite)."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name for display and debugging."""
        ...
```

All generators listed below implement the `Pattern` protocol. They return raw numeric values with no musical interpretation.

---

### `fibonacci_sequence`

```python
class FibonacciSequence:
    """
    The Fibonacci sequence: each term is the sum of the two before it.
    F(1)=1, F(2)=1, F(3)=2, F(4)=3, F(5)=5, ...

    The ratio of consecutive terms converges to phi (1.618...).
    This sequence appears in phyllotaxis, shell spirals, branching
    patterns, and was used by Bartok for structural proportions
    (Music for Strings, Percussion and Celesta: sections of 5, 8, 13,
    21, 34 bars).

    Parameters
    ----------
    start_pair : tuple[int, int], default (1, 1)
        The first two values. Use (2, 1) for Lucas numbers.
        Use (1, 3) for other Fibonacci-like sequences.

    Examples
    --------
    >>> fib = FibonacciSequence()
    >>> fib.generate(10)
    [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]

    >>> lucas = FibonacciSequence(start_pair=(2, 1))
    >>> lucas.generate(8)
    [2, 1, 3, 4, 7, 11, 18, 29]
    """

    def __init__(self, start_pair: tuple[int, int] = (1, 1)) -> None: ...
    def generate(self, n: int) -> list[float]: ...
    def ratios(self, n: int) -> list[float]:
        """Return n consecutive ratios F(k+1)/F(k), converging to phi."""
        ...
```

---

### `golden_spiral`

```python
class GoldenSpiral:
    """
    Points placed at golden-angle intervals (137.508 degrees) around
    a growing spiral. This is the phyllotaxis pattern -- sunflower seeds,
    pine cone scales, leaf arrangements.

    Each point has an angle and a radius. The angle sequence, taken
    modulo an octave or scale, produces melodies with maximal pitch
    variety (no two consecutive notes "line up" into repetitive patterns).

    Parameters
    ----------
    seed : float, default phi
        Growth rate of the spiral radius. Using phi produces the
        classic sunflower pattern. Other values produce variants.
    angle_offset : float, default 0.0
        Starting angle in degrees.

    The generate() method returns angles in degrees [0, 360).
    A separate method returns (angle, radius) pairs.

    Examples
    --------
    >>> spiral = GoldenSpiral()
    >>> angles = spiral.generate(8)
    # [0.0, 137.508, 275.015, 52.523, 190.031, 327.538, 105.046, 242.554]
    """

    def __init__(self, seed: float = ..., angle_offset: float = 0.0) -> None: ...
    def generate(self, n: int) -> list[float]: ...
    def generate_polar(self, n: int) -> list[tuple[float, float]]:
        """Return (angle_degrees, radius) pairs."""
        ...
```

---

### `infinity_series`

```python
class InfinitySeries:
    """
    Per Norgard's infinity series: a self-similar integer sequence
    discovered in 1959, used in his Symphony No. 2, 3, and many
    other works.

    Definition:
        a(0) = 0
        a(2n) = -a(n)
        a(2n+1) = a(n) + 1

    The sequence contains every integer exactly once in its infinite
    form. At every power-of-two zoom level, the sequence is a
    transposed copy of itself -- true fractal self-similarity.

    Parameters
    ----------
    seed : int, default 0
        Starting value a(0). Norgard used 0. Other seeds produce
        transposed variants.

    Examples
    --------
    >>> inf = InfinitySeries(seed=0)
    >>> inf.generate(16)
    [0, 1, -1, 2, 1, 0, -2, 3, -1, 2, 0, 1, 2, -1, -3, 4]
    """

    def __init__(self, seed: int = 0) -> None: ...
    def generate(self, n: int) -> list[float]: ...
```

---

### `digits_of`

```python
class DigitsOf:
    """
    Extract the decimal digits of a mathematical constant and return
    them as a sequence of integers 0-9.

    Maps the transcendental to the musical. Pi becomes melody.
    e becomes rhythm. phi becomes dynamics. The digits are
    deterministic, non-repeating, and statistically uniform --
    producing melodies that never repeat but have no long-range
    bias.

    Parameters
    ----------
    constant : str
        One of: "pi", "e", "phi", "sqrt2", "sqrt3", "ln2".
        The system stores at least 10,000 digits of each.
    skip_decimal : bool, default True
        If True, skips the integer part and decimal point.
        pi -> [1,4,1,5,9,2,6,5,3,5,...] (digits after "3.")

    Examples
    --------
    >>> pi_digits = DigitsOf("pi")
    >>> pi_digits.generate(10)
    [1, 4, 1, 5, 9, 2, 6, 5, 3, 5]

    >>> e_digits = DigitsOf("e")
    >>> e_digits.generate(8)
    [7, 1, 8, 2, 8, 1, 8, 2]
    """

    def __init__(self, constant: str, skip_decimal: bool = True) -> None: ...
    def generate(self, n: int) -> list[float]: ...
```

---

### `harmonic_series`

```python
class HarmonicSeries:
    """
    The overtone series of a vibrating body. Given a fundamental
    frequency, returns the frequencies of the first N partials:
    f, 2f, 3f, 4f, 5f, ...

    This is nature's only chord. The intervals between consecutive
    partials give us the octave (2:1), perfect fifth (3:2), perfect
    fourth (4:3), major third (5:4), minor third (6:5), etc.

    Spectral composers (Grisey, Murail) use this as raw harmonic
    material. We do the same.

    Parameters
    ----------
    fundamental : str or float
        Pitch name ("C2", "A1") or frequency in Hz (55.0).
        Pitch names are converted to Hz internally.
    decay : str, default "equal"
        Amplitude model for partials:
        - "equal": all partials have amplitude 1.0
        - "natural": amplitude = 1/n (natural harmonic decay)
        - "squared": amplitude = 1/n^2 (faster decay, darker timbre)

    Examples
    --------
    >>> h = HarmonicSeries(fundamental="C2")
    >>> h.generate(8)  # frequencies in Hz
    [65.41, 130.81, 196.22, 261.63, 327.03, 392.44, 457.84, 523.25]

    >>> h.as_intervals()  # intervals between consecutive partials in cents
    [1200.0, 701.96, 498.04, 386.31, 315.64, 266.87, 231.17]

    >>> h.as_midi(8)  # MIDI note numbers (fractional, not quantized to 12-TET)
    [36.0, 48.0, 55.02, 60.0, 63.86, 67.02, 69.69, 72.0]
    """

    def __init__(self, fundamental: str | float, decay: str = "equal") -> None: ...
    def generate(self, n: int) -> list[float]: ...
    def as_intervals(self, n: int = 16) -> list[float]: ...
    def as_midi(self, n: int = 16) -> list[float]: ...
    def as_chord(self, n: int = 8, quantize: bool = True) -> list[int]:
        """
        Return the first n partials as MIDI note numbers.
        If quantize=True, round to nearest 12-TET semitone.
        If quantize=False, return fractional MIDI for microtonal use.
        """
        ...
```

---

### `cellular_automata`

```python
class CellularAutomata:
    """
    Elementary cellular automata (Wolfram). A 1D row of cells evolves
    according to a rule number (0-255). Each generation is a new row.
    The resulting 2D grid of on/off cells can be mapped to:
    - pitch (on = note plays, off = rest)
    - rhythm (on = onset, off = continuation)
    - multiple voices (each row = time step, each column = a voice)

    Rule 110 is Turing-complete. Rule 30 is chaotic (used by
    Mathematica for random number generation). Rule 90 produces
    Sierpinski triangles. Each rule has a distinct musical character.

    Parameters
    ----------
    rule : int
        Wolfram rule number, 0-255. Notable rules:
        - 30: chaotic, pseudo-random (good for unpredictable textures)
        - 90: Sierpinski triangle, self-similar (fractal structure)
        - 110: complex, Turing-complete (balanced order/chaos)
        - 184: traffic flow model (rhythmic, wave-like)
    width : int, default 16
        Number of cells in each row (= number of voices or pitch slots).
    initial_state : list[int] | None, default None
        Starting row. If None, uses a single 1 in the center.

    Examples
    --------
    >>> ca = CellularAutomata(rule=110, width=8)
    >>> grid = ca.generate(16)  # 16 time steps
    # Returns 16 rows of 8 values (0 or 1), total 128 values
    # Flattened: [0,0,0,0,1,0,0,0, 0,0,0,1,1,1,0,0, ...]

    >>> ca.generate_grid(16)  # returns list[list[int]], 16 rows x 8 cols
    """

    def __init__(
        self,
        rule: int,
        width: int = 16,
        initial_state: list[int] | None = None,
    ) -> None: ...
    def generate(self, n: int) -> list[float]: ...
    def generate_grid(self, steps: int) -> list[list[int]]: ...
```

---

### `lorenz_attractor`

```python
class LorenzAttractor:
    """
    The Lorenz system: three coupled differential equations that
    produce deterministic chaos. The trajectory never repeats, never
    settles, and is sensitive to initial conditions (the butterfly
    effect).

        dx/dt = sigma * (y - x)
        dy/dt = x * (rho - z) - y
        dz/dt = x * y - beta * z

    Classic parameters: sigma=10, rho=28, beta=8/3.

    The three coordinates (x, y, z) can be mapped independently to
    pitch, rhythm, and dynamics -- producing music that is structured
    (the attractor has a definite shape) but never exactly repeats.

    Parameters
    ----------
    sigma : float, default 10.0
    rho : float, default 28.0
    beta : float, default 8/3
    dt : float, default 0.01
        Integration time step. Smaller = smoother trajectory.
    initial : tuple[float, float, float], default (1.0, 1.0, 1.0)
        Starting point (x0, y0, z0).

    Examples
    --------
    >>> lorenz = LorenzAttractor()
    >>> trajectory = lorenz.generate(1000)
    # Returns 1000 x-values (use .generate_xyz() for all three axes)

    >>> xyz = lorenz.generate_xyz(1000)
    # Returns list of (x, y, z) tuples
    """

    def __init__(
        self,
        sigma: float = 10.0,
        rho: float = 28.0,
        beta: float = 8 / 3,
        dt: float = 0.01,
        initial: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None: ...
    def generate(self, n: int) -> list[float]: ...
    def generate_xyz(self, n: int) -> list[tuple[float, float, float]]: ...
```

---

### `euclidean_rhythm`

```python
class EuclideanRhythm:
    """
    Bjorklund's algorithm: distribute k onsets as evenly as possible
    across n pulses. This generates a binary pattern that, for many
    (k, n) combinations, produces traditional world rhythms:

        E(2, 5) = [1,0,1,0,0]  -- Persian khafif-e-ramal
        E(3, 8) = [1,0,0,1,0,0,1,0]  -- Cuban tresillo
        E(5, 8) = [1,0,1,1,0,1,1,0]  -- Cuban cinquillo
        E(5,12) = [1,0,0,1,0,1,0,0,1,0,1,0]  -- South African Venda
        E(7,12) = [1,0,1,1,0,1,0,1,1,0,1,0]  -- West African bell
        E(7,16) = [1,0,0,1,0,1,0,1,0,0,1,0,1,0,1,0]  -- Brazilian samba

    Godfried Toussaint showed these rhythms maximize "evenness" --
    the mathematical property that makes them feel balanced yet
    interesting. This is the rhythmic analog of the golden angle
    in phyllotaxis.

    Parameters
    ----------
    onsets : int
        Number of sounding beats (k).
    pulses : int
        Total number of time slots (n).
    rotation : int, default 0
        Rotate the pattern by this many positions (accents shift).

    Examples
    --------
    >>> e = EuclideanRhythm(onsets=5, pulses=8)
    >>> e.generate(8)
    [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0]

    >>> e.generate(16)  # repeats the 8-pulse pattern
    [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, ...]
    """

    def __init__(self, onsets: int, pulses: int, rotation: int = 0) -> None: ...
    def generate(self, n: int) -> list[float]: ...
    @property
    def pattern(self) -> list[int]:
        """The base binary pattern before repetition."""
        ...
```

---

### `stern_brocot`

```python
class SternBrocot:
    """
    The Stern-Brocot tree: a binary tree that contains every positive
    rational number exactly once. Level 0 has 0/1 and 1/0 as
    boundaries. Each new fraction is the mediant (a+c)/(b+d) of its
    neighbors a/b and c/d.

    Level 1: 1/1
    Level 2: 1/2, 2/1
    Level 3: 1/3, 2/3, 3/2, 3/1
    ...

    This enumerates ALL possible rhythmic ratios in order of
    complexity: 1:1 (equal), 1:2 (double), 2:3 (hemiola), 3:4
    (triplet feel), etc. It is the natural ordering of rhythmic
    relationships from simple to complex.

    Parameters
    ----------
    depth : int, default 4
        Number of levels to generate. Level d has 2^d fractions.

    Examples
    --------
    >>> sb = SternBrocot(depth=3)
    >>> sb.generate(8)  # returns fractions as floats
    [1.0, 0.5, 2.0, 0.333, 0.667, 1.5, 3.0, 0.25]

    >>> sb.as_fractions(8)  # returns (numerator, denominator) pairs
    [(1,1), (1,2), (2,1), (1,3), (2,3), (3,2), (3,1), (1,4)]
    """

    def __init__(self, depth: int = 4) -> None: ...
    def generate(self, n: int) -> list[float]: ...
    def as_fractions(self, n: int) -> list[tuple[int, int]]: ...
```

---

### `pink_noise`

```python
class PinkNoise:
    """
    1/f noise: spectral energy inversely proportional to frequency.
    Between white noise (uniform random) and brown noise (random walk).

    1/f noise matches the statistical profile of natural phenomena:
    heartbeat intervals, river discharge, stock prices, loudness
    fluctuations in speech, and -- crucially -- the pitch and timing
    contours of music (Voss and Clarke, 1975).

    Used for humanization: adds micro-variations to timing, velocity,
    and pitch that sound natural rather than mechanical.

    Parameters
    ----------
    sigma : float, default 1.0
        Standard deviation of the output values. For timing
        humanization, use sigma in milliseconds (e.g., sigma=12
        for 12ms standard deviation). For velocity, use sigma in
        MIDI velocity units (e.g., sigma=5).
    seed : int | None, default None
        Random seed for reproducibility. None = non-deterministic.

    Examples
    --------
    >>> noise = PinkNoise(sigma=12.0, seed=42)
    >>> offsets = noise.generate(64)
    # 64 values with 1/f spectral distribution, std dev ~12.0
    """

    def __init__(self, sigma: float = 1.0, seed: int | None = None) -> None: ...
    def generate(self, n: int) -> list[float]: ...
```

---

### `logistic_map`

```python
class LogisticMap:
    """
    The logistic map: x(n+1) = r * x(n) * (1 - x(n)).

    A single equation that exhibits the full route from order to
    chaos as the parameter r increases:
        r < 3.0: converges to a fixed point (monotony)
        r ~ 3.0-3.45: period-2 oscillation (simple alternation)
        r ~ 3.45-3.57: period doubling cascade (increasing complexity)
        r > 3.57: chaos with islands of order (period-3 windows)
        r = 4.0: full chaos (ergodic, every value visited)

    The "edge of chaos" around r=3.57 is musically the most
    interesting: enough structure to be followable, enough surprise
    to be engaging. This mirrors the 1/f sweet spot.

    Parameters
    ----------
    r : float, default 3.99
        Control parameter. 3.57 is the onset of chaos.
        4.0 is full chaos. Values between 3.8 and 3.99 are
        musically useful.
    x0 : float, default 0.5
        Initial value, must be in (0, 1).

    Examples
    --------
    >>> lm = LogisticMap(r=3.99, x0=0.5)
    >>> lm.generate(16)
    # 16 values in (0, 1), chaotic but deterministic
    """

    def __init__(self, r: float = 3.99, x0: float = 0.5) -> None: ...
    def generate(self, n: int) -> list[float]: ...
```

---

### `lindenmayer`

```python
class Lindenmayer:
    """
    L-system (Lindenmayer system): a parallel string-rewriting grammar.
    Start with an axiom string, apply production rules simultaneously
    to all characters, repeat for a given number of iterations.

    L-systems generate fractal structures: trees, ferns, dragon curves,
    Hilbert curves. In music, they produce self-similar melodic and
    formal structures.

    Parameters
    ----------
    axiom : str
        Starting string. E.g., "A".
    rules : dict[str, str]
        Production rules. E.g., {"A": "ABA", "B": "BCB", "C": "A"}.
        Characters not in the rules dictionary are left unchanged.
    alphabet_values : dict[str, float] | None
        Mapping from characters to numeric values. E.g.,
        {"A": 0, "B": 2, "C": 4}. If None, characters are mapped
        to their ordinal positions (A=0, B=1, C=2, ...).

    Examples
    --------
    >>> l = Lindenmayer(axiom="A", rules={"A": "AB", "B": "A"})
    >>> l.expand(5)
    "ABAABABA"  # the string after 5 iterations

    >>> l.generate(21)
    # numeric values for the first 21 characters of the expansion
    # Using default alphabet: A=0, B=1 -> [0,1,0,0,1,0,1,0,...]

    >>> # Formal structure: A->ABA, B->BCB mimics exposition-development
    >>> form = Lindenmayer(
    ...     axiom="A",
    ...     rules={"A": "ABA", "B": "BCB", "C": "A"},
    ...     alphabet_values={"A": 0, "B": 5, "C": 7}
    ... )
    >>> form.generate(27)  # depth-3 expansion
    """

    def __init__(
        self,
        axiom: str,
        rules: dict[str, str],
        alphabet_values: dict[str, float] | None = None,
    ) -> None: ...
    def expand(self, depth: int) -> str: ...
    def generate(self, n: int) -> list[float]: ...
    @property
    def depth(self) -> int:
        """Current expansion depth."""
        ...
```

---

## Module: `sacred_composer.mappers`

Mappers translate raw pattern values into musical parameters. They are pure functions (no side effects, no state). Each returns a list of the same length as the input.

### `to_pitch`

```python
def to_pitch(
    values: list[float],
    scale: str = "C_major",
    octave_range: tuple[int, int] = (3, 6),
    strategy: str = "modular",
) -> list[int]:
    """
    Map numeric values to MIDI note numbers within a scale.

    Parameters
    ----------
    values : list[float]
        Raw pattern values (any range).
    scale : str
        Scale name. Format: "{root}_{type}". Examples:
        "C_major", "A_minor", "D_dorian", "F#_harmonic_minor",
        "Eb_whole_tone", "C_chromatic", "A_pentatonic_minor".
    octave_range : tuple[int, int]
        MIDI octave bounds (inclusive). (3, 6) means C3 to B6.
    strategy : str
        How to map values to scale degrees:
        - "modular": value mod num_scale_degrees -> degree index
          (wraps around, good for integer sequences like digits_of)
        - "normalize": linearly scale values to fit the octave range
          (good for continuous values like Lorenz coordinates)
        - "nearest": quantize each value (treated as a MIDI number
          or frequency) to the nearest note in the scale

    Returns
    -------
    list[int]
        MIDI note numbers, one per input value.

    Examples
    --------
    >>> to_pitch([1,4,1,5,9,2,6,5], scale="C_major", strategy="modular")
    [62, 67, 62, 69, 64, 64, 71, 69]  # D4, G4, D4, A4, E4, E4, B4, A4

    >>> to_pitch(lorenz.generate(32), scale="A_minor", strategy="normalize")
    # 32 MIDI notes distributed across A minor, octaves 3-6
    """
    ...
```

---

### `to_rhythm`

```python
def to_rhythm(
    values: list[float],
    base_duration: float = 1.0,
    time_signature: tuple[int, int] = (4, 4),
    strategy: str = "proportional",
) -> list[float]:
    """
    Map numeric values to note durations in beats.

    Parameters
    ----------
    values : list[float]
        Raw pattern values.
    base_duration : float
        Duration in beats for the "unit" value. Default 1.0 = quarter note.
    time_signature : tuple[int, int]
        (beats_per_bar, beat_unit). Used for bar-alignment when
        strategy is "quantize".
    strategy : str
        - "proportional": duration = value * base_duration.
          E.g., Fibonacci [1,1,2,3,5] -> [1.0, 1.0, 2.0, 3.0, 5.0] beats
        - "binary": value > threshold -> base_duration, else rest.
          Good for Euclidean rhythms and cellular automata.
        - "quantize": snap to nearest standard duration
          (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0 beats).
        - "ratio": values are interpreted as duration ratios
          from Stern-Brocot fractions.

    Returns
    -------
    list[float]
        Durations in beats. Negative values indicate rests.

    Examples
    --------
    >>> to_rhythm([1,0,1,1,0,1,1,0], strategy="binary", base_duration=0.5)
    [0.5, -0.5, 0.5, 0.5, -0.5, 0.5, 0.5, -0.5]  # cinquillo with rests

    >>> to_rhythm(SternBrocot(depth=3).generate(8), strategy="ratio")
    [1.0, 0.5, 2.0, 0.333, 0.667, 1.5, 3.0, 0.25]
    """
    ...
```

---

### `to_dynamics`

```python
def to_dynamics(
    values: list[float],
    velocity_range: tuple[int, int] = (40, 110),
    strategy: str = "normalize",
) -> list[int]:
    """
    Map numeric values to MIDI velocity (1-127).

    Parameters
    ----------
    values : list[float]
        Raw pattern values.
    velocity_range : tuple[int, int]
        Output range (min_velocity, max_velocity).
        Common ranges:
        - (40, 110): pp to ff
        - (60, 90): mp to f (subtle)
        - (20, 127): ppp to fff (full range)
    strategy : str
        - "normalize": linearly scale values to velocity range
        - "threshold": value > median -> high velocity, else low
        - "absolute": values are used directly as velocities (clamped)

    Returns
    -------
    list[int]
        MIDI velocity values, one per input value.

    Examples
    --------
    >>> to_dynamics(PinkNoise(sigma=1.0).generate(32), velocity_range=(50, 100))
    # 32 velocity values with natural 1/f fluctuation
    """
    ...
```

---

### `to_form`

```python
def to_form(
    values: list[float],
    total_bars: int,
    section_labels: list[str] | None = None,
) -> list[FormSection]:
    """
    Map numeric values to formal section boundaries.

    Uses the values as proportional lengths of sections.
    E.g., Fibonacci [5, 8, 13, 8, 5] with total_bars=39 ->
    sections of 5, 8, 13, 8, 5 bars.

    Parameters
    ----------
    values : list[float]
        Proportional section lengths.
    total_bars : int
        Total number of bars. Values are scaled proportionally.
    section_labels : list[str] | None
        Optional labels for each section. If None, labels are
        generated as "A", "B", "C", ...

    Returns
    -------
    list[FormSection]
        Section definitions with bar ranges and labels.
    """
    ...


@dataclass
class FormSection:
    """One section in a formal plan."""
    label: str          # "A", "B", "C", "A'", etc.
    start_bar: int
    end_bar: int
    bars: int
    key: str | None     # optional key for this section
    character: str | None  # optional character/mood
```

---

## Module: `sacred_composer.core`

### `Note`

```python
@dataclass
class Note:
    """
    A single musical event.

    This is the fundamental unit of the sacred_composer internal
    representation. Notes are collected into Voices, Voices into
    a Score, and the Score is rendered to output formats.
    """
    pitch: int              # MIDI note number (0-127), -1 for rest
    start: float            # start time in beats from beginning of piece
    duration: float         # duration in beats
    velocity: int           # MIDI velocity (1-127)
    voice: int              # voice index (0-based)
    articulation: str       # "legato", "staccato", "accent", etc.
    tied_to_next: bool      # if True, this note is tied to the next

    @property
    def end(self) -> float:
        """End time in beats."""
        ...

    @property
    def is_rest(self) -> bool:
        """True if this is a rest (pitch == -1)."""
        ...
```

---

### `Voice`

```python
@dataclass
class Voice:
    """
    A monophonic sequence of Notes. A single melodic line.

    Voices can be built from patterns using the from_patterns()
    class method, or assembled manually note by note.
    """
    notes: list[Note]
    name: str               # "soprano", "bass", "voice_0", etc.
    channel: int            # MIDI channel (0-15)
    instrument: str         # GM instrument name or number

    @classmethod
    def from_patterns(
        cls,
        pitches: list[int],
        durations: list[float],
        velocities: list[int] | None = None,
        name: str = "voice",
        channel: int = 0,
        instrument: str = "piano",
    ) -> Voice:
        """
        Build a Voice from parallel lists of pitches, durations,
        and optional velocities.

        The lists are zipped together. If velocities is None,
        all notes get velocity 80. If lists differ in length,
        the shortest determines the number of notes.

        Parameters
        ----------
        pitches : list[int]
            MIDI note numbers. Use -1 for rests.
        durations : list[float]
            Duration of each note in beats. Negative values are
            converted to rests of abs(duration).
        velocities : list[int] | None
            MIDI velocities. If None, defaults to 80 for all notes.

        Returns
        -------
        Voice
        """
        ...

    def transpose(self, semitones: int) -> Voice:
        """Return a new Voice transposed by the given interval."""
        ...

    def retrograde(self) -> Voice:
        """Return a new Voice with notes in reverse order."""
        ...

    def invert(self, axis: int | None = None) -> Voice:
        """
        Return a new Voice with intervals inverted around an axis pitch.
        If axis is None, uses the first note's pitch.
        """
        ...

    def augment(self, factor: float = 2.0) -> Voice:
        """Return a new Voice with all durations multiplied by factor."""
        ...

    def diminish(self, factor: float = 2.0) -> Voice:
        """Return a new Voice with all durations divided by factor."""
        ...

    @property
    def total_duration(self) -> float:
        """Total duration in beats."""
        ...
```

---

### `Score`

```python
@dataclass
class Score:
    """
    A collection of Voices with tempo, time signature, and metadata.

    This is the central object that Renderers consume.
    """
    voices: list[Voice]
    tempo: float                    # BPM
    time_signature: tuple[int, int] # (numerator, denominator)
    key: str                        # e.g., "C_major", "A_minor"
    title: str
    metadata: dict[str, str]        # free-form metadata

    def add_voice(self, voice: Voice) -> None:
        """Append a voice to the score."""
        ...

    def total_duration_beats(self) -> float:
        """Duration of the longest voice in beats."""
        ...

    def total_duration_seconds(self) -> float:
        """Duration in seconds at the given tempo."""
        ...

    def to_performance_ir(self) -> "PerformanceIR":
        """
        Convert to the existing SYSTEM_ARCHITECTURE.PerformanceIR format
        for compatibility with the existing MIDI rendering pipeline.
        """
        ...
```

---

### `Composition`

```python
class Composition:
    """
    The top-level compositional workspace. This is the entry point
    for the composer-programmer.

    A Composition accumulates pattern assignments, builds a Score
    internally, and renders to output formats. It supports both
    the property-assignment style (piece.melody = ...) and the
    explicit build-and-render style.

    Parameters
    ----------
    key : str, default "C"
        Key of the piece. Accepts: "C", "Am", "F#m", "Bb",
        "C_major", "A_minor", etc.
    tempo : int, default 120
        Tempo in BPM.
    time_signature : tuple[int, int], default (4, 4)
        Time signature as (beats, beat_unit).
    title : str, default ""
        Title of the composition.

    Properties (assignable)
    -----------------------
    form : list[FormSection]
        Formal structure. Assign from to_form() or fibonacci_form().
    harmony : list[int] | Pattern
        Harmonic material (pitches, chord tones, or a Pattern).
    melody : list[int] | Pattern
        Melodic material.
    rhythm : list[float] | Pattern
        Rhythmic material.
    dynamics : list[int] | Pattern
        Dynamic material (velocities).
    texture : Pattern | None
        Texture control pattern (e.g., cellular_automata for
        voice activation).
    development : Pattern | None
        Developmental structure (e.g., L-system for formal growth).
    humanize : Pattern | None
        Humanization pattern (e.g., pink_noise for timing offsets).
    voices : int
        Number of voices (default 1).

    Examples
    --------
    >>> piece = Composition(key="C", tempo=72)
    >>> piece.form = fibonacci_form(total_bars=34)
    >>> piece.melody = golden_spiral(seed=phi, scale="minor")
    >>> piece.rhythm = euclidean(onsets=5, pulses=8)
    >>> piece.render("output.mid")
    """

    def __init__(
        self,
        key: str = "C",
        tempo: int = 120,
        time_signature: tuple[int, int] = (4, 4),
        title: str = "",
    ) -> None: ...

    # -- Pattern assignment properties --

    @property
    def form(self) -> list[FormSection] | None: ...
    @form.setter
    def form(self, value: list[FormSection] | Pattern) -> None:
        """
        Accept a list of FormSection or a Pattern.
        If a Pattern, calls to_form() internally with self.total_bars.
        """
        ...

    @property
    def harmony(self) -> list[int] | None: ...
    @harmony.setter
    def harmony(self, value: list[int] | Pattern) -> None:
        """
        Accept MIDI note numbers, frequencies, or a Pattern.
        If a Pattern, calls to_pitch() internally with the
        composition's key and octave range.
        """
        ...

    @property
    def melody(self) -> list[int] | None: ...
    @melody.setter
    def melody(self, value: list[int] | Pattern) -> None: ...

    @property
    def rhythm(self) -> list[float] | None: ...
    @rhythm.setter
    def rhythm(self, value: list[float] | Pattern) -> None: ...

    @property
    def dynamics(self) -> list[int] | None: ...
    @dynamics.setter
    def dynamics(self, value: list[int] | Pattern) -> None: ...

    @property
    def texture(self) -> "CellularAutomata | None": ...
    @texture.setter
    def texture(self, value: Pattern) -> None: ...

    @property
    def development(self) -> "Lindenmayer | None": ...
    @development.setter
    def development(self, value: Pattern) -> None: ...

    @property
    def humanize(self) -> "PinkNoise | None": ...
    @humanize.setter
    def humanize(self, value: Pattern) -> None: ...

    voices: int  # number of voices, default 1

    # -- Build methods --

    def build(self) -> Score:
        """
        Assemble the assigned patterns into a Score.

        Build process:
        1. Determine total duration from form or melody/rhythm length.
        2. Generate pitch sequence from melody pattern + key.
        3. Generate duration sequence from rhythm pattern.
        4. Generate velocity sequence from dynamics pattern.
        5. If texture pattern is set, generate voice activation grid.
        6. If development pattern is set, apply formal expansion.
        7. Assemble Note objects into Voice objects.
        8. If humanize pattern is set, apply micro-offsets to timing
           and velocity.
        9. Package everything into a Score.

        Returns
        -------
        Score
        """
        ...

    # -- Render methods --

    def render(self, path: str, **kwargs) -> None:
        """
        Build the score (if not already built) and write to file.
        Format is inferred from the file extension:
        - .mid / .midi -> MIDI
        - .ly -> LilyPond
        - .wav -> WAV audio
        - .json -> JSON (Score serialization)

        Parameters
        ----------
        path : str
            Output file path.
        **kwargs
            Passed to the appropriate renderer.
        """
        ...
```

---

## Module: `sacred_composer.combiners`

### `layer`

```python
def layer(*voices: Voice, align: str = "start") -> list[Voice]:
    """
    Combine multiple Voices to play simultaneously.

    This is the simplest combiner: all voices start at the same time
    (or are aligned according to the align parameter) and play
    independently.

    Parameters
    ----------
    *voices : Voice
        Any number of Voice objects.
    align : str
        - "start": all voices begin at beat 0
        - "end": all voices end at the same beat (shorter voices
          are padded with rests at the beginning)
        - "center": voices are centered around the midpoint

    Returns
    -------
    list[Voice]
        The input voices with adjusted start times.

    Examples
    --------
    >>> melody = Voice.from_patterns(pitches=[60,62,64], durations=[1,1,2])
    >>> bass = Voice.from_patterns(pitches=[36,43], durations=[2,2])
    >>> score_voices = layer(melody, bass)
    """
    ...
```

---

### `canon`

```python
def canon(
    leader: Voice,
    num_voices: int = 2,
    offsets_beats: list[float] | None = None,
    transpositions: list[int] | None = None,
    transformations: list[str] | None = None,
) -> list[Voice]:
    """
    Create a canon (round) from a single Voice.

    Each follower enters after a delay and optionally transposed or
    transformed (inverted, retrograde, etc.).

    Parameters
    ----------
    leader : Voice
        The leading voice (dux).
    num_voices : int
        Total number of voices including the leader.
    offsets_beats : list[float] | None
        Entry delay for each follower in beats.
        Length must be num_voices - 1.
        If None, each follower enters one bar after the previous.
    transpositions : list[int] | None
        Transposition in semitones for each follower.
        If None, all followers are at unison (strict canon).
    transformations : list[str] | None
        Transformation for each follower: "prime", "inversion",
        "retrograde", "retrograde_inversion".
        If None, all followers use "prime".

    Returns
    -------
    list[Voice]
        num_voices Voice objects forming the canon.

    Examples
    --------
    >>> melody = Voice.from_patterns(pitches=[60,62,64,65,67], durations=[1]*5)
    >>> voices = canon(melody, num_voices=3, offsets_beats=[4.0, 8.0],
    ...               transpositions=[0, -12])
    # Three-voice canon: leader, follower at +4 beats, follower at +8 beats down an octave
    """
    ...
```

---

### `phase`

```python
def phase(
    pattern_voice: Voice,
    num_voices: int = 2,
    drift_rate: float = 0.01,
    drift_unit: str = "beats_per_repetition",
) -> list[Voice]:
    """
    Steve Reich-style phasing: multiple voices play the same pattern
    but one gradually drifts ahead, creating shifting alignments.

    In Reich's "Piano Phase" (1967), two pianists play the same
    12-note pattern. One gradually speeds up until they are one
    note apart, then two notes, etc. The interference pattern
    between the voices creates emergent melodies.

    Parameters
    ----------
    pattern_voice : Voice
        The repeating pattern (one cycle).
    num_voices : int
        Number of voices.
    drift_rate : float
        How fast the voices drift apart.
    drift_unit : str
        - "beats_per_repetition": each repetition, voice N is
          shifted by N * drift_rate beats from its nominal position
        - "ratio": voice N plays at tempo * (1 + N * drift_rate).
          E.g., drift_rate=phi-1 gives golden-ratio tempo offset.

    Returns
    -------
    list[Voice]
        Phased voices, each long enough to complete a full cycle
        of alignments.

    Examples
    --------
    >>> pattern = Voice.from_patterns(pitches=[60,64,67,64], durations=[0.5]*4)
    >>> voices = phase(pattern, num_voices=2, drift_rate=0.02)
    # Two voices: one at steady tempo, one gradually pulling ahead
    """
    ...
```

---

### `fractal_form`

```python
def fractal_form(
    voice: Voice,
    rule: str | Lindenmayer,
    depth: int = 3,
    section_transforms: dict[str, str] | None = None,
) -> list[Voice]:
    """
    Apply L-system formal development to a Voice.

    The voice is treated as the "axiom" material. The L-system rules
    determine how it is expanded, transformed, and recombined across
    a multi-section structure.

    Parameters
    ----------
    voice : Voice
        The seed material.
    rule : str | Lindenmayer
        Either a rule string like "A->ABA, B->BCB" (parsed into a
        Lindenmayer object) or an existing Lindenmayer instance.
    depth : int
        Number of L-system iterations.
    section_transforms : dict[str, str] | None
        Mapping from L-system symbols to Voice transformations.
        Default: {"A": "prime", "B": "inversion", "C": "retrograde"}.

    Returns
    -------
    list[Voice]
        One or more voices containing the developed material.

    Examples
    --------
    >>> seed = Voice.from_patterns(pitches=[60,62,64,65], durations=[1,1,1,1])
    >>> developed = fractal_form(seed, rule="A->ABA, B->BCB", depth=3)
    # A depth-3 expansion: ABAABABAABA... with inversions at B positions
    """
    ...
```

---

## Module: `sacred_composer.renderers`

### `to_midi`

```python
def to_midi(score: Score, path: str, **kwargs) -> None:
    """
    Write a Score to a MIDI file.

    Uses the midiutil library (already a dependency in the existing
    codebase).

    Parameters
    ----------
    score : Score
        The Score to render.
    path : str
        Output file path (.mid or .midi).
    **kwargs
        ticks_per_beat : int, default 480
        instruments : dict[str, int]
            Override GM program numbers per voice name.
            E.g., {"soprano": 0, "bass": 32}

    Notes
    -----
    This renderer maps Score -> PerformanceIR -> MIDI file,
    reusing the MIDI writing infrastructure from the existing
    composer.py pipeline where possible.
    """
    ...
```

---

### `to_lilypond`

```python
def to_lilypond(score: Score, path: str, **kwargs) -> None:
    """
    Write a Score to LilyPond notation format (.ly).

    LilyPond is a free music engraving program that produces
    publication-quality sheet music from text input.

    Parameters
    ----------
    score : Score
        The Score to render.
    path : str
        Output file path (.ly).
    **kwargs
        paper_size : str, default "a4"
        staff_size : int, default 20

    Notes
    -----
    Requires LilyPond installed separately to compile .ly to PDF.
    This renderer only writes the .ly source file.
    """
    ...
```

---

### `to_wav`

```python
def to_wav(score: Score, path: str, **kwargs) -> None:
    """
    Write a Score to a WAV audio file.

    Uses simple sine-wave synthesis or the existing render_audio.py
    infrastructure (FluidSynth with a SoundFont).

    Parameters
    ----------
    score : Score
        The Score to render.
    path : str
        Output file path (.wav).
    **kwargs
        method : str, default "fluidsynth"
            - "fluidsynth": use FluidSynth + SoundFont (best quality)
            - "sine": basic sine wave synthesis (no dependencies)
            - "additive": additive synthesis using harmonic series
              amplitudes (good for spectral compositions)
        soundfont : str | None
            Path to .sf2 SoundFont file (for fluidsynth method).
        sample_rate : int, default 44100
    """
    ...
```

---

## Module: `sacred_composer.shortcuts`

Convenience functions that wrap pattern creation with musical defaults. These are the "one-liner" interface shown in the usage examples.

```python
"""
Shortcut functions for common pattern-to-music operations.
These are imported by `from sacred_composer import *`.
"""

def fibonacci_form(total_bars: int, sections: int = 5) -> list[FormSection]:
    """
    Create a formal structure whose section lengths are consecutive
    Fibonacci numbers, scaled to fit total_bars.

    E.g., total_bars=34, sections=5 -> sections of 2, 3, 5, 8, 13, 3 bars
    (Fibonacci numbers scaled and adjusted to sum to 34).

    The climax section (longest) falls at approximately 0.618 of
    the total duration -- the golden ratio climax placement.
    """
    ...


def harmonic_series_pitches(
    fundamental: str = "C2",
    partials: int = 16,
) -> HarmonicSeries:
    """Shortcut: create a HarmonicSeries pattern from a pitch name."""
    ...


def golden_spiral_melody(
    seed: float = ...,  # defaults to phi
    scale: str = "minor",
    n: int = 64,
) -> GoldenSpiral:
    """Shortcut: create a GoldenSpiral configured for melodic use."""
    ...


def euclidean(onsets: int, pulses: int) -> EuclideanRhythm:
    """Shortcut: create a EuclideanRhythm pattern."""
    ...


def fractal(rule: str, depth: int = 3) -> Lindenmayer:
    """
    Shortcut: parse a rule string like "A->ABA, B->BCB" into a
    Lindenmayer system and expand to the given depth.
    """
    ...


def pink_noise_humanize(sigma_ms: float = 12.0) -> PinkNoise:
    """Shortcut: create PinkNoise configured for timing humanization."""
    ...


def spectral(
    fundamental: str = "A1",
    partials: int = 32,
    decay: str = "natural",
) -> HarmonicSeries:
    """Shortcut: create a HarmonicSeries for spectral composition."""
    ...


def digits_of_pi(n: int = 256) -> DigitsOf:
    """Shortcut: digits of pi."""
    ...


def phasing(ratio: float = ...) -> dict:
    """
    Configure Reich-style phasing with the given tempo ratio.
    Returns a configuration dict consumed by Composition.canon.

    Parameters
    ----------
    ratio : float
        Tempo ratio between voices. Use phi for golden-ratio phasing.
    """
    ...


def stern_brocot_rhythm(depth: int = 5) -> SternBrocot:
    """Shortcut: Stern-Brocot tree for rhythmic ratios."""
    ...


def cellular_automata_texture(
    rule: int = 110,
    voices: int = 4,
) -> CellularAutomata:
    """Shortcut: cellular automaton for multi-voice texture control."""
    ...
```

---

## Worked Examples

These examples demonstrate the intended API in full.

### Example 1: The Fibonacci Prelude

```python
from sacred_composer import *

piece = Composition(key="C", tempo=72, title="Fibonacci Prelude")

# Form: 34 bars divided by Fibonacci proportions (2+3+5+8+13+3)
piece.form = fibonacci_form(total_bars=34)

# Harmony: overtone series of C2, first 16 partials
# These become the available chord tones -- spectral harmony
piece.harmony = harmonic_series_pitches(fundamental="C2", partials=16)

# Melody: golden spiral angles mapped to C minor scale
# The 137.5-degree rotation ensures maximal pitch variety
piece.melody = golden_spiral_melody(seed=phi, scale="C_minor")

# Rhythm: Euclidean E(5,8) = Cuban cinquillo [10110110]
# One of the most universal rhythmic patterns across cultures
piece.rhythm = euclidean(onsets=5, pulses=8)

# Development: L-system A->ABA, B->BCB creates fractal form
# At depth 3: ABAABABAABAABAABABAABABAABAABAABA (self-similar)
piece.development = fractal(rule="A->ABA, B->BCB", depth=3)

# Humanize: 1/f noise on timing with 12ms standard deviation
# Matches the micro-timing variation of human performers
piece.humanize = pink_noise_humanize(sigma_ms=12)

piece.render("fibonacci_prelude.mid")
```

### Example 2: The Overtone Meditation

```python
from sacred_composer import *

piece = Composition(key="A", tempo=60, title="Overtone Meditation")

# Harmony: 32 partials of A1 with natural 1/n amplitude decay
# This is Grisey's technique: the piece IS the overtone spectrum
piece.harmony = spectral(fundamental="A1", partials=32, decay="natural")

# Melody: Norgard's infinity series -- fractal, self-similar,
# contains every integer exactly once
piece.melody = InfinitySeries(seed=0)

# Rhythm: Stern-Brocot tree enumerates all rational rhythmic ratios
# From simple (1:1, 1:2) to complex (3:5, 5:7) -- natural ordering
piece.rhythm = SternBrocot(depth=5)

# Texture: Rule 110 cellular automaton controls which of 4 voices
# are active at each time step. Rule 110 is Turing-complete --
# it produces complex, structured patterns from 8 simple rules.
piece.texture = cellular_automata_texture(rule=110, voices=4)

piece.render("overtone_meditation.mid")
```

### Example 3: The Phi Canon

```python
from sacred_composer import *

piece = Composition(tempo=108, title="Phi Canon")  # 108 = sacred number

# Melody: digits of pi mapped to C major scale degrees
# 3.14159265... -> scale degrees 3,1,4,1,5,9,2,6,5,...
# Pi is transcendental, so the melody never repeats.
piece.melody = DigitsOf("pi")

# Three voices in canon, each at golden-ratio tempo offset
# Voice 1: tempo 108
# Voice 2: tempo 108 * phi = ~174.7 (or offset by phi beats)
# Voice 3: tempo 108 * phi^2 = ~282.7
piece.voices = 3
piece.canon = phasing(ratio=phi)

piece.render("phi_canon.mid")
```

### Example 4: The Lorenz Butterfly

```python
from sacred_composer import *

piece = Composition(key="D", tempo=96, title="Lorenz Butterfly")

# The Lorenz attractor's three coordinates become three musical dimensions
lorenz = LorenzAttractor(sigma=10, rho=28, beta=8/3)

# x-coordinate -> pitch (chaotic but bounded, the "butterfly wings")
piece.melody = lorenz  # generate() returns x-values by default

# y-coordinate -> rhythm (via normalize to duration range)
# We need the y-values specifically:
y_values = [p[1] for p in lorenz.generate_xyz(512)]
piece.rhythm = to_rhythm(y_values, strategy="normalize", base_duration=0.5)

# z-coordinate -> dynamics (z is always positive, good for velocity)
z_values = [p[2] for p in lorenz.generate_xyz(512)]
piece.dynamics = to_dynamics(z_values, velocity_range=(30, 110))

# Humanize with logistic map at edge of chaos
piece.humanize = LogisticMap(r=3.57)  # onset of chaos

piece.render("lorenz_butterfly.mid")
```

### Example 5: The Rule 110 Fugue

```python
from sacred_composer import *

piece = Composition(key="G", tempo=88, title="Rule 110 Fugue")
piece.voices = 4

# Cellular automaton generates the entire contrapuntal texture
# 4 voices (columns), evolving over time (rows)
ca = CellularAutomata(rule=110, width=4)
grid = ca.generate_grid(128)  # 128 time steps

# Each column is a voice. On/off determines whether the voice
# sounds. When it sounds, pitch comes from a Fibonacci-interval
# melody seeded differently per voice.
for voice_idx in range(4):
    activations = [row[voice_idx] for row in grid]
    fib = FibonacciSequence()
    pitches = to_pitch(fib.generate(128), scale="G_minor",
                       octave_range=(3 + voice_idx, 4 + voice_idx))
    durations = to_rhythm(activations, strategy="binary", base_duration=0.5)
    piece.add_voice(Voice.from_patterns(
        pitches=pitches,
        durations=durations,
        name=f"voice_{voice_idx}",
    ))

piece.render("rule110_fugue.mid")
```

---

## Package Structure

```
sacred_composer/
    __init__.py          # exports everything via from sacred_composer import *
    constants.py         # phi, golden_angle, sacred_numbers
    patterns/
        __init__.py
        protocol.py      # Pattern protocol
        fibonacci.py     # FibonacciSequence
        golden_spiral.py # GoldenSpiral
        infinity.py      # InfinitySeries
        digits.py        # DigitsOf (with precomputed digit tables)
        harmonic.py      # HarmonicSeries
        cellular.py      # CellularAutomata
        lorenz.py        # LorenzAttractor
        euclidean.py     # EuclideanRhythm
        stern_brocot.py  # SternBrocot
        noise.py         # PinkNoise
        logistic.py      # LogisticMap
        lindenmayer.py   # Lindenmayer
    mappers/
        __init__.py
        pitch.py         # to_pitch
        rhythm.py        # to_rhythm
        dynamics.py      # to_dynamics
        form.py          # to_form, FormSection
    combiners/
        __init__.py
        layer.py         # layer
        canon.py         # canon
        phase.py         # phase
        fractal_form.py  # fractal_form
    core/
        __init__.py
        note.py          # Note
        voice.py         # Voice
        score.py         # Score
        composition.py   # Composition
    renderers/
        __init__.py
        midi.py          # to_midi
        lilypond.py      # to_lilypond
        wav.py           # to_wav
    shortcuts.py         # convenience functions
```

---

## Relationship to Existing Codebase

Sacred Composer does NOT replace the existing system. It is a parallel interface to the same musical output.

| Existing System (composer.py) | Sacred Composer |
|-------------------------------|-----------------|
| Prompt-driven: text -> music | Code-driven: patterns -> music |
| 9-pass compiler pipeline | Generate -> Map -> Combine -> Render |
| AI decides structure | Programmer decides structure |
| Galant schemata vocabulary | Mathematical pattern vocabulary |
| Random seed motif generation | Deterministic pattern generation |
| PerformanceIR -> MIDI | Score -> PerformanceIR -> MIDI (reuses renderer) |

Bridge points:
- `Score.to_performance_ir()` converts Sacred Composer's Score to the existing PerformanceIR, allowing reuse of the humanization and MIDI rendering passes.
- Sacred Composer's `to_pitch()` with `scale` parameter uses the same key/scale infrastructure as the existing system.
- The `PinkNoise` humanizer serves the same role as the existing humanization pass (Pass 8 in composer.py) but uses a 1/f spectral model rather than uniform random offsets.

---

## Dependencies

Required (already in the existing project):
- `numpy` -- numerical computation for pattern generators
- `midiutil` -- MIDI file writing
- `music21` -- pitch/scale/interval utilities

New (optional):
- `mpmath` -- arbitrary precision digits of pi, e, phi (for DigitsOf)
- `scipy` -- signal processing for pink noise generation

No AI/ML dependencies. No API calls. No prompts. Pure mathematics.

---

## Design Principles (Summary)

1. **Every note has a reason.** Traceable to a named pattern and its parameters.
2. **Patterns are composable.** Any pattern can feed any mapper. Any mapper output can feed any combiner.
3. **The code reads like a score.** A `Composition` script should be readable as a description of what the piece IS, not how to build it.
4. **Deterministic by default.** Same code, same output. Always. Chaos is opt-in (Lorenz, logistic map), not opt-out.
5. **Compatible with the existing system.** Sacred Composer outputs can flow into the existing pipeline for humanization, rendering, and evaluation.

---

---

## PART II: THE CONTEXT — Why These Patterns, Why This Approach

### The Problem with AI Music Generation

Current AI music tools (Suno, Udio, MusicGen, even our own prompt-driven composer.py) share a fundamental flaw: they generate music FROM data — statistical patterns learned from existing compositions. The output is recombination. Sophisticated recombination, but recombination. The music doesn't come FROM anywhere meaningful. It comes from a training set.

Sacred Composer inverts this. The music comes from the same patterns that create galaxies, snowflakes, and DNA. Not metaphorically — mathematically. The Fibonacci sequence that determines our section lengths is the same sequence that governs sunflower seeds. The harmonic series that determines our chords is the same series that governs every vibrating string in the universe. The 1/f noise that determines our rubato is the same noise that governs healthy heartbeats.

This is not "nature-inspired" in the vague sense. It is nature-DERIVED. The patterns are not analogies. They are the same mathematics.

### Why Each Pattern Was Chosen

Every pattern in the system was selected based on two criteria:
1. **It has proven musical applications** (documented in composers' practice or research)
2. **It maps naturally to a specific musical parameter** (not arbitrary assignment)

| Pattern | Musical Parameter | Why This Mapping Works | Evidence |
|---------|------------------|----------------------|----------|
| **Fibonacci** | Form proportions | φ creates maximum asymmetry within order (most irrational number) | Bartók's M.f.S.P.&C., KB Part 2 |
| **Harmonic Series** | Harmony/Chords | Overtones ARE consonance — physics, not convention | Grisey's Partiels, KB Part 36 |
| **Infinity Series** | Melody | Self-similar at every scale = organic, never-repeating, always coherent | Nørgård's Symphony No. 2 |
| **Golden Spiral** | Melodic intervals | 137.5° maximizes pitch-space coverage (phyllotaxis principle) | KB Part 40, biomimicry research |
| **Cellular Automata** | Texture/Polyphony | Edge-of-chaos rules produce neither random nor periodic patterns | Wolfram, Burraston research |
| **Euclidean Rhythm** | Rhythm | Bjorklund algorithm = maximally even distribution = world music rhythms | Toussaint, KB Part 4 |
| **1/f Pink Noise** | Rubato/Timing | Matches healthy heartbeat variability — between metronomic and random | Voss & Clarke, KB Part 40 |
| **Lorenz Attractor** | Melody contour | Deterministic chaos: never repeats, always bounded, two-lobe = two "key areas" | KB Part 12 |
| **L-systems** | Form/Development | Branching self-similarity = motivic development at multiple scales | KB Part 12, Tom Johnson |
| **Stern-Brocot** | Metric modulation | Enumerates ALL rational rhythmic ratios in order of complexity | Toussaint, KB Part 37 |
| **Digits of π/e/φ** | Secondary patterns | Non-repeating, statistically uniform — subtle background variation | Supplementary material |
| **Logistic Map** | Tension curve | Period-doubling route to chaos = gradual dissolution of order | KB Part 12 |

### The Creative Workflow

The composer (the human) works like this:

1. **Choose a fundamental** — the generative seed. This could be a frequency (A=55Hz), a mathematical constant (φ), or a natural structure (the harmonic series of a cello's C2).

2. **Choose patterns for each parameter**:
   - What generates the pitches? (Harmonic series? Infinity series? Golden spiral?)
   - What generates the rhythm? (Euclidean? Fibonacci? Stern-Brocot?)
   - What generates the form? (Fibonacci proportions? L-system? Golden section?)
   - What generates the dynamics? (Logistic map tension curve? 1/f noise?)

3. **Configure the mappers** — how the raw pattern values become musical values:
   - Which scale? (C minor? A Pythagorean? A spectral scale from the overtone series?)
   - Which register? (Octave 3-5? Full piano range?)
   - What base duration? (Quarter note? Eighth note?)

4. **Layer and combine** — multiple patterns become polyphony:
   - Canon: the same pattern at different time offsets
   - Phase: the same pattern at slightly different rates (Reich)
   - Layer: different patterns for different voices

5. **Render** — deterministic output:
   - MIDI for playback
   - LilyPond for notation
   - WAV for listening

The key insight: **steps 1-4 ARE the composition**. The creative decisions are: which patterns, which mappings, which combinations. The code that expresses these decisions IS the score. There is nothing else.

### Connection to the Knowledge Base (41 Parts)

The Sacred Composer doesn't discard the 41-part knowledge base. It uses it as the THEORY LAYER — the understanding of WHY certain patterns produce good music:

| KB Part | How Sacred Composer Uses It |
|---------|---------------------------|
| Part 2 (Math Foundations) | Fibonacci, golden ratio, fractals → Pattern generators |
| Part 3 (Counterpoint) | Voice-leading rules → Validation in the Combiner stage |
| Part 4 (Melody/Rhythm) | Interval statistics, Euclidean rhythms → Mapper calibration |
| Part 10 (Neuroscience) | 75/25 surprise ratio, chills triggers → Composition principles |
| Part 12 (Unconventional) | Cellular automata, chaos, L-systems → Pattern generators |
| Part 19 (Tuning) | Just intonation, harmonic series → HarmonicSeries generator |
| Part 24 (Galant Schemata) | Voice-leading patterns → Optional schema overlay |
| Part 31 (Performance) | KTH rules, rubato → Humanization via PinkNoise |
| Part 33 (Masterwork Analysis) | Constraint of means → Design philosophy |
| Part 34 (50 Rules) | Hard constraints → Validation pass |
| Part 35 (Taste) | Economy, inevitability → Guiding principles |
| Part 40 (Nature Patterns) | All 9 creation patterns → System architecture |

### What Makes This Different from Existing Tools

| Tool | Approach | Limitation |
|------|----------|-----------|
| Suno/Udio | Audio generation from text prompt | Black box, no structure, no traceability |
| MuseNet/AIVA | Neural net on MIDI corpus | Recombination of learned patterns |
| Our composer.py | Schema-based prompt compiler | Still prompt-driven, AI decides details |
| SuperCollider | General-purpose synthesis | No composition framework, just audio engine |
| TidalCycles | Pattern-based live coding | Real-time focused, no classical form |
| **Sacred Composer** | **Pattern → Music deterministically** | **Every note traceable, code = score** |

### Implementation Roadmap

**Phase 1: Core Engine** (must-have)
- Pattern protocol + 6 essential generators: Fibonacci, HarmonicSeries, InfinitySeries, EuclideanRhythm, CellularAutomata, PinkNoise
- 4 mappers: to_pitch, to_rhythm, to_dynamics, to_form
- Core data model: Note, Voice, Score
- MIDI renderer (reuse existing midiutil infrastructure)
- 3 working example compositions

**Phase 2: Extended Patterns** (should-have)
- GoldenSpiral, LorenzAttractor, DigitsOf, SternBrocot, LogisticMap, Lindenmayer
- Combiners: layer, canon, phase
- LilyPond renderer (notation output)
- Bridge to existing PerformanceIR (for humanization reuse)
- 5 more example compositions

**Phase 3: Refinement** (nice-to-have)
- fractal_form combiner (L-system development)
- WAV renderer (direct synthesis, no external dependencies)
- Microtonal support (fractional MIDI, pitch bend)
- Interactive mode (live-code a composition, hear changes in real time)
- Evaluation integration (run 50 Rules on output)

### The Aesthetic Ranking — What Actually Sounds Good

From the deep research (agents tested all approaches with actual implementations):

1. **Harmonic series** (9/10) — Physically grounded, perceptually coherent. Grisey proved this works.
2. **Fibonacci as proportions** (8/10) — Organic asymmetry for form and timing. NOT for raw pitch material.
3. **Infinity series** (8/10) — Self-similar melody that never repeats. Nørgård proved this works.
4. **1/f noise for timing** (8/10) — Matches biological rhythms. Indistinguishable from human rubato.
5. **Euclidean rhythms** (7/10) — World music patterns from pure math. Always groove.
6. **Fractals/L-systems for form** (7/10) — Self-similarity at multiple scales gives coherence.
7. **Cellular automata** (6/10) — Edge-of-chaos textures. Best for ambient/textural passages.
8. **Lorenz/chaos** (5/10) — Interesting but hard to control. Best as secondary parameter.
9. **Platonic solid walks** (5/10) — Constrained harmonic vocabularies, but adjacency walks sound random.
10. **Digit mapping (π, e, φ)** (4/10) — Naively, digits are pseudo-random. Structural properties (continued fractions) are better.
11. **DNA sonification** (3/10) — Essentially arbitrary without heavy compositional intervention.

**The rule: use patterns that map NATURALLY to their musical parameter.** The harmonic series → harmony is a natural mapping (physics). π digits → melody is an arbitrary mapping (any permutation would work equally well). Natural mappings produce better music.

### Example: A Complete Composition Walkthrough

**"Overtone Cathedral" — a 3-minute meditation built entirely from one cello note**

```python
from sacred_composer import *

# The fundamental: a cello's open C string
fundamental = HarmonicSeries("C2", decay="natural")

# HARMONY: the first 16 overtones of C2, slowly unfolding
# Partials enter one by one over 30 seconds, building from
# a single low C to a shimmering 16-note spectral chord
harmony = fundamental.as_chord(n=16, quantize=False)

# MELODY: Nørgård's infinity series mapped to the overtone pitches
# (not 12-TET scale degrees — the ACTUAL partial frequencies)
melody_pattern = InfinitySeries(seed=0)
melody = to_pitch(
    melody_pattern.generate(128),
    pitch_set=harmony,           # use overtone pitches as the "scale"
    strategy="nearest"           # snap to nearest overtone
)

# RHYTHM: Euclidean pattern E(5,8) — the Cuban cinquillo
# Applied at the 1/f level — not metronomic but with pink-noise variation
rhythm = to_rhythm(
    EuclideanRhythm(5, 8).generate(128),
    base_duration=0.5,
    humanize=PinkNoise(sigma_ms=15)
)

# FORM: Fibonacci proportions
# Sections of 1, 1, 2, 3, 5, 8, 13 bars
# Each section adds more overtones to the harmony
form = to_form(
    FibonacciSequence().generate(7),
    total_bars=34                # 34 = Fibonacci number
)

# DYNAMICS: logistic map from order to edge-of-chaos
# r increases from 2.5 (stable) to 3.57 (onset of chaos)
# = piece grows from calm certainty to trembling complexity
dynamics = to_dynamics(
    LogisticMap(r_start=2.5, r_end=3.57).generate(128),
    range=(40, 100)              # pp to f
)

# ASSEMBLE
piece = Composition(tempo=54)    # 54 BPM — deep, meditative
piece.add_voice("cello_harmonics", melody, rhythm, dynamics)
piece.add_voice("cello_drone", 
    to_pitch([0], pitch_set=[harmony[0]]),  # fundamental only
    to_rhythm([1], base_duration=34*4),      # one note, entire piece
    to_dynamics([0.6])                       # mp, steady
)
piece.form = form

# The piece IS these choices. Nothing else.
piece.render("overtone_cathedral.mid")
piece.render("overtone_cathedral.ly")   # LilyPond notation
```

**What this produces**: A piece that begins with a single low C, gradually adds overtones from the harmonic series (each arriving at a Fibonacci-determined moment), has a melody that traces the infinity series through the overtone pitches (self-similar, never repeating), pulses in a Cuban cinquillo rhythm with heartbeat-like timing variation, and grows dynamically from stability to the edge of chaos — like a cathedral being built from a single stone.

Every note is traceable. The melody at bar 13, beat 3 is infinity_series[47] mapped to the nearest overtone of C2 with a pink-noise timing offset of +8ms. There is no mystery, no black box, no "the AI decided." The code decided. The pattern decided. Nature decided.

---

*This specification is the architectural blueprint. Implementation follows.*
