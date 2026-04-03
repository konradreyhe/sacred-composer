"""Sacred Patterns — 10-track album for Spotify distribution.

Each track is driven by a different mathematical pattern, rendered to
MIDI + WAV.  Target: 2-4 minutes per track, ~30 min total runtime.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sacred_composer import (
    Composition, CompositionBuilder,
    FibonacciSequence, HarmonicSeries, InfinitySeries,
    GoldenSpiral, LorenzAttractor, CellularAutomata,
    MandelbrotBoundary, CantorSet, PinkNoise, PlanetaryRhythm,
    EuclideanRhythm, TextToMelody, RosslerAttractor,
    to_pitch, to_rhythm, to_dynamics,
)

OUT = os.path.join(os.path.dirname(__file__), "spotify_album")
os.makedirs(OUT, exist_ok=True)

results = []

def render_track(num, piece):
    """Render to MIDI + WAV, print info, collect stats."""
    tag = f"{num:02d}"
    safe = piece.title.lower().replace(" ", "_").replace("'", "")
    mid = os.path.join(OUT, f"{tag}_{safe}.mid")
    wav = os.path.join(OUT, f"{tag}_{safe}.wav")
    piece.render(mid)
    t0 = time.time()
    piece.render(wav)
    elapsed = time.time() - t0
    info = piece.info()
    dur = info["duration_seconds"]
    print(f"  [{num:2d}] {info['title']:<24s}  "
          f"{dur/60:.1f}min ({info['total_notes']:4d} notes, "
          f"{info['voices']} voices)  WAV {elapsed:.1f}s")
    results.append(info)

# ─── Helper: build a manual Composition with multiple voices ───
def manual(title, tempo, key, voices, bars_hint=None):
    """Build a Composition from a list of (name, pitches, durs, vels, instr) tuples."""
    piece = Composition(tempo=tempo, title=title)
    for name, pitches, durs, vels, instr in voices:
        piece.add_voice(name, pitches, durs, vels, instrument=instr)
    return piece

def n_for(tempo, minutes, base_dur):
    """Estimate note count for a target duration."""
    beats = tempo * minutes
    return int(beats / base_dur) + 8

print("=" * 64)
print("  SACRED PATTERNS — Album Generation")
print("=" * 64, "\n")

# ── 1. Fibonacci Garden ── gentle, F major, 66 BPM, flute + cello
n1 = n_for(66, 3.0, 0.75)
piece1 = (
    CompositionBuilder(key="F_major", tempo=66, bars=36, title="Fibonacci Garden")
    .form(pattern="fibonacci", n_sections=5)
    .melody(pattern="fibonacci", instrument="flute", octave_range=(4, 5),
            rhythm_pattern="euclidean_5_8", base_duration=0.75, seed=1)
    .bass(pattern="harmonic_series", instrument="cello", octave_range=(2, 3),
          base_duration=3.0, seed=10)
    .inner_voice(pattern="golden_spiral", instrument="harp", octave_range=(3, 4),
                 base_duration=1.5, seed=5)
    .build()
)
render_track(1, piece1)

# ── 2. Lorenz Butterfly ── dramatic, D minor, 96 BPM, violin + piano
n2 = n_for(96, 2.5, 0.5)
lorenz = LorenzAttractor(dt=0.01).generate(n2)
p2m = to_pitch(lorenz, scale="D_minor", octave_range=(4, 5), strategy="normalize")
d2m = to_rhythm(EuclideanRhythm(7, 8).generate(n2), base_duration=0.5, strategy="binary")
v2m = to_dynamics(PinkNoise(sigma=1.5, seed=20).generate(n2), velocity_range=(60, 110))
p2b = to_pitch(FibonacciSequence().generate(n2 // 3), scale="D_minor",
               octave_range=(2, 3), strategy="modular")
d2b = [2.0] * (n2 // 3)
piece2 = manual("Lorenz Butterfly", 96, "D_minor", [
    ("lorenz_violin", p2m, d2m, v2m, "violin"),
    ("fib_piano", p2b, d2b, None, "piano"),
])
render_track(2, piece2)

# ── 3. Cellular Cathedral ── spacious, Rule 110, C minor, 54 BPM, organ + strings
n3 = n_for(54, 3.5, 1.5)
ca = CellularAutomata(rule=110, width=16).generate(n3)
p3m = to_pitch(ca, scale="C_minor", octave_range=(3, 5), strategy="modular")
d3m = to_rhythm(EuclideanRhythm(3, 8).generate(n3), base_duration=1.5, strategy="binary")
v3m = to_dynamics(PinkNoise(sigma=1.0, seed=30).generate(n3), velocity_range=(35, 75))
p3b = to_pitch(HarmonicSeries(55.0).as_chord(n=4, quantize=True) * 20,
               scale="C_minor", octave_range=(2, 3), strategy="modular")[:n3 // 4]
d3b = [4.0] * (n3 // 4)
piece3 = Composition(tempo=54, title="Cellular Cathedral")
piece3.add_voice("ca_organ", p3m, d3m, v3m, instrument="organ")
piece3.add_voice("harmonic_strings", p3b, d3b, instrument="strings")
piece3.add_drone("root_drone", pitch=48, total_beats=float(sum(abs(d) for d in d3m)),
                 velocity=40, instrument="contrabass")
render_track(3, piece3)

# ── 4. Golden Dawn ── uplifting, golden spiral, G major, 72 BPM, harp + flute
piece4 = (
    CompositionBuilder(key="G_major", tempo=72, bars=38, title="Golden Dawn")
    .form(pattern="golden", n_sections=2)
    .melody(pattern="golden_spiral", instrument="flute", octave_range=(4, 5),
            rhythm_pattern="euclidean_5_8", base_duration=0.75, seed=7)
    .bass(pattern="harmonic_series", instrument="harp", octave_range=(3, 4),
          base_duration=2.0, seed=14)
    .inner_voice(pattern="fibonacci", instrument="strings", octave_range=(3, 4),
                 base_duration=1.0, seed=21)
    .build()
)
render_track(4, piece4)

# ── 5. Infinity Mirror ── hypnotic, A minor, 60 BPM, vibraphone + cello
piece5 = (
    CompositionBuilder(key="A_minor", tempo=60, bars=32, title="Infinity Mirror")
    .melody(pattern="infinity_series", instrument="vibraphone", octave_range=(4, 5),
            rhythm_pattern="euclidean_5_8", base_duration=0.75, seed=42)
    .bass(pattern="harmonic_series", instrument="cello", octave_range=(2, 3),
          base_duration=3.0, seed=11)
    .build()
)
render_track(5, piece5)

# ── 6. Cantor's Silence ── sparse/meditative, Eb major, 48 BPM, piano solo
n6 = n_for(48, 3.0, 2.0)
cantor = CantorSet(depth=4).generate(n6)
p6 = to_pitch(cantor, scale="Eb_major", octave_range=(3, 5), strategy="modular")
d6 = to_rhythm(EuclideanRhythm(3, 8).generate(n6), base_duration=2.0, strategy="binary")
v6 = to_dynamics(PinkNoise(sigma=0.8, seed=60).generate(n6), velocity_range=(25, 65))
piece6 = Composition(tempo=48, title="Cantor's Silence")
piece6.add_voice("cantor_piano", p6, d6, v6, instrument="piano")
render_track(6, piece6)

# ── 7. Planetary Waltz ── playful, Bb major, 132 BPM 3/4, strings
n7 = n_for(132, 2.0, 0.5)
pr = PlanetaryRhythm(planets=["mercury", "venus", "earth", "mars"]).generate(n7)
p7m = to_pitch(pr, scale="Bb_major", octave_range=(4, 5), strategy="normalize")
waltz = [d for _ in range(n7 // 3 + 1) for d in (1.0, 0.5, 0.5)][:n7]
v7m = to_dynamics(PinkNoise(sigma=1.2, seed=70).generate(n7), velocity_range=(55, 100))
p7b = to_pitch(GoldenSpiral(start=5.0).generate(n7 // 3),
               scale="Bb_major", octave_range=(2, 3), strategy="normalize")
piece7 = Composition(tempo=132, title="Planetary Waltz")
piece7.add_voice("planet_violin", p7m, waltz, v7m, instrument="violin")
piece7.add_voice("golden_cello", p7b, [1.5] * (n7 // 3), instrument="cello")
render_track(7, piece7)

# ── 8. Sacred Text ── mysterious, Genesis 1:1, D dorian, 80 BPM, choir + organ
genesis = "In the beginning God created the heaven and the earth"
n8 = n_for(80, 2.5, 0.75)
txt = TextToMelody(genesis).generate(n8)
p8m = to_pitch(txt, scale="D_dorian", octave_range=(4, 5), strategy="modular")
d8m = to_rhythm(EuclideanRhythm(5, 8).generate(n8), base_duration=0.75, strategy="binary")
v8m = to_dynamics(PinkNoise(sigma=1.0, seed=80).generate(n8), velocity_range=(45, 90))
p8b = to_pitch(HarmonicSeries(73.4).as_chord(n=4, quantize=True) * 20,
               scale="D_dorian", octave_range=(2, 3), strategy="modular")[:n8 // 4]
piece8 = Composition(tempo=80, title="Sacred Text")
piece8.add_voice("genesis_choir", p8m, d8m, v8m, instrument="choir")
piece8.add_voice("harmonic_organ", p8b, [4.0] * (n8 // 4), instrument="organ")
piece8.add_drone("root_drone", pitch=50, total_beats=float(sum(abs(d) for d in d8m)),
                 velocity=35, instrument="strings")
render_track(8, piece8)

# ── 9. Mandelbrot Depths ── complex, F# minor, 76 BPM, piano + strings
n9 = n_for(76, 2.5, 0.5)
mb = MandelbrotBoundary(max_iter=200, perturbation=0.012).generate(n9)
p9m = to_pitch(mb, scale="F#_minor", octave_range=(4, 5), strategy="normalize")
d9m = to_rhythm(EuclideanRhythm(7, 12).generate(n9), base_duration=0.5, strategy="binary")
v9m = to_dynamics(PinkNoise(sigma=1.3, seed=90).generate(n9), velocity_range=(50, 100))
p9b = to_pitch(GoldenSpiral(start=3.0).generate(n9 // 3),
               scale="F#_minor", octave_range=(2, 3), strategy="normalize")
piece9 = Composition(tempo=76, title="Mandelbrot Depths")
piece9.add_voice("mandelbrot_piano", p9m, d9m, v9m, instrument="piano")
piece9.add_voice("spiral_strings", p9b, [2.0] * (n9 // 3), instrument="strings")
render_track(9, piece9)

# ── 10. The Everything Piece ── climactic, all patterns, C minor, 88 BPM
piece10 = (
    CompositionBuilder(key="C_minor", tempo=88, bars=24,
                       title="The Everything Piece")
    .harmony(n_chords=16, seed=42)
    .form(pattern="fibonacci", n_sections=5,
          labels=["Genesis", "Growth", "Chaos", "Reflection", "Coda"])
    .melody(pattern="infinity_series", instrument="violin", octave_range=(4, 5),
            rhythm_pattern="euclidean_5_8", base_duration=1.0, seed=0)
    .bass(pattern="harmonic_series", instrument="contrabass", octave_range=(2, 3),
          base_duration=3.0, seed=10)
    .inner_voice(pattern="mandelbrot", instrument="piano", octave_range=(3, 4),
                 base_duration=1.5, seed=20)
    .inner_voice(pattern="golden_spiral", instrument="strings", octave_range=(3, 5),
                 base_duration=2.0, seed=30)
    .inner_voice(pattern="fibonacci", instrument="flute", octave_range=(4, 6),
                 rhythm_pattern="euclidean_3_8", base_duration=1.5, seed=40)
    .build()
)
render_track(10, piece10)

# ─── Album Summary ───
print("\n" + "=" * 64)
print("  ALBUM SUMMARY: Sacred Patterns")
print("=" * 64)
print(f"  {'#':<4} {'Title':<26} {'Dur':>6} {'Notes':>6} {'Voices':>7}")
print("  " + "-" * 53)
total = 0.0
for i, r in enumerate(results, 1):
    dur = r["duration_seconds"]
    total += dur
    print(f"  {i:<4} {r['title']:<26} {dur/60:5.1f}m {r['total_notes']:6d} {r['voices']:7d}")
print("  " + "-" * 53)
print(f"  {'TOTAL':<30} {total/60:5.1f}m")
print(f"\n  Output: {os.path.abspath(OUT)}")
print("=" * 64)
