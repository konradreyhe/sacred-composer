"""Sacred Composer V2 Showcase — 8 compositions demonstrating all capabilities.
Generates MIDI files for each piece and prints a summary table.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sacred_composer import (
    FibonacciSequence, HarmonicSeries, InfinitySeries,
    EuclideanRhythm, CellularAutomata, PinkNoise,
    GoldenSpiral, LorenzAttractor, DigitsOf,
    SternBrocot, LogisticMap, Lindenmayer,
    MandelbrotBoundary, RosslerAttractor, CantorSet,
    ZipfDistribution, TextToMelody,
    to_pitch, to_rhythm, to_dynamics,
    Composition, CompositionBuilder, HarmonicEngine,
    Raga, RAGA_PRESETS, tala_pattern,
    gamelan_to_midi, colotomic_pattern, balungan_elaborate,
    maqam_sayr, overtone_melody, KHOOMEI_PATTERNS,
    cross_rhythm, polyrhythmic_texture,
    JAPANESE_SCALES, jo_ha_kyu_curve, apply_ma, kotekan_split,
)

OUT = os.path.join(os.path.dirname(__file__))
results = []

def report(piece, filename):
    info = piece.info()
    print(f"  Title:    {info['title']}")
    print(f"  Voices:   {info['voices']}  |  Notes: {info['total_notes']}  |  "
          f"Duration: {info['duration_seconds']:.1f}s ({info['duration_beats']:.0f} beats @ {info['tempo']} bpm)")
    print(f"  File:     {filename}\n")
    results.append(info | {"file": os.path.basename(filename)})

def heading(num, title):
    print("=" * 60)
    print(f"{num}. {title}")
    print("=" * 60)

# --- 1. Harmony Cathedral --- CompositionBuilder + .harmony() mode, D minor
heading(1, "Harmony Cathedral")
piece1 = (
    CompositionBuilder(key="D_minor", tempo=66, bars=32, title="Harmony Cathedral")
    .harmony(n_chords=16, seed=7)
    .form(pattern="fibonacci", n_sections=4, labels=["Introit", "Nave", "Apse", "Coda"])
    .melody(pattern="infinity_series", instrument="violin", octave_range=(4, 5), seed=3)
    .bass(pattern="harmonic_series", instrument="cello", octave_range=(2, 3), seed=10)
    .inner_voice(pattern="golden_spiral", instrument="viola", octave_range=(3, 4), seed=20)
    .drone(instrument="contrabass", velocity=50)
    .build()
)
report(piece1, piece1.render(os.path.join(OUT, "showcase2_harmony_cathedral.mid")))

# --- 2. Mandelbrot Meditation --- fractal boundary walk + Cantor set rhythm
heading(2, "Mandelbrot Meditation")
n2 = 80
pitches2 = to_pitch(MandelbrotBoundary(max_iter=150, perturbation=0.015).generate(n2),
                     scale="A_minor", octave_range=(3, 5), strategy="normalize")
durations2 = to_rhythm(CantorSet(depth=4).generate(n2), base_duration=1.5, strategy="binary")
dynamics2 = to_dynamics(PinkNoise(sigma=1.2, seed=5).generate(n2), velocity_range=(40, 85))
piece2 = Composition(tempo=52, title="Mandelbrot Meditation")
piece2.add_voice("fractal_melody", pitches2, durations2, dynamics2, instrument="celesta")
fib_bass = FibonacciSequence().generate(20)
piece2.add_voice("fib_bass", to_pitch(fib_bass, scale="A_minor", octave_range=(2, 3),
                 strategy="modular"), [4.0] * 20, instrument="contrabass")
report(piece2, piece2.render(os.path.join(OUT, "showcase2_mandelbrot_meditation.mid")))

# --- 3. Rossler Waltz --- attractor melody in 3/4 + golden spiral bass
heading(3, "Rossler Waltz")
n3 = 96
pitches3 = to_pitch(RosslerAttractor(a=0.2, b=0.2, c=5.7, dt=0.05).generate(n3),
                     scale="G_major", octave_range=(4, 5), strategy="normalize")
waltz_durs = [d for _ in range(n3 // 3) for d in (1.5, 0.75, 0.75)]
dynamics3 = to_dynamics(PinkNoise(sigma=1.0, seed=12).generate(n3), velocity_range=(55, 100))
piece3 = Composition(tempo=144, title="Rossler Waltz")
piece3.add_voice("rossler_melody", pitches3, waltz_durs[:n3], dynamics3, instrument="violin")
gold_vals = GoldenSpiral(start=10.0).generate(n3 // 3)
bass3_p = to_pitch(gold_vals, scale="G_major", octave_range=(2, 3), strategy="normalize")
piece3.add_voice("golden_bass", bass3_p, [3.0] * len(bass3_p), instrument="cello")
report(piece3, piece3.render(os.path.join(OUT, "showcase2_rossler_waltz.mid")))

# --- 4. Sacred Text --- TextToMelody from prose
heading(4, "Sacred Text")
n4 = 64
text_vals = TextToMelody("in the beginning was the word and the word was music").generate(n4)
pitches4 = to_pitch(text_vals, scale="Eb_major", octave_range=(4, 5), strategy="modular")
durations4 = to_rhythm(EuclideanRhythm(5, 8).generate(n4), base_duration=0.75, strategy="binary")
dynamics4 = to_dynamics(PinkNoise(sigma=1.0, seed=99).generate(n4), velocity_range=(50, 90))
piece4 = Composition(tempo=80, title="Sacred Text")
piece4.add_voice("text_melody", pitches4, durations4, dynamics4, instrument="choir")
stern_vals = SternBrocot(depth=3).generate(16)
piece4.add_voice("stern_pad", to_pitch(stern_vals, scale="Eb_major", octave_range=(3, 4),
                 strategy="normalize"), [4.0] * 16, instrument="strings")
report(piece4, piece4.render(os.path.join(OUT, "showcase2_sacred_text.mid")))

# --- 5. Zipf Hierarchy --- natural tonal hierarchy in C major
heading(5, "Zipf Hierarchy")
n5 = 96
pitches5 = to_pitch(ZipfDistribution(n_categories=7, exponent=1.2, seed=33).generate(n5),
                     scale="C_major", octave_range=(4, 5), strategy="modular")
durations5 = to_rhythm(LogisticMap(r=3.82, x0=0.4).generate(n5),
                        base_duration=0.5, strategy="proportional")
dynamics5 = to_dynamics(PinkNoise(sigma=1.5, seed=77).generate(n5), velocity_range=(45, 95))
piece5 = Composition(tempo=108, title="Zipf Hierarchy")
piece5.add_voice("zipf_melody", pitches5, durations5, dynamics5, instrument="piano")
ca_vals = CellularAutomata(rule=110, width=12).generate(n5 // 2)
piece5.add_voice("ca_inner", to_pitch(ca_vals, scale="C_major", octave_range=(3, 4),
                 strategy="modular"), [1.0] * len(ca_vals), instrument="vibraphone")
report(piece5, piece5.render(os.path.join(OUT, "showcase2_zipf_hierarchy.mid")))

# --- 6. Raga Dawn --- Bhairav raga, Lorenz contour, Adi tala, morning mood
heading(6, "Raga Dawn")
bhairav = RAGA_PRESETS["bhairav"]
n6 = 72
raga_pitches = bhairav.generate_melody(LorenzAttractor(dt=0.01).generate(n6), root=60, octave_range=2)
raga_micro = bhairav.apply_gamakas(raga_pitches)
tala_durs = (tala_pattern("adi", n_cycles=6) * 3)[:n6]
jhk = jo_ha_kyu_curve(n6)
dawn_dyn = [max(30, min(110, int(40 + 50 * v / 2.0))) for v in jhk]
piece6 = Composition(tempo=60, title="Raga Dawn")
piece6.add_voice("bhairav_melody", raga_micro, tala_durs, dawn_dyn,
                 instrument="violin", microtonal=True)
drone_len = float(sum(abs(d) for d in tala_durs))
piece6.add_drone("sa_drone", pitch=60, total_beats=drone_len, velocity=45, instrument="strings")
piece6.add_drone("pa_drone", pitch=67, total_beats=drone_len, velocity=40, instrument="strings")
report(piece6, piece6.render(os.path.join(OUT, "showcase2_raga_dawn.mid")))

# --- 7. Gamelan Dreams --- slendro tuning, colotomic structure, pi-derived balungan
heading(7, "Gamelan Dreams")
slendro = gamelan_to_midi("slendro_solo", root_midi=60, octaves=2)
col = colotomic_pattern("lancaran", n_gongans=4)
n7 = 64
pi_vals = DigitsOf("pi").generate(n7)
balungan = [slendro[int(v) % len(slendro)] for v in pi_vals]
peking = balungan_elaborate([int(round(p)) for p in balungan], style="peking")
gender = balungan_elaborate([int(round(p)) for p in balungan], style="gender")
piece7 = Composition(tempo=92, title="Gamelan Dreams")
piece7.add_voice("peking", [float(p) for p in peking], [0.5] * len(peking),
                 instrument="vibraphone", microtonal=True)
piece7.add_voice("balungan", balungan, [1.0] * len(balungan),
                 instrument="marimba", microtonal=True)
piece7.add_voice("gender", [float(p) for p in gender], [2.0] * len(gender),
                 instrument="celesta", microtonal=True)
# Gong strokes from colotomic pattern
gong_p, gong_d, gong_v, prev = [], [], [], 0
for beat in col.get("gong", []):
    if beat > prev:
        gong_p.append(-1); gong_d.append(float(beat - prev)); gong_v.append(0)
    gong_p.append(48); gong_d.append(2.0); gong_v.append(100)
    prev = beat + 2
piece7.add_voice("gong", gong_p, gong_d, gong_v, instrument="vibraphone")
report(piece7, piece7.render(os.path.join(OUT, "showcase2_gamelan_dreams.mid")))

# --- 8. Everything Piece --- all 17 patterns + harmony engine, maximum complexity
heading(8, "Everything Piece")
N, KEY = 64, "F_minor"
piece8 = Composition(tempo=96, title="Everything Piece")
# Harmony engine foundation
engine = HarmonicEngine(key=KEY, n_chords=16, seed=42, beats_per_chord=4)
mel_p, mel_d = engine.melody(octave=5)
bass_p, bass_d = engine.bass(octave=2)
piece8.add_voice("harmony_melody", mel_p, mel_d, instrument="violin")
piece8.add_voice("harmony_bass", bass_p, bass_d, instrument="cello")
# Helper: add a pattern voice in one line
def pv(name, vals, inst, octs=(3, 4), strat="modular", durs=None, vel=None):
    p = to_pitch(vals, scale=KEY, octave_range=octs, strategy=strat)
    d = durs if durs else [1.0] * len(p)
    piece8.add_voice(name, p, d[:len(p)], vel, instrument=inst)
# 1-Fibonacci  2-HarmonicSeries  3-InfinitySeries  4-Euclidean  5-CellularAutomata
pv("fibonacci", FibonacciSequence().generate(N), "harp")
hs = HarmonicSeries("F2").as_chord(n=6, quantize=True)
piece8.add_voice("harmonic_series", hs, [float(N)] * len(hs), [50] * len(hs), instrument="organ")
pv("infinity", InfinitySeries(seed=2).generate(N), "flute", octs=(4, 5),
   durs=to_rhythm(EuclideanRhythm(7, 12).generate(N), base_duration=0.5, strategy="binary"))
euc = EuclideanRhythm(5, 8).generate(N)
pv("euclidean", euc, "marimba", octs=(4, 4),
   durs=to_rhythm(euc, base_duration=0.5, strategy="binary"))
pv("cellular", CellularAutomata(rule=90, width=8).generate(N), "vibraphone", durs=[0.5] * N)
# 6-PinkNoise (as dynamics for Lorenz)  7-GoldenSpiral  8-Lorenz
pink = PinkNoise(sigma=2.0, seed=42).generate(N)
pv("golden_spiral", GoldenSpiral().generate(N), "clarinet", strat="normalize")
lor = LorenzAttractor(dt=0.01).generate(N)
piece8.add_voice("lorenz", to_pitch(lor, scale=KEY, octave_range=(4, 5), strategy="normalize"),
                 [0.75] * N, to_dynamics(pink, velocity_range=(45, 100)), instrument="oboe")
# 9-DigitsOf  10-SternBrocot  11-LogisticMap  12-Lindenmayer
pv("digits_e", DigitsOf("e").generate(N), "guitar", durs=[1.5] * N, vel=[40] * N)
sb = SternBrocot(depth=4).generate(N)
pv("stern_brocot", sb, "recorder", strat="normalize",
   durs=to_rhythm(sb, base_duration=0.75, strategy="ratio"))
pv("logistic", LogisticMap(r_start=3.2, r_end=3.99, x0=0.5).generate(N), "trumpet",
   octs=(4, 5), strat="normalize", durs=[0.5] * N)
pv("lindenmayer", Lindenmayer(axiom="A", rules={"A": "AB", "B": "A"}).generate(N),
   "bassoon", durs=[0.75] * N)
# 13-Mandelbrot  14-Rossler  15-Cantor+16-Zipf  17-TextToMelody
pv("mandelbrot", MandelbrotBoundary(max_iter=120, perturbation=0.02).generate(N),
   "piano", octs=(4, 5), strat="normalize", durs=[0.5] * N, vel=[55] * N)
pv("rossler", RosslerAttractor(dt=0.04).generate(N), "horn",
   octs=(4, 5), strat="normalize", durs=[0.75] * N)
cant_d = to_rhythm(CantorSet(depth=3).generate(N), base_duration=0.75, strategy="binary")
pv("zipf_cantor", ZipfDistribution(n_categories=7, exponent=1.0, seed=88).generate(N),
   "viola", durs=cant_d)
pv("text_melody", TextToMelody(
   "all seventeen sacred patterns sing together in one piece").generate(N),
   "choir", octs=(4, 5), vel=[50] * N)
report(piece8, piece8.render(os.path.join(OUT, "showcase2_everything_piece.mid")))

# --- Summary Table ---
print("=" * 78)
print("SACRED COMPOSER V2 SHOWCASE -- SUMMARY")
print("=" * 78)
print(f"{'#':<3} {'Title':<28} {'Voices':>6} {'Notes':>6} {'Dur(s)':>7} {'Tempo':>5}")
print("-" * 78)
for i, r in enumerate(results, 1):
    print(f"{i:<3} {r['title']:<28} {r['voices']:>6} {r['total_notes']:>6} "
          f"{r['duration_seconds']:>7.1f} {r['tempo']:>5}")
print("-" * 78)
tn = sum(r["total_notes"] for r in results)
td = sum(r["duration_seconds"] for r in results)
print(f"{'':>3} {'TOTAL':<28} {'':>6} {tn:>6} {td:>7.1f}")
print(f"\nAll {len(results)} MIDI files written to: {OUT}")
print("Patterns used: all 17 generators + HarmonicEngine + World Music systems")
