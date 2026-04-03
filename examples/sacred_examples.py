"""Three example compositions demonstrating Sacred Composer Phase 1.

Each composition uses different pattern combinations to show the system's
range. Every note is traceable to a specific pattern and mapping.
"""

from sacred_composer import *


def overtone_cathedral():
    """A meditation built from one cello note's overtone series.

    Patterns used:
    - HarmonicSeries(C2): pitch material from overtones
    - InfinitySeries: self-similar melody through the overtone pitches
    - EuclideanRhythm(5,8): Cuban cinquillo rhythm
    - FibonacciSequence: formal proportions
    - PinkNoise: humanized dynamics
    """
    print("\n=== Overtone Cathedral ===")

    fundamental = HarmonicSeries("C2")
    overtone_pitches = fundamental.as_chord(n=12, quantize=True)

    # Melody: infinity series mapped to overtone pitches
    melody_raw = InfinitySeries(seed=0).generate(96)
    pitches = to_pitch(melody_raw, pitch_set=overtone_pitches, strategy="modular")

    # Rhythm: Euclidean E(5,8) cinquillo, quarter-note base
    rhythm_raw = EuclideanRhythm(5, 8).generate(96)
    durations = to_rhythm(rhythm_raw, base_duration=0.5, strategy="binary")

    # Dynamics: pink noise for natural fluctuation
    dynamics = to_dynamics(
        PinkNoise(sigma=2.0, seed=42).generate(96),
        velocity_range=(45, 95),
    )

    # Form: Fibonacci proportions
    form = to_form(FibonacciSequence().generate(5), total_bars=21)

    # Assemble
    piece = Composition(tempo=54, title="Overtone Cathedral")
    piece.form = form

    piece.add_voice("cello_melody", pitches, durations, dynamics, instrument="cello")

    # Drone: fundamental C2 sustained throughout
    total_beats = sum(abs(d) for d in durations)
    piece.add_drone("cello_drone", pitch=36, total_beats=total_beats,
                    velocity=60, instrument="contrabass")

    filename = piece.render("sacred_overtone_cathedral.mid")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Form:     {' | '.join(f'{s.label}({s.bars}b)' for s in form)}")
    print(f"  File:     {filename}")
    return piece


def fibonacci_garden():
    """A piece where Fibonacci governs everything.

    Patterns used:
    - FibonacciSequence: pitch intervals, form, rhythm groupings
    - EuclideanRhythm(8,13): 13 is Fibonacci, 8 is Fibonacci
    - HarmonicSeries(A2): harmonic grounding
    - PinkNoise: dynamic variation
    """
    print("\n=== Fibonacci Garden ===")

    n_notes = 89  # Fibonacci number

    # Pitch: Fibonacci values mapped to A minor scale
    fib_values = FibonacciSequence().generate(n_notes)
    pitches = to_pitch(fib_values, scale="A_minor", octave_range=(3, 5), strategy="modular")

    # Rhythm: Euclidean E(8,13) — both Fibonacci numbers
    rhythm_raw = EuclideanRhythm(8, 13).generate(n_notes)
    durations = to_rhythm(rhythm_raw, base_duration=0.75, strategy="binary")

    # Dynamics: normalize Fibonacci values themselves for crescendo effect
    dynamics = to_dynamics(fib_values, velocity_range=(35, 105))

    # Form: golden section — two sections in phi ratio
    form = to_form([1.0, phi], total_bars=34, section_labels=["A", "B"])

    # Bass voice: harmonic series of A2 as slow-moving harmony
    bass_series = HarmonicSeries("A2")
    bass_pitches = bass_series.as_chord(n=5, quantize=True)
    # One bass note per form section
    bass_p = to_pitch(list(range(len(form))), pitch_set=bass_pitches, strategy="modular")
    bass_d = [float(s.bars * 4) for s in form]  # hold for entire section
    bass_v = [55] * len(form)

    piece = Composition(tempo=72, title="Fibonacci Garden")
    piece.form = form

    piece.add_voice("melody", pitches, durations, dynamics, instrument="flute")
    piece.add_voice("bass", bass_p, bass_d, bass_v, instrument="cello")

    filename = piece.render("sacred_fibonacci_garden.mid")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Form:     {' | '.join(f'{s.label}({s.bars}b)' for s in form)}")
    print(f"  File:     {filename}")
    return piece


def edge_of_chaos():
    """Cellular automata texture — Rule 110 at the boundary of order and chaos.

    Patterns used:
    - CellularAutomata(rule=110): pitch and rhythm from grid
    - CellularAutomata(rule=90): Sierpinski triangle for second voice
    - PinkNoise: dynamics
    - FibonacciSequence: form
    """
    print("\n=== Edge of Chaos ===")

    n_steps = 32

    # Voice 1: Rule 110 (complex/Turing-complete)
    ca110 = CellularAutomata(rule=110, width=8)
    grid110 = ca110.generate_grid(n_steps)

    # Use each row as a chord/beat: active cells = sounding pitches
    # Flatten for melody: take the center column's value over time
    ca_values = ca110.generate(128)
    pitches_1 = to_pitch(
        [sum(row) for row in grid110] * 4,  # density as pitch proxy
        scale="C_minor", octave_range=(4, 5), strategy="modular",
    )
    durations_1 = to_rhythm(
        EuclideanRhythm(5, 8).generate(128),
        base_duration=0.5, strategy="binary",
    )

    # Voice 2: Rule 90 (Sierpinski — self-similar fractal)
    ca90 = CellularAutomata(rule=90, width=8)
    ca90_values = ca90.generate(128)
    pitches_2 = to_pitch(
        [sum(row) for row in ca90.generate_grid(n_steps)] * 4,
        scale="C_minor", octave_range=(3, 4), strategy="modular",
    )
    durations_2 = to_rhythm(
        EuclideanRhythm(3, 8).generate(128),
        base_duration=1.0, strategy="binary",
    )

    # Dynamics: pink noise
    dyn_1 = to_dynamics(PinkNoise(sigma=1.5, seed=7).generate(128), velocity_range=(50, 100))
    dyn_2 = to_dynamics(PinkNoise(sigma=1.5, seed=13).generate(128), velocity_range=(40, 85))

    # Form: Fibonacci
    form = to_form(FibonacciSequence().generate(4), total_bars=21, section_labels=["A", "B", "C", "D"])

    piece = Composition(tempo=88, title="Edge of Chaos")
    piece.form = form

    n = min(len(pitches_1), len(durations_1))
    piece.add_voice("rule_110", pitches_1[:n], durations_1[:n], dyn_1[:n], instrument="vibraphone")
    n2 = min(len(pitches_2), len(durations_2))
    piece.add_voice("rule_90", pitches_2[:n2], durations_2[:n2], dyn_2[:n2], instrument="marimba")

    filename = piece.render("sacred_edge_of_chaos.mid")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Form:     {' | '.join(f'{s.label}({s.bars}b)' for s in form)}")
    print(f"  File:     {filename}")
    return piece


if __name__ == "__main__":
    print("=" * 60)
    print("  SACRED COMPOSER — Phase 1 Examples")
    print("=" * 60)

    p1 = overtone_cathedral()
    p2 = fibonacci_garden()
    p3 = edge_of_chaos()

    print("\n" + "=" * 60)
    print("  ALL EXAMPLES COMPLETE")
    print("=" * 60)
    print(f"\n  {p1}")
    print(f"  {p2}")
    print(f"  {p3}")
    print()
