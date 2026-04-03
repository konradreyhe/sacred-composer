"""Pattern generators — the source material for Sacred Composer.

Every generator implements the Pattern protocol: generate(n) -> list[float],
__iter__ -> Iterator[float], name -> str. Raw numeric values, no musical meaning.
"""

from __future__ import annotations

import math
import random
from typing import Iterator

from sacred_composer.constants import phi


class FibonacciSequence:
    """The Fibonacci sequence: each number is the sum of the two preceding.

    1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, ...

    The ratio of consecutive terms converges to phi (1.618...).
    Used for: form proportions, rhythmic groupings, interval selection.
    """

    def __init__(self, a: int = 1, b: int = 1) -> None:
        self._a = a
        self._b = b

    @property
    def name(self) -> str:
        return "fibonacci"

    def generate(self, n: int) -> list[float]:
        result = []
        a, b = self._a, self._b
        for _ in range(n):
            # Cap large Fibonacci values to prevent float overflow
            if a > 1e15:
                a, b = self._a, self._b  # wrap around
            result.append(float(a))
            a, b = b, a + b
        return result

    def __iter__(self) -> Iterator[float]:
        a, b = self._a, self._b
        while True:
            yield float(a)
            a, b = b, a + b


class HarmonicSeries:
    """The overtone series of a fundamental frequency.

    Given a fundamental (e.g. C2 = 65.41 Hz), the partials are:
    f, 2f, 3f, 4f, 5f, ... — the physical basis of consonance.

    Parameters
    ----------
    fundamental : str or float
        Note name like "C2" or frequency in Hz.
    n_partials : int
        Number of partials to generate.
    decay : str
        "natural" = 1/n amplitude decay, "equal" = flat.
    """

    def __init__(
        self,
        fundamental: str | float = "C2",
        n_partials: int = 32,
        decay: str = "natural",
    ) -> None:
        if isinstance(fundamental, str):
            self._freq = self._note_to_freq(fundamental)
        else:
            self._freq = fundamental
        self._n_partials = n_partials
        self._decay = decay

    @staticmethod
    def _note_to_freq(note: str) -> float:
        from sacred_composer.constants import NOTE_NAMES
        name = note[:-1]
        octave = int(note[-1])
        midi = NOTE_NAMES[name] + (octave + 1) * 12
        return 440.0 * (2 ** ((midi - 69) / 12))

    @property
    def name(self) -> str:
        return f"harmonic_series({self._freq:.1f}Hz)"

    def generate(self, n: int) -> list[float]:
        """Return frequencies of the first n partials."""
        return [self._freq * (i + 1) for i in range(n)]

    def as_midi(self, n: int = 16, quantize: bool = True) -> list[float]:
        """Return partials as MIDI note numbers."""
        freqs = self.generate(n)
        midis = []
        for f in freqs:
            if f <= 0:
                continue
            midi = 69 + 12 * math.log2(f / 440.0)
            if quantize:
                midi = round(midi)
            midis.append(midi)
        return midis

    def as_chord(self, n: int = 8, quantize: bool = True) -> list[int]:
        """Return the first n partials as MIDI note numbers."""
        return [int(m) for m in self.as_midi(n, quantize)]

    def amplitudes(self, n: int) -> list[float]:
        """Return amplitude weights for n partials."""
        if self._decay == "natural":
            return [1.0 / (i + 1) for i in range(n)]
        return [1.0] * n

    def __iter__(self) -> Iterator[float]:
        i = 1
        while True:
            yield self._freq * i
            i += 1


class InfinitySeries:
    """Norgard's infinity series — a self-similar integer sequence.

    Defined recursively:
        a(0) = seed
        a(2n) = -a(n)
        a(2n+1) = a(n) + 1

    Every subsequence at every scale is a transposition/inversion of the whole.
    Used for: melody generation (self-similar, never-repeating, always coherent).
    """

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed

    @property
    def name(self) -> str:
        return "infinity_series"

    def generate(self, n: int) -> list[float]:
        if n == 0:
            return []
        seq = [0] * n
        seq[0] = self._seed
        for i in range(1, n):
            if i % 2 == 0:
                seq[i] = -seq[i // 2]
            else:
                seq[i] = seq[i // 2] + 1
        return [float(x) for x in seq]

    def __iter__(self) -> Iterator[float]:
        cache = [self._seed]
        yield float(self._seed)
        i = 1
        while True:
            if i % 2 == 0:
                val = -cache[i // 2]
            else:
                val = cache[i // 2] + 1
            cache.append(val)
            yield float(val)
            i += 1


class EuclideanRhythm:
    """Bjorklund's algorithm: distribute k onsets evenly across n pulses.

    E(3,8) = [1,0,0,1,0,0,1,0] — Cuban tresillo
    E(5,8) = [1,0,1,1,0,1,1,0] — Cuban cinquillo
    E(7,12) = [1,0,1,1,0,1,0,1,1,0,1,0] — West African bell

    Used for: rhythmic patterns that always groove.
    """

    def __init__(self, onsets: int, pulses: int, rotation: int = 0) -> None:
        self._onsets = onsets
        self._pulses = pulses
        self._rotation = rotation
        self._pattern = self._compute()

    def _compute(self) -> list[int]:
        """Bjorklund's algorithm."""
        if self._onsets >= self._pulses:
            return [1] * self._pulses
        if self._onsets == 0:
            return [0] * self._pulses

        groups: list[list[int]] = [[1]] * self._onsets + [[0]] * (self._pulses - self._onsets)

        while True:
            remainder = len(groups) - len(groups) // 2 * 2  # just for clarity
            # Split into two halves: the larger group and the remainder
            n_large = min(
                len([g for g in groups if g == groups[0]]),
                len([g for g in groups if g != groups[0]]),
            )
            if n_large <= 1:
                break

            # More standard Bjorklund: distribute remainder into front
            front = groups[:n_large]
            back = groups[n_large:]
            if not back:
                break

            new_groups = []
            for i in range(min(len(front), len(back))):
                new_groups.append(front[i] + back[i])
            # Leftovers
            remaining_front = front[min(len(front), len(back)):]
            remaining_back = back[min(len(front), len(back)):]
            new_groups.extend(remaining_front)
            new_groups.extend(remaining_back)

            if len(new_groups) == len(groups):
                break
            groups = new_groups

        pattern = []
        for g in groups:
            pattern.extend(g)

        # Apply rotation
        if self._rotation:
            r = self._rotation % len(pattern)
            pattern = pattern[r:] + pattern[:r]

        return pattern

    @property
    def name(self) -> str:
        return f"euclidean({self._onsets},{self._pulses})"

    @property
    def pattern(self) -> list[int]:
        return list(self._pattern)

    def generate(self, n: int) -> list[float]:
        """Return n pulses, cycling the pattern as needed."""
        result = []
        for i in range(n):
            result.append(float(self._pattern[i % len(self._pattern)]))
        return result

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield float(self._pattern[i % len(self._pattern)])
            i += 1


class CellularAutomata:
    """Elementary cellular automata (Wolfram).

    A 1D row of cells evolves according to a rule number (0-255).
    Rule 30: chaotic. Rule 90: Sierpinski. Rule 110: complex/Turing-complete.

    Used for: texture, polyphony, edge-of-chaos patterns.
    """

    def __init__(
        self,
        rule: int = 110,
        width: int = 16,
        initial_state: list[int] | None = None,
    ) -> None:
        self._rule = rule
        self._width = width
        if initial_state is not None:
            self._state = list(initial_state)
        else:
            self._state = [0] * width
            self._state[width // 2] = 1

    @property
    def name(self) -> str:
        return f"cellular_automata(rule={self._rule})"

    def _step(self, state: list[int]) -> list[int]:
        """Compute next generation."""
        n = len(state)
        new = [0] * n
        for i in range(n):
            left = state[(i - 1) % n]
            center = state[i]
            right = state[(i + 1) % n]
            neighborhood = (left << 2) | (center << 1) | right
            new[i] = (self._rule >> neighborhood) & 1
        return new

    def generate_grid(self, steps: int) -> list[list[int]]:
        """Return steps rows of width cells."""
        grid = []
        state = list(self._state)
        for _ in range(steps):
            grid.append(list(state))
            state = self._step(state)
        return grid

    def generate(self, n: int) -> list[float]:
        """Return n values (flattened grid)."""
        steps = (n + self._width - 1) // self._width
        grid = self.generate_grid(steps)
        flat = []
        for row in grid:
            flat.extend(row)
        return [float(x) for x in flat[:n]]

    def __iter__(self) -> Iterator[float]:
        state = list(self._state)
        while True:
            for cell in state:
                yield float(cell)
            state = self._step(state)


class PinkNoise:
    """1/f pink noise generator using Voss-McCartney algorithm.

    Pink noise has equal energy per octave — it matches the spectral
    characteristics of natural phenomena (heartbeats, ocean waves,
    neural firing). Used for: humanization, rubato, dynamic fluctuation.
    """

    def __init__(self, sigma: float = 1.0, seed: int | None = None) -> None:
        self._sigma = sigma
        self._rng = random.Random(seed)

    @property
    def name(self) -> str:
        return f"pink_noise(sigma={self._sigma})"

    def generate(self, n: int) -> list[float]:
        """Voss-McCartney algorithm for 1/f noise."""
        # Number of octave layers
        n_layers = max(1, int(math.log2(max(n, 2))))
        layers = [0.0] * n_layers
        result = []

        for i in range(n):
            # Update one layer per step based on binary counter
            for j in range(n_layers):
                if i % (1 << j) == 0:
                    layers[j] = self._rng.gauss(0, self._sigma)
                    break  # Only update the lowest-period layer that triggers

            result.append(sum(layers) / n_layers)

        return result

    def __iter__(self) -> Iterator[float]:
        n_layers = 16
        layers = [0.0] * n_layers
        i = 0
        while True:
            for j in range(n_layers):
                if i % (1 << j) == 0:
                    layers[j] = self._rng.gauss(0, self._sigma)
                    break
            yield sum(layers) / n_layers
            i += 1


# ──────────────────────────────────────────────────────────
# Phase 2: Extended Pattern Generators
# ──────────────────────────────────────────────────────────


class GoldenSpiral:
    """Golden angle sequence — successive points at 137.5077... degrees.

    In phyllotaxis, this angle maximizes coverage of a disk (sunflower
    seed packing). When mapped to pitch, it maximizes coverage of
    pitch space — no clustering, no gaps.

    Used for: melodic intervals, pitch distribution.
    """

    def __init__(self, start: float = 0.0) -> None:
        from sacred_composer.constants import golden_angle
        self._angle = golden_angle
        self._start = start

    @property
    def name(self) -> str:
        return "golden_spiral"

    def generate(self, n: int) -> list[float]:
        """Return n successive golden-angle values (in degrees, mod 360)."""
        return [(self._start + i * self._angle) % 360.0 for i in range(n)]

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield (self._start + i * self._angle) % 360.0
            i += 1


class LorenzAttractor:
    """The Lorenz system — deterministic chaos with butterfly-wing shape.

    Three coupled ODEs producing trajectories that never repeat but
    stay bounded within two lobes. The two lobes can map to two
    tonal areas — structured chaos.

    Used for: melody contour (x), rhythm variation (y), dynamics (z).
    """

    def __init__(
        self,
        sigma: float = 10.0,
        rho: float = 28.0,
        beta: float = 8 / 3,
        dt: float = 0.01,
        initial: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        self._sigma = sigma
        self._rho = rho
        self._beta = beta
        self._dt = dt
        self._initial = initial

    @property
    def name(self) -> str:
        return "lorenz_attractor"

    def generate_xyz(self, n: int) -> list[tuple[float, float, float]]:
        """Return list of (x, y, z) tuples."""
        x, y, z = self._initial
        result = []
        for _ in range(n):
            result.append((x, y, z))
            dx = self._sigma * (y - x) * self._dt
            dy = (x * (self._rho - z) - y) * self._dt
            dz = (x * y - self._beta * z) * self._dt
            x += dx
            y += dy
            z += dz
        return result

    def generate(self, n: int) -> list[float]:
        """Return n x-coordinate values."""
        return [p[0] for p in self.generate_xyz(n)]

    def __iter__(self) -> Iterator[float]:
        x, y, z = self._initial
        while True:
            yield x
            dx = self._sigma * (y - x) * self._dt
            dy = (x * (self._rho - z) - y) * self._dt
            dz = (x * y - self._beta * z) * self._dt
            x += dx
            y += dy
            z += dz


class DigitsOf:
    """Digits of a mathematical constant (pi, e, phi, sqrt2).

    Non-repeating, statistically uniform sequences. Each digit (0-9)
    becomes a value. Not the strongest melodic source on its own,
    but useful as a secondary pattern for subtle variation.

    Used for: background variation, secondary parameters.
    """

    # Pre-computed first 200 digits (after decimal point)
    _DIGITS = {
        "pi": "14159265358979323846264338327950288419716939937510"
              "58209749445923078164062862089986280348253421170679"
              "82148086513282306647093844609550582231725359408128"
              "48111745028410270193852110555964462294895493038196",
        "e":  "71828182845904523536028747135266249775724709369995"
              "95749669676277240766303535475945713821785251664274"
              "27466391932003059921817413596629043572900334295260"
              "59563073813232862794349076323382988075319525101901",
        "phi": "6180339887498948482045868343656381177203091798057"
               "62862135448622705260462818902449707207204189391137"
               "48475408807538689175212663386222353693179318006076"
               "67263544333890865959395829056383226613199282902678",
    }

    def __init__(self, constant: str = "pi") -> None:
        self._constant = constant
        self._digits_str = self._DIGITS.get(constant, self._DIGITS["pi"])

    @property
    def name(self) -> str:
        return f"digits_of({self._constant})"

    def generate(self, n: int) -> list[float]:
        """Return n digit values (0-9)."""
        result = []
        for i in range(n):
            idx = i % len(self._digits_str)
            result.append(float(self._digits_str[idx]))
        return result

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            idx = i % len(self._digits_str)
            yield float(self._digits_str[idx])
            i += 1


class SternBrocot:
    """The Stern-Brocot tree — every positive rational number exactly once.

    Enumerates all rhythmic ratios in order of complexity:
    1:1, 1:2, 2:1, 1:3, 2:3, 3:2, 3:1, ...

    Used for: metric modulation, rhythmic ratios, tempo relationships.
    """

    def __init__(self, depth: int = 4) -> None:
        self._depth = depth
        self._fractions = self._build()

    def _build(self) -> list[tuple[int, int]]:
        """Build Stern-Brocot tree level by level."""
        # Start with boundaries
        fracs = [(1, 1)]  # Level 1
        queue = [((0, 1), (1, 1)), ((1, 1), (1, 0))]

        for _ in range(self._depth - 1):
            next_queue = []
            new_fracs = []
            for (a, b), (c, d) in queue:
                mediant = (a + c, b + d)
                new_fracs.append(mediant)
                next_queue.append(((a, b), mediant))
                next_queue.append((mediant, (c, d)))
            fracs.extend(new_fracs)
            queue = next_queue

        return fracs

    @property
    def name(self) -> str:
        return f"stern_brocot(depth={self._depth})"

    def as_fractions(self, n: int) -> list[tuple[int, int]]:
        """Return (numerator, denominator) pairs."""
        result = []
        for i in range(n):
            result.append(self._fractions[i % len(self._fractions)])
        return result

    def generate(self, n: int) -> list[float]:
        """Return fractions as floats."""
        return [a / b for a, b in self.as_fractions(n)]

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            a, b = self._fractions[i % len(self._fractions)]
            yield a / b
            i += 1


class LogisticMap:
    """The logistic map: x(n+1) = r * x(n) * (1 - x(n)).

    Route from order to chaos as r increases:
    r < 3.0: fixed point. r ~ 3.45: period doubling. r > 3.57: chaos.

    Can sweep r from r_start to r_end over n steps for a tension curve.

    Used for: tension/release arcs, dynamic curves.
    """

    def __init__(
        self,
        r: float = 3.99,
        x0: float = 0.5,
        r_start: float | None = None,
        r_end: float | None = None,
    ) -> None:
        self._r = r
        self._x0 = x0
        self._r_start = r_start
        self._r_end = r_end

    @property
    def name(self) -> str:
        if self._r_start is not None:
            return f"logistic_map(r={self._r_start}->{self._r_end})"
        return f"logistic_map(r={self._r})"

    def generate(self, n: int) -> list[float]:
        x = self._x0
        result = []
        for i in range(n):
            if self._r_start is not None and self._r_end is not None:
                r = self._r_start + (self._r_end - self._r_start) * i / max(1, n - 1)
            else:
                r = self._r
            result.append(x)
            x = r * x * (1 - x)
        return result

    def __iter__(self) -> Iterator[float]:
        x = self._x0
        while True:
            yield x
            x = self._r * x * (1 - x)


class Lindenmayer:
    """L-system (Lindenmayer system) — parallel string-rewriting grammar.

    Produces fractal, self-similar structures. In music: motivic
    development at multiple scales.

    Example: axiom="A", rules={"A": "AB", "B": "A"} produces the
    Fibonacci word: A, AB, ABA, ABAAB, ABAABABA, ...

    Used for: formal structure, melodic development, fractal form.
    """

    def __init__(
        self,
        axiom: str = "A",
        rules: dict[str, str] | None = None,
        alphabet_values: dict[str, float] | None = None,
    ) -> None:
        self._axiom = axiom
        self._rules = rules or {"A": "AB", "B": "A"}
        self._alphabet_values = alphabet_values
        self._current = axiom
        self._depth = 0

    @property
    def name(self) -> str:
        return f"lindenmayer(depth={self._depth})"

    @property
    def depth(self) -> int:
        return self._depth

    def expand(self, depth: int) -> str:
        """Apply rules depth times and return the resulting string."""
        s = self._axiom
        for _ in range(depth):
            s = "".join(self._rules.get(c, c) for c in s)
        self._current = s
        self._depth = depth
        return s

    def generate(self, n: int) -> list[float]:
        """Return numeric values for the first n characters of the expansion.

        Auto-expands until the string is at least n characters long.
        """
        # Expand until we have enough characters
        s = self._current
        d = self._depth
        while len(s) < n:
            d += 1
            s = self.expand(d)

        values = []
        for i in range(n):
            c = s[i]
            if self._alphabet_values and c in self._alphabet_values:
                values.append(self._alphabet_values[c])
            else:
                # Default: map character to ordinal position (A=0, B=1, ...)
                values.append(float(ord(c) - ord('A')))
        return values

    def __iter__(self) -> Iterator[float]:
        # Expand progressively
        d = 0
        pos = 0
        s = self._axiom
        while True:
            if pos >= len(s):
                d += 1
                s = self.expand(d)
            c = s[pos]
            if self._alphabet_values and c in self._alphabet_values:
                yield self._alphabet_values[c]
            else:
                yield float(ord(c) - ord('A'))
            pos += 1


# ──────────────────────────────────────────────────────────
# Phase 3: Extended Pattern Generators
# ──────────────────────────────────────────────────────────


class MandelbrotBoundary:
    """Walk along the Mandelbrot set boundary, recording escape-time counts.

    Parametrizes the main cardioid boundary and perturbs slightly outward
    to sample the rich fractal structure at the edge. Produces non-repeating
    but locally coherent sequences.

    Used for: melody contour with fractal detail, texture variation.
    """

    def __init__(self, max_iter: int = 100, perturbation: float = 0.02) -> None:
        self._max_iter = max_iter
        self._perturb = perturbation

    @property
    def name(self) -> str:
        return "mandelbrot_boundary"

    def _escape_count(self, c: complex) -> int:
        z, count = complex(0, 0), 0
        while abs(z) < 2 and count < self._max_iter:
            z = z * z + c
            count += 1
        return count

    def generate(self, n: int) -> list[float]:
        values = []
        for i in range(n):
            theta = 2 * math.pi * i / max(n, 1)
            # Cardioid parametrization
            c_real = 0.5 * math.cos(theta) - 0.25 * math.cos(2 * theta)
            c_imag = 0.5 * math.sin(theta) - 0.25 * math.sin(2 * theta)
            # Perturb outward for interesting iteration counts
            c_real += self._perturb * math.cos(theta * 7)
            c_imag += self._perturb * math.sin(theta * 7)
            values.append(float(self._escape_count(complex(c_real, c_imag))))
        return values

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            theta = 2 * math.pi * i / 1000
            c_real = 0.5 * math.cos(theta) - 0.25 * math.cos(2 * theta)
            c_imag = 0.5 * math.sin(theta) - 0.25 * math.sin(2 * theta)
            c_real += self._perturb * math.cos(theta * 7)
            c_imag += self._perturb * math.sin(theta * 7)
            yield float(self._escape_count(complex(c_real, c_imag)))
            i += 1


class RosslerAttractor:
    """The Rossler system — simpler than Lorenz, single-lobe spiral with excursions.

    Three coupled ODEs:
        dx/dt = -y - z
        dy/dt = x + a*y
        dz/dt = b + z*(x - c)

    The x-y plane shows a simple spiral that occasionally kicks out
    into a large excursion (controlled by c). Good for melody contour
    with mostly stepwise motion and occasional leaps.

    Used for: melody contour, phrasing arcs.
    """

    def __init__(
        self,
        a: float = 0.2,
        b: float = 0.2,
        c: float = 5.7,
        dt: float = 0.05,
        initial: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        self._a = a
        self._b = b
        self._c = c
        self._dt = dt
        self._initial = initial

    @property
    def name(self) -> str:
        return "rossler_attractor"

    def generate_xyz(self, n: int) -> list[tuple[float, float, float]]:
        """Return list of (x, y, z) tuples."""
        x, y, z = self._initial
        result = []
        for _ in range(n):
            result.append((x, y, z))
            dx = (-y - z) * self._dt
            dy = (x + self._a * y) * self._dt
            dz = (self._b + z * (x - self._c)) * self._dt
            x += dx
            y += dy
            z += dz
        return result

    def generate(self, n: int) -> list[float]:
        """Return n x-coordinate values."""
        return [p[0] for p in self.generate_xyz(n)]

    def __iter__(self) -> Iterator[float]:
        x, y, z = self._initial
        while True:
            yield x
            dx = (-y - z) * self._dt
            dy = (x + self._a * y) * self._dt
            dz = (self._b + z * (x - self._c)) * self._dt
            x += dx
            y += dy
            z += dz


class CantorSet:
    """Recursive middle-third removal — the Cantor set as a rhythm pattern.

    Start with all ones, recursively replace the middle third with zeros:
        depth=1: [1, 0, 1]
        depth=2: [1, 0, 1, 0, 0, 0, 1, 0, 1]
        depth=3: 27 elements, etc.

    Produces fractal silence at multiple scales — silence is as structured
    as sound.

    Used for: rhythmic patterns with self-similar rests.
    """

    def __init__(self, depth: int = 5) -> None:
        self._depth = depth
        self._pattern = self._build()

    def _build(self) -> list[int]:
        """Build the Cantor set pattern at the given depth."""
        pattern = [1]
        for _ in range(self._depth):
            new = []
            for bit in pattern:
                if bit == 1:
                    new.extend([1, 0, 1])
                else:
                    new.extend([0, 0, 0])
            pattern = new
        return pattern

    @property
    def name(self) -> str:
        return f"cantor_set(depth={self._depth})"

    def generate(self, n: int) -> list[float]:
        """Return n values, cycling the pattern as needed."""
        result = []
        for i in range(n):
            result.append(float(self._pattern[i % len(self._pattern)]))
        return result

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield float(self._pattern[i % len(self._pattern)])
            i += 1


class ZipfDistribution:
    """Power-law frequency distribution (Zipf's law).

    Draws values from a Zipf distribution where P(k) ~ 1/k^exponent.
    Creates natural tonal hierarchy: lower-numbered categories appear
    far more often than higher ones — just like a tonic appears more
    than other scale degrees in tonal music.

    Used for: pitch class selection, tonal weight distribution.
    """

    def __init__(
        self, n_categories: int = 12, exponent: float = 1.0, seed: int = 42
    ) -> None:
        self._n_categories = n_categories
        self._exponent = exponent
        self._rng = random.Random(seed)
        # Pre-compute cumulative distribution
        weights = [1.0 / (k ** exponent) for k in range(1, n_categories + 1)]
        total = sum(weights)
        self._cdf = []
        cumulative = 0.0
        for w in weights:
            cumulative += w / total
            self._cdf.append(cumulative)

    @property
    def name(self) -> str:
        return f"zipf(n={self._n_categories}, exp={self._exponent})"

    def _sample(self) -> float:
        """Draw one sample from the Zipf distribution."""
        r = self._rng.random()
        for k, c in enumerate(self._cdf):
            if r <= c:
                return float(k)
        return float(self._n_categories - 1)

    def generate(self, n: int) -> list[float]:
        """Return n samples from the Zipf distribution (values 0..n_categories-1)."""
        return [self._sample() for _ in range(n)]

    def __iter__(self) -> Iterator[float]:
        while True:
            yield self._sample()


class TextToMelody:
    """Guido d'Arezzo's method (c. 1026): vowels to pitches.

    The earliest documented algorithmic composition technique.
    Extract vowels from text and map them to pitch degrees:
        a -> 0, e -> 1, i -> 2, o -> 3, u -> 4

    These five values correspond to pentatonic scale degrees.

    Used for: text-derived melody, aleatoric composition from prose.
    """

    _VOWEL_MAP = {"a": 0.0, "e": 1.0, "i": 2.0, "o": 3.0, "u": 4.0}

    def __init__(self, text: str = "sacred geometry creates music from mathematics") -> None:
        self._text = text
        self._values = self._extract()

    def _extract(self) -> list[float]:
        """Extract vowel-mapped values from the text."""
        result = []
        for ch in self._text.lower():
            if ch in self._VOWEL_MAP:
                result.append(self._VOWEL_MAP[ch])
        return result if result else [0.0]  # Fallback if no vowels

    @property
    def name(self) -> str:
        return "text_to_melody"

    def generate(self, n: int) -> list[float]:
        """Return n values, cycling through vowel-derived values."""
        result = []
        for i in range(n):
            result.append(self._values[i % len(self._values)])
        return result

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield self._values[i % len(self._values)]
            i += 1


class CombinationTones:
    """Generate bass notes from difference tones of a melody.

    When two frequencies f1 and f2 sound, the ear perceives:
    - First-order: |f1 - f2| (most audible)
    - Second-order: |2*f1 - f2| and |2*f2 - f1|

    This creates bass lines that are physically grounded in the
    melody — uncanny coherence because the ear already "hears"
    these phantom tones (Tartini tones).

    Parameters
    ----------
    melody_pitches : list[int]
        MIDI note numbers of the melody.
    order : int
        1 = first-order only (|f1-f2|), 2 = include second-order
    min_pitch : int
        Minimum MIDI pitch for output (default 36 = C2)
    max_pitch : int
        Maximum MIDI pitch for output (default 60 = C4)
    """

    def __init__(self, melody_pitches: list[int], order: int = 1,
                 min_pitch: int = 36, max_pitch: int = 60) -> None:
        self._melody = melody_pitches
        self._order = order
        self._min = min_pitch
        self._max = max_pitch
        self._values = self._compute()

    @staticmethod
    def _midi_to_freq(midi: int | float) -> float:
        return 440.0 * (2 ** ((midi - 69) / 12))

    @staticmethod
    def _freq_to_midi(freq: float) -> float:
        if freq <= 0:
            return -1.0
        return 69 + 12 * math.log2(freq / 440.0)

    def _fold_to_range(self, midi: float) -> float:
        """Fold a MIDI pitch into the min..max range by octave transposition."""
        if midi < 0:
            return -1.0
        while midi < self._min:
            midi += 12
        while midi > self._max:
            midi -= 12
        if midi < self._min:
            return -1.0  # can't fit in range
        return midi

    def _compute(self) -> list[float]:
        """Compute combination tones from consecutive melody pairs."""
        results: list[float] = []
        for i in range(len(self._melody) - 1):
            f1 = self._midi_to_freq(self._melody[i])
            f2 = self._midi_to_freq(self._melody[i + 1])

            # First-order difference tone: |f1 - f2|
            diff = abs(f1 - f2)
            if diff > 0:
                midi_val = self._fold_to_range(self._freq_to_midi(diff))
                if midi_val >= 0:
                    results.append(midi_val)

            # Second-order difference tones
            if self._order >= 2:
                for combo_freq in [abs(2 * f1 - f2), abs(2 * f2 - f1)]:
                    if combo_freq > 0:
                        midi_val = self._fold_to_range(self._freq_to_midi(combo_freq))
                        if midi_val >= 0:
                            results.append(midi_val)

        return results if results else [float(self._min)]

    @property
    def name(self) -> str:
        return f"combination_tones(order={self._order})"

    def generate(self, n: int) -> list[float]:
        """Return n combination tone values, cycling as needed."""
        return [self._values[i % len(self._values)] for i in range(n)]

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield self._values[i % len(self._values)]
            i += 1


class IChing:
    """I Ching hexagram generator — structured randomness.

    64 hexagrams from 6 binary lines. Unlike pure random, hexagrams
    have internal relationships (upper/lower trigrams, changing lines).
    Each hexagram produces a base value (0-63) plus sub-values from
    its trigram components.

    Used for: form decisions, pitch selection, structured chance.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    @property
    def name(self) -> str:
        return "i_ching"

    def _hexagram(self) -> tuple[int, int, int]:
        """Generate one hexagram, return (hexagram_number, lower_trigram, upper_trigram)."""
        lines = [self._rng.randint(0, 1) for _ in range(6)]
        hex_num = sum(bit << i for i, bit in enumerate(lines))
        lower = sum(bit << i for i, bit in enumerate(lines[:3]))
        upper = sum(bit << i for i, bit in enumerate(lines[3:]))
        return hex_num, lower, upper

    def generate(self, n: int) -> list[float]:
        """Return n hexagram numbers (0-63)."""
        return [float(self._hexagram()[0]) for _ in range(n)]

    def __iter__(self) -> Iterator[float]:
        while True:
            yield float(self._hexagram()[0])


class ThueMorse:
    """Thue-Morse sequence — the fairest binary sequence.

    Built by: start with 0, repeatedly append the complement.
    0, 01, 0110, 01101001, ...

    Has zero autocorrelation at every lag — no rhythmic pattern
    ever repeats exactly. Used by Johnson for anti-repetitive music.
    """

    def __init__(self) -> None:
        pass

    @property
    def name(self) -> str:
        return "thue_morse"

    def generate(self, n: int) -> list[float]:
        """Return n values of the Thue-Morse sequence (0.0 or 1.0)."""
        # thue_morse(i) = number of 1-bits in binary(i) mod 2
        return [float(bin(i).count('1') % 2) for i in range(n)]

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield float(bin(i).count('1') % 2)
            i += 1


class PlanetaryRhythm:
    """Planetary orbital periods as polyrhythmic ratios.

    Real NASA orbital period ratios create phasing cycles that
    never quite align — a celestial canon.

    Used for: polyrhythmic textures, phasing processes.
    """

    PERIODS = {
        "mercury": 0.2408, "venus": 0.6152, "earth": 1.0,
        "mars": 1.8809, "jupiter": 11.862, "saturn": 29.457,
        "uranus": 84.01, "neptune": 164.8,
    }

    def __init__(self, planets: list[str] | None = None, base_period: float = 1.0) -> None:
        # Default: inner 4 planets
        self._planets = planets or ["mercury", "venus", "earth", "mars"]
        self._base = base_period
        self._periods = [self.PERIODS[p] / self.PERIODS[self._planets[0]]
                         for p in self._planets]

    @property
    def name(self) -> str:
        return f"planetary_rhythm({'+'.join(self._planets)})"

    def generate(self, n: int) -> list[float]:
        """Return n values: superposition of sine waves at planetary period ratios."""
        return [sum(math.sin(2 * math.pi * i / max(1, p * self._base * 10))
                for p in self._periods) for i in range(n)]

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield sum(math.sin(2 * math.pi * i / max(1, p * self._base * 10))
                      for p in self._periods)
            i += 1


class SieveScale:
    """Xenakis's sieve theory — pitch sets from modular arithmetic.

    A sieve is a union/intersection of residue classes mod n.
    E.g., {x: x mod 3 = 0} ∪ {x: x mod 4 = 1} = {0, 1, 3, 5, 6, 9, ...}
    Produces asymmetric, non-repeating scales unlike Western equal temperament.

    Used for: pitch set generation, non-standard scales.
    """

    def __init__(self, residues: list[tuple[int, int]] | None = None,
                 modulus_range: int = 128) -> None:
        # residues: list of (modulus, remainder) pairs
        # Default: union of mod 3=0 and mod 5=2 (creates an interesting asymmetric scale)
        self._residues = residues or [(3, 0), (5, 2)]
        self._range = modulus_range
        self._sieve = self._compute()

    def _compute(self) -> list[int]:
        """Compute the sieve as a sorted list of integers passing the residue filter."""
        result: set[int] = set()
        for mod, rem in self._residues:
            for i in range(self._range):
                if i % mod == rem:
                    result.add(i)
        return sorted(result)

    @property
    def name(self) -> str:
        residue_str = ",".join(f"{m}:{r}" for m, r in self._residues)
        return f"sieve_scale({residue_str})"

    def generate(self, n: int) -> list[float]:
        """Return n values, cycling through the sieve pitches."""
        return [float(self._sieve[i % len(self._sieve)]) for i in range(n)]

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield float(self._sieve[i % len(self._sieve)])
            i += 1


class DataPattern:
    """Wrap any numeric dataset as a Pattern — the sonification bridge.

    Feed in CSV data, API responses, sensor readings, or any list of
    floats. The data becomes a pattern that flows through the standard
    generate -> map -> combine -> render pipeline.

    Used for: climate sonification, financial data, biosignals, astronomy.

    Examples
    --------
    >>> data = DataPattern([14.0, 14.1, 14.3, 14.8, 15.2], name="temperature")
    >>> pitches = to_pitch(data.generate(100), scale="C_minor", strategy="normalize")
    """

    def __init__(self, values: list[float], name: str = "data") -> None:
        if not values:
            raise ValueError("DataPattern requires at least one value")
        self._values = [float(v) for v in values]
        self._name = name

    @classmethod
    def from_csv(cls, filepath: str, column: int = 0, skip_header: bool = True,
                 name: str | None = None) -> "DataPattern":
        """Load numeric data from a CSV file column."""
        import csv
        values = []
        with open(filepath, "r") as f:
            reader = csv.reader(f)
            if skip_header:
                next(reader, None)
            for row in reader:
                if len(row) > column:
                    try:
                        values.append(float(row[column]))
                    except ValueError:
                        continue
        return cls(values, name=name or filepath)

    @property
    def name(self) -> str:
        return f"data({self._name})"

    def generate(self, n: int) -> list[float]:
        """Return n values, cycling if the dataset is shorter."""
        return [self._values[i % len(self._values)] for i in range(n)]

    def __iter__(self) -> Iterator[float]:
        i = 0
        while True:
            yield self._values[i % len(self._values)]
            i += 1

    def __len__(self) -> int:
        return len(self._values)
