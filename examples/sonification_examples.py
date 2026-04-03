"""Data sonification examples — turning real-world data into music.

Four demonstrations of Sacred Composer's DataPattern, each mapping a
different dataset to pitch, rhythm, and dynamics through the standard
generate -> map -> render pipeline.

Run:  python examples/sonification_examples.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sacred_composer import (
    Composition, DataPattern, FibonacciSequence, DigitsOf,
    to_pitch, to_rhythm, to_dynamics,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sonification_output")


def climate_sonification():
    """Global temperature anomaly (1880-2024) as a rising melody with CO2 drone.

    Each year becomes one note. Lower anomalies map to lower pitches,
    higher anomalies to higher. The listener hears a melody that gradually
    climbs upward — slow and ambiguous in the early decades, then
    unmistakably ascending from the 1980s onward. A cello drone rises
    in two steps to mark the acceleration.
    """
    print("\n=== 1. Climate Sonification (1880-2024) ===")

    # Simplified NASA GISS annual global temperature anomaly (degrees C).
    # Sampled at ~5-year intervals, then filled to ~145 yearly values.
    temp_data = [
        -0.18, -0.10, -0.15, -0.12, -0.28, -0.32, -0.30, -0.36, -0.27, -0.17,
        -0.26, -0.24, -0.29, -0.32, -0.35, -0.20, -0.15, -0.37, -0.46, -0.29,
        -0.27, -0.25, -0.31, -0.38, -0.13, -0.14, -0.36, -0.14, -0.17, -0.28,
        -0.10, -0.07, -0.16, -0.04, -0.12, -0.18, -0.07, -0.01, -0.04,  0.04,
        -0.02, -0.06, -0.13, -0.19, -0.22, -0.21, -0.06,  0.01,  0.08,  0.05,
         0.03, -0.01, -0.03,  0.07,  0.10,  0.14, -0.14, -0.07, -0.01, -0.05,
        -0.08,  0.05,  0.03, -0.02,  0.06, -0.20, -0.11, -0.06, -0.02, -0.08,
         0.05,  0.09, -0.07,  0.02,  0.06, -0.02, -0.08,  0.01,  0.16,  0.12,
        -0.01, -0.16, -0.12, -0.10,  0.22,  0.14,  0.08,  0.04,  0.07,  0.12,
         0.18,  0.22,  0.14,  0.16,  0.19,  0.20,  0.21,  0.10,  0.07,  0.12,
         0.18,  0.27,  0.32,  0.13,  0.10,  0.08,  0.17,  0.28,  0.34,  0.12,
         0.15,  0.25,  0.28,  0.34,  0.40,  0.46,  0.33,  0.44,  0.42,  0.55,
         0.54,  0.63,  0.41,  0.54,  0.57,  0.62,  0.40,  0.52,  0.63,  0.62,
         0.65,  0.75,  0.85,  0.99,  1.02,  0.92,  0.85,  0.98,  1.01,  0.82,
         0.89,  0.85,  1.17,  1.02,  1.18,
    ]

    n = len(temp_data)
    pattern = DataPattern(temp_data, name="temperature_anomaly")
    values = pattern.generate(n)

    pitches = to_pitch(values, scale="C_minor", octave_range=(3, 6), strategy="normalize")
    durations = to_rhythm([0.5] * n, base_duration=1.0, strategy="proportional")
    dynamics = to_dynamics(values, velocity_range=(40, 100), strategy="normalize")

    piece = Composition(tempo=160, title="Warming — Climate Data 1880-2024")

    piece.add_voice("temperature", pitches, durations, dynamics, instrument="piano")

    # CO2 drone: low organ note for first half, rising for second half
    half = sum(durations) / 2
    piece.add_drone("co2_low", pitch=36, total_beats=half, velocity=50, instrument="cello")
    piece.add_voice(
        "co2_high",
        pitches=[43],
        durations=[half],
        velocities=[60],
        instrument="cello",
        channel=2,
    )

    out = os.path.join(OUTPUT_DIR, "climate_sonification.mid")
    piece.render(out)
    print(f"  Notes:    {n} (one per year, 1880-2024)")
    print(f"  Mapping:  temperature anomaly -> pitch (C minor) + velocity")
    print(f"  Listen:   the melody drifts low and ambiguous for a century,")
    print(f"            then climbs steeply from the 1980s. The drone rises too.")
    print(f"  Output:   {out}")
    return out


def fibonacci_sonification():
    """Fibonacci numbers as both pitch and rhythm.

    The Fibonacci values control pitch (modular wrap through a scale)
    and rhythm (proportional durations normalized to musical range).
    Small early values produce short, low notes; larger values yield
    longer, leaping pitches. The golden ratio emerges audibly as the
    series grows: note durations approach phi-proportional relationships.
    """
    print("\n=== 2. Fibonacci Sequence Sonification ===")

    fib = FibonacciSequence().generate(20)

    pitches = to_pitch(fib, scale="D_major", octave_range=(3, 5), strategy="modular")

    # Rhythm: Fibonacci values as proportional durations, capped for musicality
    max_fib = max(fib)
    rhythm_values = [v / max_fib * 3.0 for v in fib]  # scale to 0..3 beats
    durations = to_rhythm(rhythm_values, base_duration=1.0, strategy="proportional")

    dynamics = to_dynamics(fib, velocity_range=(50, 110), strategy="normalize")

    piece = Composition(tempo=90, title="Golden Growth — Fibonacci Sonification")
    piece.add_voice("fibonacci", pitches, durations, dynamics, instrument="piano")

    # Pedal tone on the tonic
    total = sum(durations)
    piece.add_drone("tonic_pedal", pitch=50, total_beats=total, velocity=45, instrument="cello")

    out = os.path.join(OUTPUT_DIR, "fibonacci_sonification.mid")
    piece.render(out)
    print(f"  Values:   {[int(f) for f in fib]}")
    print(f"  Mapping:  Fibonacci -> pitch (modular, D major) AND rhythm (proportional)")
    print(f"  Listen:   starts with tiny repeated notes (1, 1, 2, 3...), then")
    print(f"            durations and leaps grow exponentially. The golden ratio")
    print(f"            lives in the spacing between notes.")
    print(f"  Output:   {out}")
    return out


def constants_race():
    """Pi, e, and phi digits as three competing melodies.

    Same rhythm, different pitch sequences. Each digit (0-9) maps to
    a scale degree. The three voices diverge and occasionally align,
    revealing where the constants share digit sequences. Pi sounds
    the most 'random'; phi, built from the golden ratio, has subtle
    self-similarity the ear can almost catch.
    """
    print("\n=== 3. Mathematical Constants Race (pi vs e vs phi) ===")

    n = 50
    pi_digits = DigitsOf("pi").generate(n)
    e_digits = DigitsOf("e").generate(n)
    phi_digits = DigitsOf("phi").generate(n)

    # All three share a steady eighth-note pulse
    uniform_rhythm = [0.5] * n
    durations = to_rhythm(uniform_rhythm, base_duration=1.0, strategy="proportional")

    pi_pitches = to_pitch(pi_digits, scale="C_major", octave_range=(4, 5), strategy="modular")
    e_pitches = to_pitch(e_digits, scale="C_major", octave_range=(3, 4), strategy="modular")
    phi_pitches = to_pitch(phi_digits, scale="C_major", octave_range=(5, 6), strategy="modular")

    pi_vel = to_dynamics(pi_digits, velocity_range=(65, 95), strategy="normalize")
    e_vel = to_dynamics(e_digits, velocity_range=(55, 85), strategy="normalize")
    phi_vel = to_dynamics(phi_digits, velocity_range=(60, 90), strategy="normalize")

    piece = Composition(tempo=120, title="Constants Race — Pi vs E vs Phi")
    piece.add_voice("pi", pi_pitches, durations, pi_vel, instrument="piano")
    piece.add_voice("e", e_pitches, durations, e_vel, instrument="vibraphone", channel=1)
    piece.add_voice("phi", phi_pitches, durations, phi_vel, instrument="celesta", channel=2)

    out = os.path.join(OUTPUT_DIR, "constants_race.mid")
    piece.render(out)
    print(f"  Digits:   {n} per constant")
    print(f"  Voices:   pi (piano, mid), e (vibraphone, low), phi (celesta, high)")
    print(f"  Mapping:  digit 0-9 -> scale degree (C major), same rhythm")
    print(f"  Listen:   three melodies that share a pulse but wander apart.")
    print(f"            Moments of unison reveal shared digit subsequences.")
    print(f"  Output:   {out}")
    return out


def heartbeat_sonification():
    """Simulated heart rate variability as rhythm.

    Inter-beat intervals (IBI) become note-onset spacing. The two
    overlaid sine waves mimic respiratory sinus arrhythmia (breathing
    modulates heart rate) and a slower autonomic oscillation. A
    bass drum marks each beat; a higher tone plays the IBI value
    as pitch, so the listener hears tempo AND pitch shift together.
    """
    print("\n=== 4. Heartbeat / HRV Sonification ===")

    # Simulate 75 heartbeats (~60 seconds at ~75 bpm)
    hrv_ms = [800 + 50 * math.sin(0.1 * i) + 20 * math.sin(0.25 * i) for i in range(75)]

    n = len(hrv_ms)
    pattern = DataPattern(hrv_ms, name="heart_rate_variability")
    values = pattern.generate(n)

    # Rhythm: IBI in ms -> beats (at 120 bpm, 1 beat = 500ms)
    ibi_beats = [v / 500.0 for v in values]
    durations = to_rhythm(ibi_beats, base_duration=1.0, strategy="proportional")

    # Pitch: IBI mapped to scale — slower beats = lower, faster = higher
    pitches = to_pitch(values, scale="A_minor", octave_range=(3, 5), strategy="normalize")
    dynamics = to_dynamics(values, velocity_range=(60, 100), strategy="normalize")

    piece = Composition(tempo=120, title="Pulse — Heart Rate Variability")

    # Melodic voice tracks pitch changes
    piece.add_voice("hrv_melody", pitches, durations, dynamics, instrument="piano")

    # Percussive heartbeat on every onset (steady kick)
    kick_pitches = [36] * n  # bass drum GM note
    kick_vel = [90] * n
    piece.add_voice("heartbeat", kick_pitches, durations, kick_vel, instrument=0, channel=9)

    out = os.path.join(OUTPUT_DIR, "heartbeat_sonification.mid")
    piece.render(out)
    print(f"  Beats:    {n} simulated heartbeats (~60 seconds)")
    print(f"  IBI range: {min(hrv_ms):.0f}-{max(hrv_ms):.0f} ms")
    print(f"  Mapping:  IBI -> inter-onset time AND pitch (A minor)")
    print(f"  Listen:   a breathing rhythm — tempo speeds up and slows down")
    print(f"            with two overlaid oscillations. Pitch rises when the")
    print(f"            heart beats faster (shorter IBI = higher note).")
    print(f"  Output:   {out}")
    return out


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Sacred Composer — Data Sonification Examples")
    print("=" * 50)

    climate_sonification()
    fibonacci_sonification()
    constants_race()
    heartbeat_sonification()

    print("\n" + "=" * 50)
    print(f"All MIDI files written to: {OUTPUT_DIR}")
    print("Open them in any MIDI player or DAW to listen.")
