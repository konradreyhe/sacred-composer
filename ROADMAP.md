# Sacred Composer — Master Enhancement Roadmap

> Compiled from **28 parallel deep-research agents** covering music theory, mathematics, psychoacoustics, AI/ML, orchestration, world music, synthesis, visualization, live performance, education, distribution, blockchain, therapy, installations, competitions, history, sonification, and social features.

---

## The Vision

Sacred Composer sits at a unique intersection that **no other tool occupies**: deterministic, GPU-free, traceable, music-theory-aware composition from mathematical patterns. The 2,500-year lineage from Pythagoras → Guido → Kircher → Mozart → Hiller → Xenakis → Cage → Nørgård leads directly here.

**Current state**: 86.5/100 evaluation score, 12 patterns, constraint-aware voice leading, MIDI/LilyPond/WAV output, orchestration engine, psychoacoustics module.

---

## Tier 0: Already Built (by research agents during this session)

- `orchestration.py` — 14 instrument profiles, Orchidée-inspired timbre matching, orchestral WAV renderer (`.orch.wav`)
- `psychoacoustics.py` — Sethares dissonance, frisson triggers, groove templates, earworm scoring, peak-end rule
- Japanese scales (in_sen, yo, miyako_bushi, hirajoshi, kumoi, iwato) and Indian ragas (bhairav, yaman, todi, malkauns) in constants.py

---

## Tier 1: Immediate Wins (hours-days)

### 1.1 NumPy-Vectorize WAV Renderer (100-200x speedup)
Replace sample-by-sample loops with vectorized arrays. The entire note becomes 3 lines:
```python
t = np.arange(n_samples) / sample_rate
envelope = vectorized_adsr(t, duration)
signal = sum(amp * np.sin(2*pi*freq*h*t) for h, amp in timbre)
```
**Source**: Codebase audit, Synthesis research

### 1.2 Karplus-Strong Plucked Strings
8 lines of Python for remarkably realistic plucked strings. Add FM synthesis for bells/brass (2 sin() calls per buffer).
**Source**: Synthesis research

### 1.3 Combination Tone Bass Generator
`bass_freq = abs(f1 - f2)` from melody note pairs. Physics-grounded bass that the ear already "hears."
**Source**: Spectral/Microtonal research

### 1.4 Five New Pattern Generators
| Pattern | Musical Use | Lines of Code |
|---------|------------|---------------|
| Mandelbrot boundary walk | Non-repeating pitch | ~20 |
| Rössler attractor | Melody contour (simpler than Lorenz) | ~15 |
| Cantor set rhythm | Fractal silence/sparse meditation | ~10 |
| Zipf distribution | Natural tonal hierarchy | ~10 |
| Planetary polyrhythm | Phasing rhythmic cycles | ~5 (just ratios) |
**Source**: Novel Pattern Sources research

### 1.5 Historical Pattern Generators
| Pattern | Origin | Musical Use |
|---------|--------|------------|
| TextToMelody | Guido d'Arezzo (1026) | Any text → melody via vowel mapping |
| ThueMorse | Tom Johnson (1982) | Zero-autocorrelation rhythm |
| IChing | John Cage (1951) | Structured randomness (64 hexagrams) |
**Source**: Historical Algorithms research

### 1.6 Fix Critical Bugs
- `constraints.py:404` — hardcoded range 60-79 (parameterize)
- `core.py:262` — float equality (use epsilon)
- `constants.py` — add input validation to `parse_scale()`
**Source**: Codebase audit

### 1.7 FluidSynth Audio Upgrade
`pyfluidsynth` + FluidR3_GM SoundFont → near-professional audio, zero ML.
**Source**: Output/Distribution research

---

## Tier 2: Score-Boosting → 95+ (1-2 weeks)

### 2.1 Bayesian Parameter Optimization (Optuna)
Two-phase: fast proxy model (GBR on composition features, <1ms) for exploration → real evaluation only on top 20 candidates. 500 trials in minutes.
```python
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=500)
```
**Source**: AI Music Analysis research

### 2.2 Genetic Algorithm (DEAP)
Evolve `(pattern, seed, key, tempo)` chromosomes. Fitness = evaluation score. Population 50, 10-20 generations. Refactor existing `best_of_n.py`.
**Source**: AI/ML research

### 2.3 Harmony Engine
Chord grammar as weighted state machine with corpus-derived transition probabilities. Chord-first composition: melody = chord tones on strong beats, passing tones on weak. Pattern-driven harmony: Fibonacci→harmonic rhythm, LogisticMap→stability, GoldenSpiral→modulation.
**Source**: Harmony research

### 2.4 Developing Variation (Schoenberg)
Augmentation, diminution, intervallic expansion, fragmentation, liquidation. Track "variation distance" to stay in evaluator sweet spot. Fixes repetition_variation (72.4→95+).
**Source**: Advanced Music Theory research

### 2.5 Neo-Riemannian Transitions
PLR operations on Tonnetz graph. BFS shortest path for smooth modulations. Fixes transition_motivation (66.7→95+).
**Source**: Advanced Music Theory research

### 2.6 Lerdahl Tension Model
`T(t) = hierarchical_dist + dissonance + spiral_dist`. Fit target curve per form section. Fixes tension_arc (77.2→95+).
**Source**: Advanced Music Theory research

### 2.7 OR-Tools Constraint Solver
Replace hand-rolled constraint passes with declarative CP-SAT. Counterpoint rules as constraints, solver finds valid solutions in milliseconds.
**Source**: Generative Algorithms research

### 2.8 Comprehensive Test Suite
50+ pytest tests: patterns, mappers, constraints, core, rendering, performance benchmarks.
**Source**: Codebase audit

---

## Tier 3: Platform Plays (2-4 weeks)

### 3.1 Remotion Sacred Geometry Visualization
`to_visualization_json()` → Remotion React project:
- PianoRoll (scrolling colored bars synced to audio)
- Flower of Life (19 circles pulsing with notes)
- Fibonacci spiral as melodic path
- Cymatics (Chladni figures changing with pitch)
- Lissajous curves from harmony
- Tonnetz on a torus (PLR animated)
- Cellular automata as circular mandalas
**Source**: Remotion + Sacred Geometry research

### 3.2 Publication-Ready Notation
Auto-clef, velocity→dynamics, duration→articulations, slur detection, grand staff, orchestral grouping, part extraction. MusicXML via music21. Total: 1 working day.
**Source**: Notation research

### 3.3 FastAPI Composition Service
`POST /compose` → MIDI/WAV/PDF. Target: meditation apps, game studios, hold music. Freemium: 10 free/month, $29/mo pro.
**Source**: Output/Distribution research

### 3.4 Live Coding REPL
IPython + `python-rtmidi` + hot-reload. TidalCycles-like experience for Sacred Composer.
**Source**: Live Performance research

### 3.5 Adaptive Game Music Engine
`AdaptiveComposer` with vertical layering (enable/disable voices by game state) + horizontal re-sequencing (switch sections at boundaries). OSC/MIDI parameter mapping: danger→LogisticMap r, biome→scale, health→dissonance. **No open-source competitor exists.**
**Source**: Procedural Game/Film research

### 3.6 Consciousness State Presets
| State | Tempo | Hz | Scale | Pattern |
|-------|-------|-----|-------|---------|
| Deep sleep | 50 | 2Hz iso | Pentatonic minor | PinkNoise |
| Meditation | 60 | 6Hz | Bhairav/Phrygian | GoldenSpiral |
| Relaxation | 66 | 10Hz bin | Major/Lydian | Fibonacci |
| Flow/study | 68 | — | Pentatonic major | LogisticMap(3.2) |
| Focus | 80 | 40Hz | Dorian | InfinitySeries |
| Shamanic | 240=4Hz | 4.5Hz | Root drone | Euclidean(7,8) |
**Source**: Music & Consciousness research

### 3.7 Spotify Distribution
DistroKid $22/year. Human authorship via pattern selection. Sleep/focus playlists = massive streaming market.
**Source**: Output/Distribution research

---

## Tier 4: Revenue & Impact (1-3 months)

### 4.1 Music Therapy Engine
ISO principle = LogisticMap r-sweep (chaos→calm). Parkinson's RAS = Euclidean(4,4) + PinkNoise. Sleep = fading drone. Biometric-adaptive via smartwatch HR/GSR. Market: **$6.68B by 2030**. B2B licensing to wellness apps.
**Source**: Music Therapy research

### 4.2 Educational Platform
12-module "Music from Mathematics" course. Streamlit playground + Jupyter notebooks + YouTube channel (Vi Hart niche is **open**). Revenue: $500-2K/month year 1. **BRIDGES 2026 conference paper (Galway, Aug 5-8, deadline Feb 1).**
**Source**: Education research

### 4.3 Generative On-Chain Music
Art Blocks model: 32 bytes per composition on Base L2 (<$0.01/mint). **No one has shipped this.** Generative player: wallet → unique composition, free to listen, pay to own.
**Source**: Blockchain research

### 4.4 Multi-Sensory Installation
OSC bridge → TouchDesigner visuals + DMX lighting + Arduino kinetic sculpture + cymatics plate. Budget: $5-8K proof of concept. Venues: Ars Electronica, ZKM, MUTEK. Funding: Musikfonds (up to 50K EUR).
**Source**: Installation research

### 4.5 Sheet Music Marketplace
Volume play: 100 generated arrangements at $5 avg on MusicNotes.com. Pipeline: Sacred Composer → LilyPond → PDF.
**Source**: Notation research

---

## Tier 5: Ambitious Frontiers (3-12 months)

### 5.1 World Music Systems
Indian raga grammar (arohana/avarohana, vadi/samvadi, gamakas). Arabic maqam (24-TET via pitch bend, jin substitution). Gamelan (slendro/pelog, colotomic structure). West African polyrhythm (timeline patterns). Japanese jo-ha-kyu form. Balinese kotekan (interlocking parts).
**Source**: World Music research

### 5.2 Spectral Interpolation Engine
Grisey-style timbral morphing between two spectra. Partials interpolate independently. Spectral envelope as formal structure.
**Source**: Spectral/Microtonal research

### 5.3 Data Sonification Framework
Climate (NASA GISS temperature → melody), financial (VIX → dissonance), astronomical (pulsar timing → polyrhythm, gravitational wave chirps → glissando), biosignal (EEG bands → multi-layer rhythm). `DataPattern` class wraps any `list[float]`.
**Source**: Data Sonification research

### 5.4 Interactive Web App
FastAPI + WebSocket + Tone.js. Drag patterns onto parameters, hear instantly. Or Pyodide (Python in WASM) for zero-backend.
**Source**: Live Performance research

### 5.5 Social/Multiplayer Composition
Discord bot (`/compose D_minor fibonacci 72bpm`). Multiplayer rooms (each user controls one voice). Competitive leaderboard (highest eval score wins). Musical genetics (breed compositions by crossing parameters).
**Source**: Social/Collaborative research

### 5.6 Deep Math Structures
Voice-leading orbifolds (Tymoczko), maximally even scales for any N-in-M, Pisano periods, Feigenbaum bifurcation as form, Haar wavelet multi-resolution composition, group theory (D12 on pitch classes), Xenakis sieve theory scales.
**Source**: Deep Math research

### 5.7 System Merge
Unify composer.py + sacred_composer/ with shared voice-leading, evaluation, and orchestration. Long-term: sacred_composer becomes the primary engine.
**Source**: Codebase audit

---

## Competition & Conference Calendar

| Event | Date | Fit |
|-------|------|-----|
| **BRIDGES 2026** (Galway) | Aug 5-8, 2026 | Perfect — math+art+music |
| **Reply AI Music Contest** | Jul 3-5, 2026 | Live AI performance |
| **AIMC 2026** | Sep 16-18, 2026 | AI music creativity |
| **ISMIR 2026** (Abu Dhabi) | Nov 8-12, 2026 | Evaluation framework paper |

## Market Opportunities

| Market | Size | Sacred Composer Angle |
|--------|------|----------------------|
| Music Therapy | $6.68B by 2030 | ISO principle engine, Parkinson's RAS |
| Wellness Streaming | $100K+/year per app | Infinite non-repeating calm/sleep/focus music |
| Game Audio Middleware | $500-5K/title | Adaptive procedural engine (no competitor) |
| Sheet Music | $3-15/arrangement | Volume generation pipeline |
| Education | $500-2K/mo | "Music from Mathematics" (underserved niche) |
| Generative Art/NFT | $5K-100K/drop | On-chain deterministic music (whitespace) |

---

## Competitive Positioning

Sacred Composer is the **only tool** that is simultaneously:
1. **Deterministic** — every note traceable to a mathematical pattern
2. **GPU-free** — runs on any hardware, no training data
3. **Music-theory-aware** — voice leading, harmony, counterpoint constraints
4. **Evaluation-equipped** — built-in 100-point scoring framework
5. **Multi-format output** — MIDI, LilyPond, WAV, orchestral WAV, MusicXML
6. **Open-source Python** — hackable, extensible, embeddable

No competing tool (Magenta, MusicGen, AIVA, TidalCycles, Sonic Pi, SuperCollider) has all six.

---

*Generated 2026-04-02 from 28 parallel research agents. Total research tokens: ~500K+.*
*The through-line from Pythagoras to Sacred Composer: music is pattern, constrained by rules, rendered as sound.*
