# GAMEPLAN — Sacred Composer Codebase Health, Consolidation & Evolution

> From the Principles Compliance Audit of 2026-04-02.
> Enhanced 2026-04-03 with findings from 28 parallel deep-research agents covering music theory, mathematics, psychoacoustics, AI/ML, orchestration, world music, synthesis, visualization, live performance, education, distribution, blockchain, therapy, installations, competitions, history, and sonification.
>
> This is the actionable plan to bring the codebase in line with its own PRINCIPLES.md AND evolve it into its full potential.

---

## Current State Snapshot

| Metric | Value |
|--------|-------|
| Total Python lines | ~20,500+ |
| Root-level files | 14 .py files (13,448 lines) |
| sacred_composer/ package | 18 .py files (~7,000+ lines) |
| Largest file | `composer.py` — 4,366 lines (21% of codebase) |
| Functions >50 lines | 36+ across all files |
| Unit test files | 0 |
| Integration test files | 1 (`test_compositions.py`, no assertions) |
| `print()` statements | 447 total (162 in production code) |
| Bare `except` blocks | 10+ (errors silently swallowed) |
| Magic number instances | 60+ (same values hardcoded in multiple files) |
| Evaluation score | 86.5/100 (best), 79.1/100 (5-piece average) |
| Principles compliance | ~40% |
| New modules (built by research agents) | orchestration.py, psychoacoustics.py, world_music.py |

### Two Parallel Systems (Not Connected)

```
System A: composer.py pipeline         System B: sacred_composer/ package
================================       ================================
9-pass compiler (text -> MIDI)          Pattern -> Map -> Combine -> Render
4,366 lines, monolithic                ~7,000 lines, modular
Form/Schema/Harmony/Melody/etc.        Fibonacci/Lorenz/Cellular/etc.
classical_music_gen.py toolkit         constraints.py, mappers.py
evaluation_framework.py (2,359 lines)  evaluate.py (113 lines, stub)
prompt_template_library.py (2,200 l.)  builder.py (451 lines)
SYSTEM_ARCHITECTURE.py (IR defs)       bridge.py (sys.path hack)
                                       orchestration.py (600 lines) [NEW]
                                       psychoacoustics.py [NEW]
                                       world_music.py (460 lines) [NEW]
```

Both systems have their own: form builders, melody generators, constraint systems, MIDI renderers, evaluation logic. They share nothing except a fragile `bridge.py` that uses `sys.path.insert()`.

### Historical Lineage (Context from Research Agent 26)

Sacred Composer's architecture (generate -> map -> combine -> render) is the modern realization of a **2,500-year idea**: Pythagoras (ratios = consonance) -> Guido d'Arezzo (text -> melody, 1026) -> Kircher (constraint-based composition, 1650) -> Mozart (combinatorial fragment assembly, 1787) -> Hiller (random + counterpoint filter, 1957) -> Xenakis (stochastic distribution assignment, 1962) -> Cage (structured randomness, 1951) -> Norgard (self-similar series, 1970). Every innovator discovered the same truth: **the source pattern matters less than the mapping and constraints applied to it.**

### Competitive Position (Context from Research Agent 20)

Sacred Composer is the **only tool** that is simultaneously:
1. **Deterministic** — every note traceable to a mathematical pattern
2. **GPU-free** — runs on any hardware, no training data
3. **Music-theory-aware** — voice leading, harmony, counterpoint constraints
4. **Evaluation-equipped** — built-in 100-point scoring framework
5. **Multi-format output** — MIDI, LilyPond, WAV, orchestral WAV, MusicXML
6. **Open-source Python** — hackable, extensible, embeddable

No competing tool (Magenta [archived Jan 2026], MusicGen, AIVA, TidalCycles, Sonic Pi, SuperCollider) has all six. **No open-source deterministic procedural music engine exists** for game/film adaptive music. This is a genuine market gap.

---

## Phase 1: Stop the Bleeding (1-2 days)

These are quick, mechanical fixes that prevent further debt accumulation.

### 1.1 Fix `.gitignore` — generated files polluting git

**Problem:** `.gitignore` has `output/*.mid` but not `*.mid`. Nine generated MIDI files are tracked in the repo root.

**Action:**
```gitignore
# Add to .gitignore:
*.mid
*.wav
*.mp3
output/
```
Then: `git rm --cached *.mid *.wav` to untrack existing files.

**Principle:** Consistency, 12-Factor (codebase hygiene)

---

### 1.2 Replace `print()` with `logging` in production code

**Problem:** 447 `print()` calls total. Production code (`composer.py`: 110, `render_audio.py`: 52) uses print instead of the logging module. No log levels, no structured output, no way to silence or redirect.

**Action:**
1. Add `import logging; logger = logging.getLogger(__name__)` to each production file
2. Replace `print(f"...")` -> `logger.info(...)` / `logger.debug(...)` / `logger.warning(...)`
3. Leave `print()` in demo/example/showcase files (they're user-facing scripts)

**Files to change:**
- `composer.py` — 110 statements
- `render_audio.py` — 52 statements
- `best_of_n.py` — 16 statements (borderline, it's a CLI tool)
- `sacred_composer/orchestration.py` — new file, set up logging from day 1
- `sacred_composer/psychoacoustics.py` — new file, set up logging from day 1

**Principle:** "Log Everything Important", "No debug code or console.logs"

---

### 1.3 Fix silent error swallowing

**Problem:** 10+ bare `except Exception: pass` blocks hide real failures. When something breaks, there's zero diagnostic output. The psychoacoustics research (Agent 10) showed that subtle numerical errors in consonance calculation or groove timing can silently produce wrong output — these MUST surface as warnings.

**Action:** Add `logger.exception()` or `logger.warning()` to every bare except block:

| File | Lines | Current | Fix |
|------|-------|---------|-----|
| `composer.py` | 2613 | `except Exception: pass` | `logger.warning("...", exc_info=True)` |
| `evaluation_framework.py` | 128, 651, 710, 1218, 1258, 1349, 1856 | bare excepts | Add context-specific warnings |
| `render_audio.py` | 89, 208 | import/subprocess failures hidden | Log which backend failed and why |
| `sacred_composer/evaluate.py` | 69-71 | `os.unlink()` error swallowed | Acceptable for cleanup, but add debug log |
| `sacred_composer/evaluate.py` | 36 | Catches ImportError but not AttributeError | Catch both |

**Principle:** "Fail Fast", "Explicit > Implicit", "No swallowed exceptions"

---

### 1.4 Fix critical bugs identified by codebase audit (Agent 8)

These are bugs, not style issues. They cause incorrect output.

| File:Line | Bug | Fix |
|-----------|-----|-----|
| `constraints.py:404-405` | Hardcoded melody range 60-79 in `_final_leap_recovery`, rejects other voice types | Accept `range_limits` parameter, default from `VOICE_RANGES` |
| `core.py:262` | Float equality `note.pitch_bend != 0.0` — misses tiny bends from rounding | Use `abs(note.pitch_bend) > 1e-6` |
| `constants.py:48-64` | `parse_scale()` raises KeyError on unknown root (e.g. "H"), silently defaults on unknown scale type | Validate input, raise `ValueError` with valid options |
| `constraints.py:215-266` | `add_phrase_endings` accesses `pitches[phrase_end + 2]` but only checks `phrase_end + 1 < len` | Add bounds check for +2 access |
| `mappers.py:42-51` | Empty scale silently returns `[60] * len(values)` | Log warning or raise ValueError |
| `core.py:139-151` | Silent modular cycling when `pitches` and `durations` differ in length | Log warning when lengths differ |

**Principle:** "Fail Fast", "Explicit > Implicit"

---

### 1.5 Remove unused imports

**Action:**
- `evaluation_framework.py` — remove unused `import math`
- `render_audio.py` — remove unused `import math`

**Principle:** YAGNI

---

## Phase 2: Centralize Constants & Shared Infrastructure (2-3 days)

### 2.1 Create a shared constants module

**Problem:** 60+ magic numbers scattered across 10+ files. The golden ratio `0.618` alone appears 18+ times. MIDI constants (`8192`, `16383`, `127`) are raw literals. Velocity ranges, phrase lengths, and step ratios are hardcoded everywhere with inconsistent values. The psychoacoustics module (Agent 10) adds new constants (JND threshold = 10-20ms, critical bandwidth formula coefficients) that must be centralized from the start.

**Action:** Expand `sacred_composer/constants.py` into the shared module for the entire project:

```python
"""Shared constants for the entire MUSIK! project."""

import math

# === Mathematical Constants ===
PHI = (1 + math.sqrt(5)) / 2          # 1.6180339887...
PHI_INVERSE = 1 / PHI                  # 0.6180339887... (golden section)
GOLDEN_ANGLE = 360 / PHI**2            # 137.5077640...
FEIGENBAUM_DELTA = 4.669201609...      # Universal period-doubling constant

# === MIDI Constants ===
MIDI_MAX_PITCH = 127
MIDI_MIN_PITCH = 0
MIDI_MAX_VELOCITY = 127
MIDI_PITCH_BEND_CENTER = 8192
MIDI_PITCH_BEND_RANGE = 4096  # semitones per direction (standard: 2)
MIDI_PITCH_BEND_MAX = 16383
MIDI_MIN_NOTE_DURATION = 0.0625        # 1/16th note floor

# === Composition Defaults ===
DEFAULT_PHRASE_LENGTH = 8
DEFAULT_MAX_LEAP_SEMITONES = 7
DEFAULT_STEP_RATIO = 0.65
DEFAULT_TEMPO = 72
DEFAULT_SEED = 42

# === Psychoacoustic Constants (Agent 10) ===
JND_TIMING_MS = 15          # Just-noticeable difference in timing
GROOVE_DEVIATION_MAX_MS = 30  # Maximum "good groove" offset
FRISSON_DENSITY_TARGET = 0.03  # 2-5% of beats should trigger frisson
HURON_SURPRISE_RATIO = 0.25   # 75% predictable, 25% surprising
IC_TARGET_RANGE = (1.0, 2.5)  # Information content bits per event

# === Velocity Ranges ===
VELOCITY_PPP = 20
VELOCITY_PP = 35
VELOCITY_P = 55
VELOCITY_MP = 70
VELOCITY_MF = 85
VELOCITY_F = 100
VELOCITY_FF = 120
VELOCITY_FFF = 127

# === Voice Ranges (MIDI) — from orchestration research (Agent 11) ===
SOPRANO_RANGE = (60, 84)
ALTO_RANGE = (53, 77)
TENOR_RANGE = (48, 72)
BASS_RANGE = (36, 60)
# Expanded instrument-specific ranges in orchestration.py
```

**Then:** Replace all raw literals with imports. This is mechanical — grep for each value, replace with the named constant.

**Principle:** DRY ("every piece of knowledge should have a single representation"), Explicit > Implicit

---

### 2.2 Consolidate GM instrument mappings

**Problem:** General MIDI instrument name mappings exist in `core.py`, `bridge.py`, `wav_renderer.py`, and now `orchestration.py` independently.

**Action:** Define once in shared constants. The orchestration module's `ORCHESTRA_DB` (Agent 11) with 14 instrument profiles is now the authoritative source — all other files import from it.

**Principle:** DRY, Single Source of Truth

---

### 2.3 Performance-critical optimization: NumPy-vectorize WAV renderer

**Problem (from Agents 8 + 14):** `wav_renderer.py:86-101` runs O(n_harmonics x n_samples) Python-level sin() calls. For a 60-second piece with 8 harmonics at 44.1kHz: ~21 million sin() calls. This is the single biggest performance bottleneck in the codebase.

**Action:** Replace sample-by-sample loops with vectorized NumPy:
```python
# BEFORE (current, ~60 seconds for a 3-minute piece):
for i in range(n_samples):
    for h, amp in timbre:
        samples[i] += amp * math.sin(phase)
        phase += phase_inc

# AFTER (~0.5 seconds for the same piece):
t = np.arange(n_samples) / sample_rate
envelope = vectorized_adsr(t, duration, attack, decay, sustain, release)
signal = sum(rel_amp * np.sin(2 * np.pi * freq * h * t) for h, rel_amp in timbre)
return signal * envelope * amp
```

**Expected speedup:** 100-200x. This is not premature optimization — it's fixing an algorithmic issue (Python interpreter overhead on tight inner loops) that prevents the system from being usable for any piece over 30 seconds.

**Additional synthesis upgrades (from Agent 14):**
- **Karplus-Strong plucked strings** (8 lines of NumPy) — delay line + filter = realistic strings
- **FM synthesis for bells/brass** (2 sin() calls per buffer, carrier:modulator ratios)
- **Freeverb** (8 comb filters + 4 allpass filters in NumPy) — spatial depth
- **Long-term:** Csound integration via `ctcsound` for professional rendering

**Principle:** "Make it work, make it right, make it fast" — the renderer works and is correct, it just needs to be fast. Measured bottleneck, not speculation.

---

## Phase 3: Sacred Composer Internal Cleanup (3-5 days)

These fixes are scoped to `sacred_composer/` and don't touch the main pipeline.

### 3.1 Merge `add_voice()` and `add_voice_microtonal()`

**File:** `sacred_composer/core.py`
**Problem:** Two 55-line functions with 95% identical code. Only difference: microtonal pitch-bend extraction. The world music module (Agent 13) needs microtonal support for Arabic maqam (24-TET quarter tones), gamelan (non-equal tunings), and Tuvan overtone singing — all routed through `add_voice_microtonal()`. Having two paths doubles the maintenance burden.
**Action:** One method with `microtonal: bool = False` parameter. Eliminate ~50 lines of duplication.

**Principle:** DRY, SRP

---

### 3.2 Extract note-assembly helper in combiners

**File:** `sacred_composer/combiners.py`
**Problem:** `layer()`, `canon()`, and `phase()` all repeat the same voice/note construction pattern (lines 45-58, 106-120, 171-183). The fractal_form combiner adds a fourth copy.
**Action:** Extract `_build_voice(pitches, durations, velocities, ...)` helper. Call from all four.

**Principle:** DRY

---

### 3.3 Break down `fractal_form()` (92 lines -> 4 functions)

**File:** `sacred_composer/combiners.py:189-280`
**Problem:** L-system expansion + motif sequencing + voice assembly + form section generation in one function. Historical research (Agent 26) shows this is conceptually rich — Kircher's Arca Musarithmica (1650) used the same fragment-assembly approach, and Mozart's Musikalisches Wurfelspiel (1787) is a random walk over pre-composed fragments. This function should be clean enough to serve as the foundation for these historical techniques.
**Action:** Split into `_expand_lsystem()`, `_sequence_motifs()`, `_assemble_voices()`, and keep `fractal_form()` as orchestrator.

**Principle:** SRP, KISS

---

### 3.4 Break down `build()` (84 lines -> 8 methods)

**File:** `sacred_composer/builder.py:153-236`
**Problem:** 8+ distinct responsibilities in one method. The harmony engine (Agent 16) and developing variation (Agent 5) will add more steps — this must be extensible.
**Action:** Extract: `_build_form()`, `_build_voice_pitches()`, `_build_voice_rhythm()`, `_build_voice_dynamics()`, `_apply_phrase_structure()`, `_apply_rhythm_variation()`, `_apply_constraints()`, `_apply_sectional_variation()`.

**Context from Agent 16 (Harmony):** The builder currently generates melody and bass independently. A proper harmony engine would add a `_build_harmony()` step that generates chord progressions first (using the weighted state machine grammar), then derives melody as chord tones on strong beats + passing tones on weak beats. This step must slot cleanly into the pipeline.

**Context from Agent 5 (Music Theory):** Developing variation (Schoenberg) requires a `_apply_motivic_development()` step: track motifs, apply augmentation/diminution/fragmentation/liquidation across phrases. The `build()` pipeline must accommodate this.

**Principle:** SRP, Open/Closed (open for extension, closed for modification)

---

### 3.5 Fix `bridge.py` coupling

**File:** `sacred_composer/bridge.py`
**Problem:** `sys.path.insert(0, ...)` to import from parent directory — fragile runtime coupling that breaks if the project structure changes.
**Action:** Use proper relative imports or make `SYSTEM_ARCHITECTURE.py` importable as a package.

**Principle:** High Cohesion / Low Coupling

---

### 3.6 Replace if/elif dispatch with dict

**File:** `sacred_composer/builder.py:256-287`
**Problem:** Long if/elif chain for pattern generation strategy selection. As we add new patterns (Mandelbrot, Rossler, Cantor, Zipf, planetary polyrhythm, TextToMelody, ThueMorse, IChing — from Agents 6+26), this chain grows without bound.
**Action:**
```python
PATTERN_DISPATCH = {
    "fibonacci": lambda seed, n: FibonacciSequence().generate(n),
    "infinity_series": lambda seed, n: InfinitySeries(seed=seed).generate(n),
    "lorenz": lambda seed, n: LorenzAttractor().generate(n),
    "golden_spiral": lambda seed, n: GoldenSpiral(start=float(seed)).generate(n),
    "mandelbrot": lambda seed, n: MandelbrotBoundary().generate(n),  # NEW
    "rossler": lambda seed, n: RosslerAttractor().generate(n),  # NEW
    "cantor": lambda seed, n: CantorSet().generate(n),  # NEW
    "zipf": lambda seed, n: ZipfDistribution(seed=seed).generate(n),  # NEW
    "planetary": lambda seed, n: PlanetaryRhythm().generate(n),  # NEW
    # ... etc
}
```

**Principle:** Open/Closed, KISS (dict lookup vs cascade)

---

### 3.7 Split `add_motivic_variation()` (61 lines -> 3 functions)

**File:** `sacred_composer/constraints.py:269-329`
**Problem:** Implements 3 variation strategies (upper neighbor, lower neighbor, inversion) in one function with nested conditionals. The developing variation research (Agent 5) identified 7 more techniques needed: augmentation, diminution, intervallic expansion, fragmentation, liquidation, rhythmic displacement, retrograde. This function must be extensible.
**Action:** One function per strategy + a dispatcher. Create a `VariationStrategy` protocol:
```python
class VariationStrategy(Protocol):
    def apply(self, pitches: list[int], scale: list[int], phrase_start: int, phrase_end: int) -> list[int]: ...
```

**Principle:** SRP, Open/Closed, Strategy Pattern

---

### 3.8 Use `phi` from constants consistently

**Problem:** `sacred_composer/constants.py` already defines `phi`, but `constraints.py` and `builder.py` use raw `0.618` instead. The deep math research (Agent 12) identified that `PHI_INVERSE` (0.618...), `GOLDEN_ANGLE` (137.508...), and `FEIGENBAUM_DELTA` (4.669...) should all be named constants.
**Action:** `from .constants import phi` in all sacred_composer modules.

**Principle:** DRY, Explicit > Implicit

---

### 3.9 Integrate new modules cleanly (orchestration, psychoacoustics, world_music)

**Problem:** Three new modules were built by research agents during this session. They need to follow the same patterns as the rest of the codebase.

**Action:**
- `orchestration.py` — Add logging (currently uses print), validate instrument profile data at import time, add docstrings to `find_best_instruments()` and `assign_instrument()`. The 14-instrument `ORCHESTRA_DB` encodes Rimsky-Korsakov's orchestration principles — document the sources.
- `psychoacoustics.py` — The 7 subsystems (information content, frisson, Bregman, groove, Sethares dissonance, peak-end, earworm) are research-backed (citations from Huron 2006, Sloboda 1991, Blood & Zatorre 2001, Plomp & Levelt 1965, Sethares 2005, Kahneman 2000, Jakubowski 2017). Add these citations as module-level docstring.
- `world_music.py` — The 7 music systems (raga, maqam, gamelan, West African, Japanese, Balinese kotekan, Tuvan overtone) are correctly using fractional MIDI for non-12-TET. Ensure all scale data is in `constants.py` (the Japanese and Indian scales are already there from the user's manual edits).

**Principle:** Consistency, Documentation as Code

---

## Phase 4: Decompose `composer.py` (1-2 weeks)

This is the biggest structural change. `composer.py` is 4,366 lines — a god file containing all 9 compilation passes, form builders, prompt parsing, and orchestration logic.

### 4.1 Target structure

```
composer/
├── __init__.py          # Public API: compose(), compose_suite()
├── pipeline.py          # 9-pass orchestrator (~100 lines)
├── parser.py            # parse_prompt() + validation
├── pass_1_plan.py       # Form planning
├── pass_2_schema.py     # Schema selection
├── pass_3_harmony.py    # Harmony realization
├── pass_4_melody.py     # Melody generation
├── pass_5_counterpoint.py
├── pass_6_orchestration.py
├── pass_7_expression.py
├── pass_8_humanization.py
├── pass_9_validation.py
├── forms/
│   ├── base.py          # FormStrategy protocol
│   ├── sonata.py
│   ├── fugue.py
│   ├── rondo.py
│   ├── ternary.py
│   └── variations.py
└── helpers/
    ├── flocking.py
    ├── pink_noise.py
    └── phyllotaxis.py
```

### 4.2 Eliminate fugue duplication with Strategy pattern

**Problem:** `pass_2_schema_fugue()`, `pass_4_melody_fugue()`, `pass_6_orchestration_fugue()` duplicate ~800 lines of their non-fugue counterparts with minor variations.

**Action:** Each pass function takes a `FormStrategy` that provides form-specific behavior:

```python
class FormStrategy(Protocol):
    def build_plan(self, form_ir: FormIR) -> FormIR: ...
    def generate_melody(self, section: Section, harmony: list) -> list: ...
    def assign_instruments(self, voices: list, ensemble: str) -> list: ...
```

**Context from Agent 13 (World Music):** This Strategy pattern also enables non-Western forms. Japanese jo-ha-kyu (introduction-development-climax) is structurally different from sonata form but fits the same protocol. Indian tala (additive meters like 3+2+2) can slot in as a `TalaStrategy`. The form system must be extensible beyond Western classical.

**Principle:** DRY, Strategy Pattern, Open/Closed

---

### 4.3 Port classical theory into sacred_composer (Phase 7 prep)

**Context from Agent 16 (Harmony), Agent 5 (Music Theory), Agent 9 (Algorithms):**

As composer.py is decomposed, its music theory capabilities should migrate into sacred_composer modules rather than staying in the monolithic file:

| composer.py capability | Target sacred_composer module | Research backing |
|----------------------|------------------------------|-----------------|
| ChordGrammar | `harmony.py` (new) | Agent 16: weighted state machine, corpus-derived probabilities |
| VoiceLeader | `constraints.py` (extend) | Agent 12: Tymoczko orbifold geodesics |
| CounterpointSolver | `constraints.py` (extend) | Agent 9: OR-Tools CP-SAT, Fux rules as constraints |
| SchemaRealization (galant) | `schemas.py` (new) | Agent 5: Schenkerian generation |
| OrchestrationMapper | `orchestration.py` (already started) | Agent 11: Orchidee-inspired timbre matching |
| Humanization pass | `psychoacoustics.py` (extend) | Agent 10: groove templates, 1/f timing |
| Expression pass | `psychoacoustics.py` (extend) | Agent 10: frisson triggers, peak-end rule |

**Principle:** High Cohesion, Migration not Rewrite

---

## Phase 5: Testing (1-2 weeks, parallel with Phase 4)

### 5.1 Fix existing test file

**File:** `test_compositions.py`
**Problem:** Runs compositions and prints results but has zero `assert` statements. A test "passes" if it doesn't crash.

**Action:**
1. Convert to pytest
2. Add assertions: voice count, bar count, note count, quality score threshold
3. Add setup/teardown to clean up generated .mid files
4. Replace `print()` with pytest output

### 5.2 Add unit test suite

**Target:** 80+ pytest tests covering all modules including the new ones.

**Context from Agent 25 (AI Analysis):** The fast quality proxy model (Section 3 of that research) requires ~200 evaluated compositions as training data. The test suite should generate and cache these as a side effect — each test composition with its evaluation score becomes training data for the Bayesian optimizer.

| Module | Tests Needed | Critical Tests |
|--------|-------------|---------------|
| `patterns.py` (12 generators) | 15 | Fibonacci correctness, Lorenz determinism with seed, EuclideanRhythm(3,8) = known pattern |
| `mappers.py` | 12 | `to_pitch` range clamping, `to_rhythm` binary mode, `to_form` bar sum |
| `constraints.py` | 18 | `smooth_leaps` reduces intervals, `_final_leap_recovery` works, phrase endings don't create new leaps |
| `core.py` | 10 | MIDI render/read round-trip, microtonal pitch bend values, voice duration calculation |
| `builder.py` | 8 | Builder produces valid composition for each pattern type |
| `orchestration.py` | 8 | Instrument range validation, timbre distance symmetry, register effectiveness |
| `psychoacoustics.py` | 10 | Sethares consonance ranking matches theory (P8>P5>P4>M3>tt>m2), earworm score on "Twinkle Twinkle" = 90+ |
| `world_music.py` | 8 | 72 melakarta ragas all valid, maqam quarter-tones produce correct pitch bends |
| `evaluation_framework.py` | 5 | Known-good MIDI scores >80, known-bad scores <50 |

### 5.3 Test structure

```
tests/
├── conftest.py                  # Shared fixtures
├── test_patterns.py             # 12 pattern generators
├── test_mappers.py              # 5 mappers
├── test_constraints.py          # Constraint functions
├── test_core.py                 # Core composition + MIDI
├── test_builder.py              # Builder integration
├── test_orchestration.py        # Instrument DB + timbre matching
├── test_psychoacoustics.py      # Perceptual models
├── test_world_music.py          # Raga/maqam/gamelan
├── test_evaluation.py           # Evaluation framework
└── test_compose_integration.py  # End-to-end pipeline
```

**Principle:** "Test Pyramid — 80%+ unit test coverage for new code", "Readable, Independent, Deterministic"

---

## Phase 6: Score Optimization -> 95+ (1-2 weeks, parallel with Phase 5)

This phase uses AI/ML techniques to push the evaluation score from 86.5 toward 95+, guided by research from Agents 2, 5, 9, 16, and 25.

### 6.1 Bayesian parameter optimization with Optuna

**Context (Agent 25):** The `CompositionBuilder` has a well-defined parameter space (~185 million combinations). Bayesian optimization can find near-optimal settings in 200-500 trials.

**Two-phase strategy:**
1. Train a fast proxy model (GradientBoostingRegressor on composition features, <1ms inference) on ~200 evaluated samples
2. Use Optuna's TPE sampler for exploration, only running full music21 evaluation on top ~20 candidates
3. Expected: 86.5 -> 92+ by exploiting the evaluation landscape

**Principle:** "Measure Before Optimizing" — we measured (86.5), identified the bottleneck metrics (tension_arc 77.2, repetition_variation 72.4, transition_motivation 66.7), now we optimize.

### 6.2 Harmony engine (chord grammar state machine)

**Context (Agent 16):** The system currently has NO explicit chord/harmony system. Chords are implied by vertical alignment of voices. Adding a proper harmony engine is the single biggest quality improvement possible.

**Implementation:**
- Weighted directed graph: nodes = Roman numeral chords, edges = transition probabilities from Bach chorale corpus
- Chord-first composition: generate progression, derive melody as chord tones + passing tones
- Pattern integration: Fibonacci -> harmonic rhythm timing, LogisticMap -> harmonic stability, GoldenSpiral -> key relationships on circle of fifths
- Chromatic insertions: Neapolitan, augmented sixths, borrowed chords with mandatory resolution targets

### 6.3 Developing variation (Schoenberg techniques)

**Context (Agent 5):** Fixes repetition_variation metric (72.4).

Implement 7 transformation functions on motif `[(interval, duration), ...]`:
- Augmentation/diminution (scale durations by factor k)
- Intervallic expansion/contraction (multiply intervals, round to semitone)
- Fragmentation (take first N notes)
- Liquidation (progressively replace intervals with steps)
- Rhythmic displacement (shift onset, keep intervals)
- Inversion/retrograde
Track "variation distance" (edit distance on interval+rhythm sequences) to stay in evaluator sweet spot.

### 6.4 Neo-Riemannian transitions

**Context (Agent 5):** Fixes transition_motivation (66.7).

- PLR operations on Tonnetz graph (P=parallel, L=leading-tone, R=relative)
- BFS shortest path between source and target triads for smooth modulations
- Pivot chord modulation: intersect chord sets of both keys, rank by voice-leading parsimony
- Sequential progressions: transpose 2-bar pattern by step toward target key

### 6.5 Lerdahl tension model

**Context (Agent 5):** Fixes tension_arc (77.2).

`T(t) = w1 * hierarchical_dist(event, parent) + w2 * dissonance(melody, chord) + w3 * spiral_dist(current_key, home_key)`

Fit target tension curve per form section. Constrain generation so that chosen chords minimize `|actual_tension - target_tension|`.

### 6.6 OR-Tools constraint solver

**Context (Agent 9):** Replace hand-rolled constraint passes with declarative CP-SAT solver. Counterpoint rules become constraints:
```python
from ortools.sat.python import cp_model
model = cp_model.CpModel()
notes = [model.NewIntVar(60, 84, f'n{i}') for i in range(32)]
for i in range(31):
    model.Add(abs(notes[i+1] - notes[i]) <= 7)  # max leap
```
Solver finds valid solutions in milliseconds. This eliminates the convergence issues where constraint passes undo each other's work.

---

## Phase 7: Documentation Cleanup (2-3 days)

### 7.1 Update README.md

- Add `sacred_composer/` documentation (architecture, usage, examples)
- Add "How to run tests" section
- Add competitive positioning (the 6-point uniqueness from Agent 20)
- Add "How to run tests" section
- Add license

### 7.2 Deduplicate docs

**Problem:** `PATTERNS_OF_CREATION.md` (29KB) overlaps with Parts 1-2 of `KNOWLEDGE_BASE.md` (372KB+). `SACRED_GEOMETRY_AND_MUSIC.md` overlaps with `SACRED_COMPOSER_SPEC.md`.
**Action:** Merge unique content, delete or convert duplicates to pointers.

### 7.3 Add TOC to KNOWLEDGE_BASE.md

**Problem:** Now 9,500+ lines with 42 parts (Part 42: Data Sonification added by Agent 27) and no table of contents.
**Action:** Add clickable TOC at top.

### 7.4 Clean up root directory

**Problem:** Root is cluttered with 20+ generated .mid files, example scripts, and showcase outputs.
**Action:**
- Move `sacred_examples*.py` and `sacred_showcase.py` -> `examples/`
- Move `demo.py` -> `examples/`
- Generated .mid/.wav files already gitignored after Phase 1.1

### 7.5 Document the research findings

**Context:** 28 research agents produced ~500K+ tokens of findings. The most actionable findings are captured in `ROADMAP.md`, but the raw research contains algorithms, pseudocode, citations, and mathematical formulations that will be needed during implementation.

**Action:** Create `docs/research/` directory with summary documents per topic, linking back to the specific algorithms and citations.

**Principle:** Documentation as Code, Knowledge Preservation

---

## Phase 8: System Unification (2-4 weeks, long-term)

### 8.1 Decision: Sacred Composer becomes the primary engine

Per ROADMAP.md (Tier 5.7): "Long-term: sacred_composer becomes the primary engine."

**Why:** Sacred Composer's architecture (Pattern -> Map -> Combine -> Render) is more modular, testable, and extensible. The 9-pass pipeline in `composer.py` is powerful but monolithic. The new modules (orchestration, psychoacoustics, world_music, upcoming harmony engine) all plug into sacred_composer naturally.

### 8.2 Migration path

```
Phase 8a: Shared foundation (done in Phase 2)
  - Shared constants module
  - Shared MIDI rendering
  - Shared evaluation

Phase 8b: Port classical theory into sacred_composer
  - ChordGrammar -> sacred_composer/harmony.py
  - VoiceLeader -> sacred_composer/constraints.py (extend)
  - CounterpointSolver -> sacred_composer/constraints.py (extend)
  - OrchestrationMapper -> sacred_composer/orchestration.py (done)
  - SchemaRealization -> sacred_composer/schemas.py (new)

Phase 8c: Port form intelligence
  - Form templates -> sacred_composer/forms/
  - Pass logic becomes constraint/builder configuration
  - Prompt parser becomes a builder factory

Phase 8d: Deprecate composer.py
  - composer.compose() becomes thin wrapper around CompositionBuilder
  - Eventually remove
```

### 8.3 What NOT to lose from composer.py

These capabilities must be preserved:
- **Galant schemata realization** (Do-Re-Mi, Prinner, Romanesca, etc.)
- **9-pass pipeline ordering** (the pass sequence is musically correct)
- **Fugue generation** (subject/answer/countersubject/stretto)
- **Humanization pass** (now enhanced by psychoacoustics module)
- **Expression pass** (now enhanced by frisson triggers, peak-end rule)
- **Prompt-to-music** (text input -> structured composition plan)

---

## Phase 9: Platform & Distribution (ongoing, after Phase 5)

These are feature additions guided by research findings, prioritized by revenue potential and competitive advantage.

### 9.1 Adaptive game/film music engine (Agents 17 + 14)

**No open-source competitor exists.** Build `sacred_composer/adaptive.py`:
- Vertical layering (enable/disable voices by game state)
- Horizontal re-sequencing (switch sections at boundaries)
- OSC/MIDI parameter mapping: `danger -> LogisticMap r`, `biome -> scale`, `health -> dissonance`
- Real-time rendering via `python-rtmidi`

**Market:** $500-5K/title licensing. Indie game studios need this.

### 9.2 Remotion visualization pipeline (Agent 3 + 21)

Add `to_visualization_json()` to `Composition`. Build Remotion project with:
- PianoRoll, Flower of Life, Fibonacci spiral, cymatics, Lissajous curves, Tonnetz torus
- Audio sync via `<Audio>` component, frame-perfect at 60fps

### 9.3 Music therapy engine (Agent 22)

Market: **$6.68B by 2030**. ISO principle = LogisticMap r-sweep. Parkinson's RAS. Sleep music. Biometric-adaptive via smartwatch.

### 9.4 Educational platform (Agent 15)

12-module "Music from Mathematics" course. Streamlit playground. YouTube channel. **BRIDGES 2026 paper (Galway, Aug 5-8, deadline Feb 1, 2026).** Revenue: $500-2K/month year 1.

### 9.5 Generative on-chain music (Agent 23)

32 bytes per composition on Base L2. No one has shipped this in the Art Blocks model. Generative player: wallet -> unique composition. Free to listen, pay to own.

### 9.6 Social/multiplayer composition (Agent 28)

Discord bot, seed-based sharing (compositions as URLs), multiplayer rooms, competitive leaderboard, musical genetics (breed compositions). Full React + FastAPI architecture designed.

---

## Priority Order & Timeline

| Phase | Effort | Impact | Dependency |
|-------|--------|--------|------------|
| **1: Stop the bleeding** | 1-2 days | High | None |
| **2: Centralize constants + vectorize WAV** | 2-3 days | High | None |
| **3: Sacred Composer cleanup** | 3-5 days | Medium | Phase 2 |
| **4: Decompose composer.py** | 1-2 weeks | Critical | Phase 2 |
| **5: Testing** | 1-2 weeks | High | Phases 3-4 (parallel) |
| **6: Score optimization -> 95+** | 1-2 weeks | High | Phase 3 (parallel with 4-5) |
| **7: Documentation** | 2-3 days | Medium | Phases 1-4 |
| **8: System unification** | 2-4 weeks | Strategic | Phases 3-5 |
| **9: Platform & distribution** | Ongoing | Revenue | Phase 5+ |

**Total for code health (Phases 1-5): ~4-6 weeks.**
**Total including evolution (all phases): ~3-4 months.**
Phases 1-2 ship this week. Phases 3-6 run in parallel. Phases 7-9 are ongoing.

---

## Principles Violation Tracker

Each phase maps to the principles it fixes:

| Principle | Current | Target | Fixed By |
|-----------|---------|--------|----------|
| KISS | ~30% | >85% | Phase 3, 4 |
| DRY | ~25% | >90% | Phase 2, 3, 4 |
| YAGNI | ~70% | >90% | Phase 3 |
| SRP | ~30% | >85% | Phase 3, 4 |
| High Cohesion / Low Coupling | ~40% | >85% | Phase 3, 7, 8 |
| Composition > Inheritance | ~90% | >95% | — |
| Law of Demeter | ~85% | >90% | — |
| Explicit > Implicit | ~40% | >90% | Phase 1, 2 |
| Fail Fast | ~30% | >90% | Phase 1 |
| Test Pyramid | ~5% | >80% | Phase 5 |
| Documentation as Code | ~50% | >85% | Phase 7 |
| Consistency | ~60% | >90% | Phase 1, 2 |
| No Secrets in Code | 100% | 100% | — |
| Log Everything Important | ~20% | >85% | Phase 1 |

**Target after all phases: >85% compliance across all principles.**

---

## Non-Goals (Things We're NOT Doing in the Health Phases)

- **Not rewriting from scratch.** The music theory logic in `composer.py` is correct and battle-tested (2,500 years of lineage validates the approach). We're restructuring, not replacing.
- **Not adding features in Phases 1-5.** New patterns, harmony engine, world music systems, visualization — these belong in Phase 6+ and ROADMAP.md. Health first, features second.
- **Not changing the architecture philosophy.** Pattern -> Map -> Combine -> Render stays. 9-pass pipeline stays (as implementation detail inside the builder). We're cleaning, not redesigning.
- **Not optimizing for a specific platform yet.** Game engine, web app, NFT platform, therapy engine — these are Phase 9. The clean architecture enables all of them; we don't pick one until the foundation is solid.

---

## Research Agent Index (28 Reports)

For detailed algorithms, pseudocode, citations, and mathematical formulations referenced throughout this plan:

| # | Topic | Key Deliverable |
|---|-------|----------------|
| 1 | Spectral/Microtonal | Combination tone bass, JI lattice, spectral interpolation |
| 2 | AI/ML Enhancement | DEAP genetic algorithm, Bayesian optimization, FluidSynth |
| 3 | Remotion Visualization | to_visualization_json(), PianoRoll component, sacred geometry |
| 4 | Live Performance | python-rtmidi, live coding REPL, generative installation |
| 5 | Advanced Music Theory | Developing variation, neo-Riemannian, Lerdahl tension, Schenkerian |
| 6 | Novel Pattern Sources | Mandelbrot, Rossler, Cantor, Zipf, planetary, EEG, protein |
| 7 | Output & Distribution | FluidSynth, API service, DistroKid, MusicXML |
| 8 | Codebase Audit | 18 bugs with file:line, performance bottlenecks, missing tests |
| 9 | Generative Algorithms | Xenakis sieves, Cope EMI/SPEAC, Factor Oracle, OR-Tools, entropy |
| 10 | Psychoacoustics | **Built psychoacoustics.py** — Sethares, frisson, groove, earworm |
| 11 | Orchestration & Timbre | **Built orchestration.py** — 14 instruments, timbre matching, orchestral WAV |
| 12 | Deep Math | Group theory D12, Tonnetz orbifolds, maximally even sets, wavelets |
| 13 | World Music | **Built world_music.py** — raga, maqam, gamelan, polyrhythm, kotekan |
| 14 | Synthesis Techniques | Karplus-Strong, FM, granular, Moog filter, Freeverb, Csound |
| 15 | Education Platform | 12-module curriculum, Streamlit, BRIDGES 2026, revenue estimates |
| 16 | Harmony Engine | Chord grammar FSM, jazz voicing, spectral harmony, pattern-driven |
| 17 | Procedural Game/Film | Adaptive engine, iMUSE, parameter mapping, market gap analysis |
| 18 | Notation & Publication | Advanced LilyPond, MusicXML, auto-articulation, sheet music market |
| 19 | Music & Consciousness | Binaural beats, brainwave entrainment, flow state, raga time-of-day |
| 20 | Competitions & Community | AIMC, ISMIR, BRIDGES deadlines, feature comparison matrix |
| 21 | Sacred Geometry Viz | Flower of Life, Metatron's Cube, cymatics, Lissajous, Tonnetz torus |
| 22 | Music Therapy | ISO principle, Parkinson's RAS, sleep music, $6.68B market |
| 23 | Blockchain/On-Chain | Art Blocks model, 32 bytes/composition, generative player |
| 24 | Multi-Sensory Installation | Hardware budgets ($5K-80K), Ars Electronica, Musikfonds funding |
| 25 | AI Music Analysis | Fast proxy model, Optuna optimization, style distance, emotion MER |
| 26 | Historical Algorithms | Pythagoras->Norgard lineage, 7 techniques to revive |
| 27 | Data Sonification | **Built KNOWLEDGE_BASE Part 42** — climate, LIGO, biosignal, DataPattern |
| 28 | Social/Collaborative | Discord bot, multiplayer rooms, musical genetics, web app architecture |

---

*Generated from Principles Compliance Audit of 2026-04-02.*
*Enhanced 2026-04-03 with findings from 28 parallel deep-research agents.*
*Maintainer: Konrad Reyhe*
