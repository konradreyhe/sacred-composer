"""Phase 3 example compositions — fractal form, microtonal, WAV, evaluation.

1. Fractal Cathedral — L-system fractal_form combiner
2. Spectral Meditation — microtonal overtones (just intonation)
3. Fibonacci Waltz — evaluated composition with WAV render
"""

from sacred_composer import *
from sacred_composer.core import GM_INSTRUMENTS


def fractal_cathedral():
    """L-system driven formal structure with three motif types.

    A -> tonic motif (stable, grounded)
    B -> dominant motif (tension, reaching)
    C -> chromatic motif (dissonance, brief)

    L-system ABA -> BCB -> A expands into self-similar form.
    """
    print("\n=== Fractal Cathedral ===")

    # Define three contrasting motifs
    motifs = {
        "A": {
            "pitches": to_pitch(
                InfinitySeries(seed=0).generate(6),
                scale="C_major", octave_range=(4, 5), strategy="modular",
            ),
            "durations": [0.5, 0.5, 0.5, 0.5, 1.0, 1.0],
            "velocities": to_dynamics(
                PinkNoise(sigma=1.0, seed=1).generate(6),
                velocity_range=(60, 85),
            ),
            "instrument": GM_INSTRUMENTS["organ"],
        },
        "B": {
            "pitches": to_pitch(
                [7, 9, 11, 12, 11, 9],  # dominant region
                scale="C_major", octave_range=(4, 5), strategy="modular",
            ),
            "durations": [0.25, 0.25, 0.5, 1.0, 0.5, 0.5],
            "velocities": to_dynamics(
                PinkNoise(sigma=1.5, seed=2).generate(6),
                velocity_range=(70, 100),
            ),
            "instrument": GM_INSTRUMENTS["organ"],
        },
        "C": {
            "pitches": to_pitch(
                [11, 10, 9, 8],  # chromatic descent
                scale="C_chromatic", octave_range=(5, 5), strategy="modular",
            ),
            "durations": [0.25, 0.25, 0.25, 0.25],
            "velocities": [95, 85, 75, 65],
            "instrument": GM_INSTRUMENTS["organ"],
        },
    }

    voices, form_sections = fractal_form(
        motifs,
        axiom="A",
        rules={"A": "ABA", "B": "BCB", "C": "A"},
        depth=3,
    )

    piece = Composition(tempo=60, title="Fractal Cathedral")
    for v in voices:
        v.instrument = GM_INSTRUMENTS["organ"]
        piece.score.add_voice(v)
    piece.form = form_sections

    # Add a bass drone on C2
    total_beats = piece.score.duration
    piece.add_drone("pedal_c", pitch=36, total_beats=total_beats,
                    velocity=55, instrument="organ")

    filename = piece.render("sacred_fractal_cathedral.mid")
    piece.render("sacred_fractal_cathedral.ly")
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Sections: {len(form_sections)} (L-system depth 3)")
    print(f"  File:     {filename} + .ly")
    return piece


def spectral_meditation():
    """Microtonal piece using the pure overtone series — just intonation.

    The harmonic series of C2 is NOT quantized to 12-TET. The 7th partial
    (natural 7th, ~969 Hz) is 31 cents flat of Bb4. The 11th partial
    (~1046 Hz) sits between F5 and F#5. These deviations from equal
    temperament give the piece its distinctive spectral character.
    """
    print("\n=== Spectral Meditation ===")

    fundamental = HarmonicSeries("C2")

    # Get unquantized overtone frequencies
    freqs = fundamental.generate(16)
    # Convert to fractional MIDI
    micro_pitches = to_pitch_microtonal(freqs)

    # Melody: walk through the overtones using infinity series as index
    inf_vals = InfinitySeries(seed=0).generate(48)
    melody_indices = [int(abs(v)) % len(micro_pitches) for v in inf_vals]
    melody_pitches = [micro_pitches[i] for i in melody_indices]

    # Rhythm: Euclidean with longer durations for meditative feel
    rhythm_raw = EuclideanRhythm(5, 8).generate(48)
    durations = to_rhythm(rhythm_raw, base_duration=1.0, strategy="binary")

    # Dynamics: very subtle pink noise variation
    dynamics = to_dynamics(
        PinkNoise(sigma=0.5, seed=33).generate(48),
        velocity_range=(45, 70),
    )

    piece = Composition(tempo=48, title="Spectral Meditation")

    piece.add_voice(
        "spectral_voice",
        melody_pitches, durations, dynamics,
        instrument="strings",
        microtonal=True,
    )

    # Drone: fundamental C2 (no microtonal needed — it's the reference)
    total_beats = sum(abs(d) for d in durations)
    piece.add_drone("fundamental", pitch=36, total_beats=total_beats,
                    velocity=50, instrument="cello")

    filename = piece.render("sacred_spectral_meditation.mid")
    info = piece.info()

    # Show the microtonal deviations
    unique_pitches = sorted(set(melody_pitches))
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Microtonal pitches: {len(unique_pitches)} unique")
    for mp in unique_pitches[:8]:
        cents_off = (mp - round(mp)) * 100
        print(f"    MIDI {mp:.2f} ({cents_off:+.0f} cents from 12-TET)")
    print(f"  File:     {filename}")
    return piece


def fibonacci_waltz():
    """A waltz in 3/4 evaluated by the framework, rendered to WAV.

    Fibonacci governs the melody, golden ratio the form, Euclidean
    rhythm provides the waltz feel, pink noise humanizes.
    """
    print("\n=== Fibonacci Waltz (with WAV + evaluation) ===")

    n_notes = 96

    # Melody: Fibonacci mapped to F major
    fib_vals = FibonacciSequence().generate(n_notes)
    pitches = to_pitch(fib_vals, scale="F_major", octave_range=(4, 5), strategy="modular")

    # Waltz rhythm: E(2,3) = [1,0,1] — strong-weak-weak in 3/4
    waltz_pattern = EuclideanRhythm(2, 3).generate(n_notes)
    durations = to_rhythm(waltz_pattern, base_duration=1.0, strategy="binary")

    # Dynamics: pink noise with waltz emphasis
    raw_dyn = PinkNoise(sigma=1.5, seed=88).generate(n_notes)
    dynamics = to_dynamics(raw_dyn, velocity_range=(50, 95))

    # Golden ratio form
    form = to_form([1, phi, 1], total_bars=24, section_labels=["A", "B", "A'"])

    # Bass: simple oom-pah-pah
    bass_notes = to_pitch([0, 4, 4] * (n_notes // 3), scale="F_major",
                          octave_range=(3, 3), strategy="modular")
    bass_dur = [1.0] * n_notes
    bass_dyn = [70, 45, 45] * (n_notes // 3)

    piece = Composition(tempo=132, title="Fibonacci Waltz")
    piece.form = form
    piece.add_voice("melody", pitches, durations, dynamics, instrument="piano")
    piece.add_voice("bass", bass_notes, bass_dur, bass_dyn[:len(bass_notes)],
                    instrument="piano", channel=1)

    # Render all three formats
    piece.render("sacred_fibonacci_waltz.mid")
    piece.render("sacred_fibonacci_waltz.ly")

    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}")
    print(f"  Notes:    {info['total_notes']}")
    print(f"  Duration: {info['duration_seconds']:.1f}s")
    print(f"  Form:     {' | '.join(f'{s.label}({s.bars}b)' for s in form)}")

    # WAV render
    print("  Rendering WAV (pure Python synthesis)...")
    piece.render("sacred_fibonacci_waltz.wav")
    wav_size = __import__("os").path.getsize("sacred_fibonacci_waltz.wav") / (1024 * 1024)
    print(f"  WAV:      sacred_fibonacci_waltz.wav ({wav_size:.1f} MB)")

    # Evaluation
    print("  Running evaluation...")
    result = evaluate_composition(piece, verbose=True)

    return piece


if __name__ == "__main__":
    print("=" * 60)
    print("  SACRED COMPOSER — Phase 3 Examples")
    print("=" * 60)

    p1 = fractal_cathedral()
    p2 = spectral_meditation()
    p3 = fibonacci_waltz()

    print("\n" + "=" * 60)
    print("  ALL PHASE 3 EXAMPLES COMPLETE")
    print("=" * 60)
    for p in [p1, p2, p3]:
        print(f"  {p}")
    print()
