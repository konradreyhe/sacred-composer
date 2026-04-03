"""Five Phase 2 example compositions — extended patterns and combiners.

Each demonstrates a different Phase 2 capability:
1. Lorenz Butterfly — chaotic attractor as melody
2. Fractal Fern — L-system formal structure
3. Canon of the Spheres — canon combiner with golden spiral
4. Phase Drift — Steve Reich-inspired phasing
5. Order to Chaos — logistic map tension arc
"""

from sacred_composer import *
from sacred_composer.core import GM_INSTRUMENTS


def lorenz_butterfly():
    """Melody from the Lorenz attractor's two-wing trajectory.

    The x-coordinate becomes melody (two lobes = two pitch regions),
    y becomes rhythm variation, z becomes dynamics. Structured chaos.
    """
    print("\n=== Lorenz Butterfly ===")

    lorenz = LorenzAttractor(sigma=10, rho=28, beta=8/3, dt=0.01)
    xyz = lorenz.generate_xyz(200)

    # Sample every 5th point for musical density
    sampled = xyz[::5]
    xs = [p[0] for p in sampled]
    ys = [p[1] for p in sampled]
    zs = [p[2] for p in sampled]

    pitches = to_pitch(xs, scale="D_minor", octave_range=(3, 5), strategy="normalize")
    durations = to_rhythm(
        [abs(y) for y in ys],
        base_duration=0.25, strategy="quantize",
    )
    dynamics = to_dynamics(zs, velocity_range=(40, 105))

    form = to_form(FibonacciSequence().generate(5), total_bars=21)

    piece = Composition(tempo=96, title="Lorenz Butterfly")
    piece.form = form
    piece.add_voice("attractor", pitches, durations, dynamics, instrument="violin")

    # Second voice: digits of pi as a subtle counterpoint
    pi_vals = DigitsOf("pi").generate(len(pitches))
    pi_pitches = to_pitch(pi_vals, scale="D_minor", octave_range=(2, 3), strategy="modular")
    pi_durations = [2.0] * len(pi_pitches)  # slow whole notes
    pi_dynamics = [50] * len(pi_pitches)

    piece.add_voice("pi_bass", pi_pitches, pi_durations, pi_dynamics, instrument="cello")

    filename = piece.render("sacred_lorenz_butterfly.mid")
    piece.render("sacred_lorenz_butterfly.ly")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  File:     {filename} + .ly")
    return piece


def fractal_fern():
    """L-system drives the formal structure: A->ABA, B->BCB.

    The L-system expansion creates self-similar sections at multiple
    scales. Each letter maps to a different musical character.
    """
    print("\n=== Fractal Fern ===")

    # L-system for form: A=tonic, B=dominant, C=chromatic
    lsys = Lindenmayer(
        axiom="A",
        rules={"A": "ABA", "B": "BCB", "C": "A"},
        alphabet_values={"A": 0, "B": 7, "C": 6},  # semitone offsets
    )
    formal_values = lsys.generate(27)  # depth-3 expansion: 27 characters

    # Each formal value becomes a short motif based on infinity series
    all_pitches = []
    all_durations = []
    all_dynamics = []

    inf = InfinitySeries(seed=0)
    base_motif = inf.generate(8)

    for fv in formal_values:
        transposition = int(fv)
        motif_pitches = to_pitch(
            base_motif,
            scale="C_major", octave_range=(4, 5), strategy="modular",
        )
        # Transpose by the formal value
        motif_pitches = [p + transposition for p in motif_pitches]
        motif_durations = to_rhythm(
            EuclideanRhythm(5, 8).generate(8),
            base_duration=0.5, strategy="binary",
        )
        motif_dynamics = to_dynamics(
            PinkNoise(sigma=1.0, seed=int(fv * 100) % 1000).generate(8),
            velocity_range=(55, 90),
        )

        all_pitches.extend(motif_pitches)
        all_durations.extend(motif_durations)
        all_dynamics.extend(motif_dynamics)

    form = to_form(
        FibonacciSequence().generate(3),
        total_bars=27,
        section_labels=["Exposition", "Development", "Recapitulation"],
    )

    piece = Composition(tempo=80, title="Fractal Fern")
    piece.form = form
    piece.add_voice("fern", all_pitches, all_durations, all_dynamics, instrument="piano")

    filename = piece.render("sacred_fractal_fern.mid")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  L-system: {lsys.expand(3)[:40]}...")
    print(f"  File:     {filename}")
    return piece


def canon_of_the_spheres():
    """Three-voice canon using golden spiral melodic intervals.

    The golden angle (137.5 deg) generates maximally spaced intervals.
    Three voices enter in staggered canon at different transpositions.
    """
    print("\n=== Canon of the Spheres ===")

    spiral = GoldenSpiral()
    spiral_values = spiral.generate(48)

    pitches = to_pitch(spiral_values, scale="G_major", octave_range=(4, 5), strategy="normalize")
    durations = to_rhythm(
        EuclideanRhythm(7, 12).generate(48),  # West African bell pattern
        base_duration=0.5, strategy="binary",
    )
    dynamics = to_dynamics(
        PinkNoise(sigma=1.5, seed=99).generate(48),
        velocity_range=(50, 95),
    )

    # Create 3-voice canon: entries at 8 beats apart, transposed by 0, -5, -12 semitones
    voices = canon(
        pitches, durations, dynamics,
        n_voices=3,
        offset_beats=8.0,
        transpositions=[0, -5, -12],  # unison, 4th below, octave below
        instrument=GM_INSTRUMENTS["flute"],
    )

    piece = Composition(tempo=66, title="Canon of the Spheres")
    for v in voices:
        piece.score.add_voice(v)

    form = to_form([1, phi, 1], total_bars=21, section_labels=["Entry", "Full", "Coda"])
    piece.form = form

    filename = piece.render("sacred_canon_spheres.mid")
    piece.render("sacred_canon_spheres.ly")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Canon:    3 voices, 8-beat offset, transposed [0, -5, -12]")
    print(f"  File:     {filename} + .ly")
    return piece


def phase_drift():
    """Steve Reich-inspired phase music — two voices gradually drift apart.

    Same Euclidean rhythm pattern in both voices, but voice 2 is 2% faster.
    Over time, the patterns phase through all possible alignments.
    """
    print("\n=== Phase Drift ===")

    # A pentatonic melody from harmonic series
    hs = HarmonicSeries("C3")
    overtones = hs.as_chord(n=8, quantize=True)

    # Use Stern-Brocot ratios to pick notes from overtones
    sb = SternBrocot(depth=3)
    sb_values = sb.generate(64)
    pitches = to_pitch(sb_values, pitch_set=overtones, strategy="normalize")

    # Euclidean rhythm
    durations = to_rhythm(
        EuclideanRhythm(5, 8).generate(64),
        base_duration=0.5, strategy="binary",
    )
    dynamics = to_dynamics(
        PinkNoise(sigma=1.0, seed=55).generate(64),
        velocity_range=(55, 85),
    )

    # Phase: voice 1 at normal rate, voice 2 at 97% rate (3% slower)
    voices = phase(
        pitches, durations, dynamics,
        n_voices=2,
        rate_multipliers=[1.0, 0.97],
        instrument=GM_INSTRUMENTS["marimba"],
    )

    piece = Composition(tempo=120, title="Phase Drift")
    for v in voices:
        piece.score.add_voice(v)

    filename = piece.render("sacred_phase_drift.mid")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Phase:    voice 2 at 97% rate (3% slower)")
    print(f"  File:     {filename}")
    return piece


def order_to_chaos():
    """The logistic map sweeps from stability to chaos.

    r increases from 2.5 (fixed point = calm repetition) through
    period doubling (increasing complexity) to 3.99 (full chaos).
    The piece literally dissolves from order into chaos.
    """
    print("\n=== Order to Chaos ===")

    n_notes = 128

    # Logistic map sweeping from order to chaos
    lm = LogisticMap(r_start=2.5, r_end=3.99, x0=0.5)
    logistic_values = lm.generate(n_notes)

    # Melody: logistic values mapped to pitch
    pitches = to_pitch(
        logistic_values,
        scale="A_harmonic_minor", octave_range=(3, 5), strategy="normalize",
    )

    # Rhythm: starts regular, becomes increasingly erratic
    # Use the logistic values themselves as rhythm source
    durations = to_rhythm(logistic_values, base_duration=1.0, strategy="quantize")

    # Dynamics: logistic map for velocity too — grows more extreme
    dynamics = to_dynamics(logistic_values, velocity_range=(35, 115))

    # Second voice: cellular automata Rule 30 (chaotic) as bass texture
    ca = CellularAutomata(rule=30, width=8)
    ca_vals = ca.generate(n_notes)
    bass_pitches = to_pitch(ca_vals, scale="A_minor", octave_range=(2, 3), strategy="modular")
    bass_durs = to_rhythm(
        EuclideanRhythm(3, 8).generate(n_notes),
        base_duration=1.0, strategy="binary",
    )
    bass_dyns = to_dynamics(
        PinkNoise(sigma=1.0, seed=77).generate(n_notes),
        velocity_range=(40, 75),
    )

    form = to_form(
        [1, 2, 3, 5],
        total_bars=34,
        section_labels=["Stability", "Oscillation", "Doubling", "Chaos"],
    )

    piece = Composition(tempo=76, title="Order to Chaos")
    piece.form = form
    piece.add_voice("logistic", pitches, durations, dynamics, instrument="piano")
    piece.add_voice("automata_bass", bass_pitches, bass_durs, bass_dyns, instrument="contrabass")

    filename = piece.render("sacred_order_to_chaos.mid")
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
    print("  SACRED COMPOSER — Phase 2 Examples")
    print("=" * 60)

    p1 = lorenz_butterfly()
    p2 = fractal_fern()
    p3 = canon_of_the_spheres()
    p4 = phase_drift()
    p5 = order_to_chaos()

    print("\n" + "=" * 60)
    print("  ALL PHASE 2 EXAMPLES COMPLETE")
    print("=" * 60)
    for p in [p1, p2, p3, p4, p5]:
        print(f"  {p}")
    print()
