"""Tests for sacred_composer.patterns — all 17 generators."""

from __future__ import annotations

import itertools
import math
from collections import Counter

import pytest

from sacred_composer.patterns import (
    FibonacciSequence,
    HarmonicSeries,
    InfinitySeries,
    EuclideanRhythm,
    CellularAutomata,
    PinkNoise,
    GoldenSpiral,
    LorenzAttractor,
    DigitsOf,
    SternBrocot,
    LogisticMap,
    Lindenmayer,
    MandelbrotBoundary,
    RosslerAttractor,
    CantorSet,
    ZipfDistribution,
    TextToMelody,
)


# ── FibonacciSequence ────────────────────────────────────────

class TestFibonacciSequence:
    def test_known_values(self):
        fib = FibonacciSequence()
        assert fib.generate(8) == [1.0, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0]

    def test_output_length(self):
        fib = FibonacciSequence()
        for n in (0, 1, 5, 50):
            assert len(fib.generate(n)) == n

    def test_custom_seeds(self):
        fib = FibonacciSequence(a=2, b=3)
        result = fib.generate(5)
        assert result == [2.0, 3.0, 5.0, 8.0, 13.0]

    def test_determinism(self):
        fib1 = FibonacciSequence()
        fib2 = FibonacciSequence()
        assert fib1.generate(20) == fib2.generate(20)

    def test_iterator(self):
        fib = FibonacciSequence()
        first_5 = list(itertools.islice(fib, 5))
        assert first_5 == [1.0, 1.0, 2.0, 3.0, 5.0]

    def test_name(self):
        assert FibonacciSequence().name == "fibonacci"


# ── HarmonicSeries ───────────────────────────────────────────

class TestHarmonicSeries:
    def test_output_length(self):
        hs = HarmonicSeries(fundamental=100.0)
        assert len(hs.generate(10)) == 10

    def test_partials_are_multiples(self):
        hs = HarmonicSeries(fundamental=100.0)
        result = hs.generate(5)
        for i, val in enumerate(result):
            assert val == pytest.approx(100.0 * (i + 1))

    def test_as_midi_returns_correct_count(self):
        hs = HarmonicSeries(fundamental=65.41)
        midis = hs.as_midi(n=8)
        assert len(midis) == 8

    def test_amplitudes_natural_decay(self):
        hs = HarmonicSeries(fundamental=100.0, decay="natural")
        amps = hs.amplitudes(4)
        assert amps == [1.0, 0.5, pytest.approx(1 / 3), 0.25]

    def test_amplitudes_equal(self):
        hs = HarmonicSeries(fundamental=100.0, decay="equal")
        assert hs.amplitudes(4) == [1.0, 1.0, 1.0, 1.0]

    def test_note_name_fundamental(self):
        hs = HarmonicSeries(fundamental="A4")
        assert hs.generate(1) == [pytest.approx(440.0, rel=1e-2)]


# ── InfinitySeries ───────────────────────────────────────────

class TestInfinitySeries:
    def test_known_values_seed_0(self):
        inf = InfinitySeries(seed=0)
        result = inf.generate(8)
        # a(0)=0, a(1)=0+1=1, a(2)=-a(1)=-1, a(3)=a(1)+1=2,
        # a(4)=-a(2)=1, a(5)=a(2)+1=0, a(6)=-a(3)=-2, a(7)=a(3)+1=3
        assert result == [0.0, 1.0, -1.0, 2.0, 1.0, 0.0, -2.0, 3.0]

    def test_output_length(self):
        inf = InfinitySeries()
        assert len(inf.generate(0)) == 0
        assert len(inf.generate(100)) == 100

    def test_determinism(self):
        assert InfinitySeries(seed=5).generate(30) == InfinitySeries(seed=5).generate(30)

    def test_iterator_matches_generate(self):
        inf = InfinitySeries(seed=0)
        gen = inf.generate(10)
        it = list(itertools.islice(InfinitySeries(seed=0), 10))
        assert gen == it


# ── EuclideanRhythm ──────────────────────────────────────────

class TestEuclideanRhythm:
    def test_tresillo(self):
        """E(3,8) should have exactly 3 onsets."""
        er = EuclideanRhythm(3, 8)
        pat = er.pattern
        assert len(pat) == 8
        assert sum(pat) == 3

    def test_cinquillo(self):
        """E(5,8) should have exactly 5 onsets."""
        er = EuclideanRhythm(5, 8)
        assert sum(er.pattern) == 5

    def test_generate_cycles(self):
        er = EuclideanRhythm(3, 8)
        result = er.generate(16)
        assert len(result) == 16
        # Second half is a repeat of the first
        assert result[:8] == result[8:]

    def test_all_onsets_when_k_equals_n(self):
        er = EuclideanRhythm(8, 8)
        assert er.pattern == [1] * 8

    def test_zero_onsets(self):
        er = EuclideanRhythm(0, 8)
        assert er.pattern == [0] * 8

    def test_rotation(self):
        er0 = EuclideanRhythm(3, 8, rotation=0)
        er1 = EuclideanRhythm(3, 8, rotation=1)
        # Rotated pattern has same number of onsets
        assert sum(er0.pattern) == sum(er1.pattern)
        # But different arrangement
        assert er0.pattern != er1.pattern


# ── CellularAutomata ─────────────────────────────────────────

class TestCellularAutomata:
    def test_output_length(self):
        ca = CellularAutomata(rule=110, width=16)
        result = ca.generate(32)
        assert len(result) == 32

    def test_values_are_binary(self):
        ca = CellularAutomata(rule=30, width=8)
        result = ca.generate(24)
        assert all(v in (0.0, 1.0) for v in result)

    def test_determinism(self):
        ca1 = CellularAutomata(rule=90, width=16)
        ca2 = CellularAutomata(rule=90, width=16)
        assert ca1.generate(64) == ca2.generate(64)

    def test_generate_grid_shape(self):
        ca = CellularAutomata(rule=110, width=10)
        grid = ca.generate_grid(5)
        assert len(grid) == 5
        assert all(len(row) == 10 for row in grid)


# ── PinkNoise ────────────────────────────────────────────────

class TestPinkNoise:
    def test_output_length(self):
        pn = PinkNoise(seed=42)
        assert len(pn.generate(50)) == 50

    def test_determinism_with_seed(self):
        pn1 = PinkNoise(seed=42)
        pn2 = PinkNoise(seed=42)
        assert pn1.generate(30) == pn2.generate(30)

    def test_different_seeds_differ(self):
        pn1 = PinkNoise(seed=1)
        pn2 = PinkNoise(seed=2)
        assert pn1.generate(20) != pn2.generate(20)

    def test_values_are_float(self):
        pn = PinkNoise(seed=0)
        result = pn.generate(10)
        assert all(isinstance(v, float) for v in result)


# ── GoldenSpiral ─────────────────────────────────────────────

class TestGoldenSpiral:
    def test_output_length(self):
        gs = GoldenSpiral()
        assert len(gs.generate(20)) == 20

    def test_values_in_0_360(self):
        gs = GoldenSpiral()
        result = gs.generate(100)
        assert all(0.0 <= v < 360.0 for v in result)

    def test_first_value_is_start(self):
        gs = GoldenSpiral(start=45.0)
        assert gs.generate(1)[0] == pytest.approx(45.0)

    def test_determinism(self):
        assert GoldenSpiral().generate(50) == GoldenSpiral().generate(50)


# ── LorenzAttractor ──────────────────────────────────────────

class TestLorenzAttractor:
    def test_output_length(self):
        la = LorenzAttractor()
        assert len(la.generate(100)) == 100

    def test_generate_xyz_returns_tuples(self):
        la = LorenzAttractor()
        xyz = la.generate_xyz(5)
        assert len(xyz) == 5
        assert all(len(t) == 3 for t in xyz)

    def test_determinism(self):
        la1 = LorenzAttractor(initial=(1.0, 1.0, 1.0))
        la2 = LorenzAttractor(initial=(1.0, 1.0, 1.0))
        assert la1.generate(50) == la2.generate(50)

    def test_initial_value(self):
        la = LorenzAttractor(initial=(5.0, 3.0, 1.0))
        assert la.generate(1)[0] == 5.0


# ── DigitsOf ─────────────────────────────────────────────────

class TestDigitsOf:
    def test_pi_first_digits(self):
        d = DigitsOf("pi")
        result = d.generate(5)
        # Digits of pi after decimal: 1, 4, 1, 5, 9
        assert result == [1.0, 4.0, 1.0, 5.0, 9.0]

    def test_output_length(self):
        d = DigitsOf("e")
        assert len(d.generate(30)) == 30

    def test_values_are_single_digits(self):
        d = DigitsOf("phi")
        result = d.generate(50)
        assert all(0.0 <= v <= 9.0 for v in result)

    def test_determinism(self):
        assert DigitsOf("pi").generate(20) == DigitsOf("pi").generate(20)


# ── SternBrocot ──────────────────────────────────────────────

class TestSternBrocot:
    def test_output_length(self):
        sb = SternBrocot(depth=3)
        result = sb.generate(10)
        assert len(result) == 10

    def test_first_fraction_is_1(self):
        sb = SternBrocot()
        fracs = sb.as_fractions(1)
        assert fracs[0] == (1, 1)
        assert sb.generate(1) == [1.0]

    def test_values_are_positive(self):
        sb = SternBrocot(depth=4)
        result = sb.generate(20)
        assert all(v > 0 for v in result)

    def test_determinism(self):
        assert SternBrocot(depth=3).generate(15) == SternBrocot(depth=3).generate(15)


# ── LogisticMap ──────────────────────────────────────────────

class TestLogisticMap:
    def test_output_length(self):
        lm = LogisticMap()
        assert len(lm.generate(50)) == 50

    def test_first_value_is_x0(self):
        lm = LogisticMap(x0=0.3)
        assert lm.generate(1)[0] == pytest.approx(0.3)

    def test_values_stay_bounded(self):
        lm = LogisticMap(r=3.99, x0=0.5)
        result = lm.generate(200)
        assert all(0.0 <= v <= 1.0 for v in result)

    def test_r_sweep(self):
        lm = LogisticMap(r_start=2.5, r_end=3.99, x0=0.5)
        result = lm.generate(100)
        assert len(result) == 100

    def test_determinism(self):
        assert LogisticMap(r=3.7, x0=0.2).generate(40) == LogisticMap(r=3.7, x0=0.2).generate(40)


# ── Lindenmayer ──────────────────────────────────────────────

class TestLindenmayer:
    def test_fibonacci_word_expansion(self):
        ls = Lindenmayer(axiom="A", rules={"A": "AB", "B": "A"})
        assert ls.expand(0) == "A"
        assert ls.expand(1) == "AB"
        assert ls.expand(2) == "ABA"
        assert ls.expand(3) == "ABAAB"

    def test_output_length(self):
        ls = Lindenmayer()
        result = ls.generate(20)
        assert len(result) == 20

    def test_default_values_A_is_0_B_is_1(self):
        ls = Lindenmayer(axiom="A", rules={"A": "AB", "B": "A"})
        result = ls.generate(3)
        # Expansion at depth 2: "ABA" -> values: A=0, B=1, A=0
        assert result == [0.0, 1.0, 0.0]

    def test_custom_alphabet_values(self):
        ls = Lindenmayer(
            axiom="A",
            rules={"A": "AB", "B": "A"},
            alphabet_values={"A": 10.0, "B": 20.0},
        )
        result = ls.generate(3)
        assert result == [10.0, 20.0, 10.0]

    def test_determinism(self):
        ls1 = Lindenmayer(axiom="A", rules={"A": "AB", "B": "A"})
        ls2 = Lindenmayer(axiom="A", rules={"A": "AB", "B": "A"})
        assert ls1.generate(30) == ls2.generate(30)


# ── MandelbrotBoundary ──────────────────────────────────────

class TestMandelbrotBoundary:
    def test_output_length(self):
        mb = MandelbrotBoundary()
        for n in (0, 1, 10, 50):
            assert len(mb.generate(n)) == n

    def test_values_are_positive_ints(self):
        mb = MandelbrotBoundary(max_iter=100)
        result = mb.generate(30)
        for v in result:
            assert v >= 1.0
            assert v == float(int(v))  # integer-valued floats

    def test_determinism(self):
        mb1 = MandelbrotBoundary(perturbation=0.03)
        mb2 = MandelbrotBoundary(perturbation=0.03)
        assert mb1.generate(40) == mb2.generate(40)


# ── RosslerAttractor ────────────────────────────────────────

class TestRosslerAttractor:
    def test_output_length(self):
        ra = RosslerAttractor()
        assert len(ra.generate(100)) == 100

    def test_generate_xyz_returns_3_tuples(self):
        ra = RosslerAttractor()
        xyz = ra.generate_xyz(10)
        assert len(xyz) == 10
        assert all(len(t) == 3 for t in xyz)

    def test_determinism(self):
        ra1 = RosslerAttractor(initial=(1.0, 1.0, 1.0))
        ra2 = RosslerAttractor(initial=(1.0, 1.0, 1.0))
        assert ra1.generate(50) == ra2.generate(50)


# ── CantorSet ───────────────────────────────────────────────

class TestCantorSet:
    def test_depth_1_produces_1_0_1(self):
        cs = CantorSet(depth=1)
        assert cs.generate(3) == [1.0, 0.0, 1.0]

    def test_depth_2_produces_correct_9_elements(self):
        cs = CantorSet(depth=2)
        expected = [1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0]
        assert cs.generate(9) == expected

    def test_cycling(self):
        cs = CantorSet(depth=1)
        result = cs.generate(6)
        # Pattern [1, 0, 1] cycles: [1, 0, 1, 1, 0, 1]
        assert result == [1.0, 0.0, 1.0, 1.0, 0.0, 1.0]


# ── ZipfDistribution ───────────────────────────────────────

class TestZipfDistribution:
    def test_output_length(self):
        zd = ZipfDistribution(seed=0)
        for n in (0, 1, 20, 100):
            assert len(zd.generate(n)) == n

    def test_values_in_range(self):
        n_cat = 7
        zd = ZipfDistribution(n_categories=n_cat, seed=99)
        result = zd.generate(200)
        for v in result:
            assert 0 <= v < n_cat

    def test_lower_values_more_frequent(self):
        zd = ZipfDistribution(n_categories=12, exponent=1.0, seed=1)
        result = zd.generate(1000)
        counts = Counter(result)
        # Category 0 should be more frequent than category 11
        assert counts.get(0.0, 0) > counts.get(11.0, 0)


# ── TextToMelody ────────────────────────────────────────────

class TestTextToMelody:
    def test_known_vowel_values(self):
        """'aeiou' should produce [0, 1, 2, 3, 4]."""
        ttm = TextToMelody(text="aeiou")
        assert ttm.generate(5) == [0.0, 1.0, 2.0, 3.0, 4.0]

    def test_output_length_matches_vowel_count(self):
        text = "hello world"
        # vowels: e, o, o -> 3 vowels
        ttm = TextToMelody(text=text)
        # Requesting exactly the number of vowels
        assert len(ttm.generate(3)) == 3
        # Requesting more cycles
        assert len(ttm.generate(7)) == 7

    def test_consonants_ignored(self):
        ttm = TextToMelody(text="bcdfg")
        # No vowels -> fallback [0.0]
        assert ttm.generate(1) == [0.0]
