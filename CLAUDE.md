# Sacred Composer — Project Instructions for Claude

## Project Overview

Sacred Composer is a deterministic music composition system where mathematical patterns ARE the music. Python, no ML, no GPU. Every note traceable to a generating pattern.

## Architecture

```
sacred_composer/     # Core package (20 modules, 8,600+ lines)
  patterns.py        # 23 pattern generators (Pattern protocol: generate/iter/name)
  mappers.py         # to_pitch, to_rhythm, to_dynamics, to_form
  combiners.py       # layer, canon, phase, fractal_form
  constraints.py     # Voice leading, leap recovery, phrase endings
  builder.py         # CompositionBuilder (fluent API, .harmony(), .consciousness())
  harmony.py         # Chord grammar FSM, voice leading, chord-first composition
  core.py            # Note, Voice, Score, Composition (renders .mid/.ly/.wav/.xml)
  orchestration.py   # 14 instruments, timbre matching, orchestral WAV
  psychoacoustics.py # Sethares dissonance, frisson, groove, earworm
  world_music.py     # Raga, maqam, gamelan, W.African, Japanese, Balinese, Tuvan
  adaptive.py        # GameState -> AdaptiveComposer (game/film music)
  optimizer.py       # Fast eval proxy + parameter search
  wav_renderer.py    # NumPy vectorized + Karplus-Strong + FM + Freeverb
  lilypond.py        # Publication-ready notation
  musicxml.py        # MusicXML export
  osc_bridge.py      # OSC/MIDI for installations
  constants.py       # Shared constants (phi, scales, MIDI)
  evaluate.py        # Evaluation framework integration
  bridge.py          # PerformanceIR bridge

composer/            # Decomposed 9-pass pipeline (24 files)
tests/               # 327 pytest tests (14 files)
examples/            # Example scripts and sonification demos
viz/                 # Remotion visualization scaffold
web/                 # Standalone generative player (HTML/JS)
```

## Key Commands

```bash
python -m pytest tests/ -v          # Run 327 tests
python playground.py                # Streamlit interactive UI (needs: pip install streamlit)
python api.py                       # FastAPI at localhost:8000/docs
python examples/sacred_showcase_v2.py  # Generate 8 demo compositions
```

## Coding Conventions

- Pattern generators follow the Pattern protocol: `generate(n) -> list[float]`, `__iter__`, `name`
- All randomness uses `random.Random(seed)` for determinism (never global random)
- Use `from sacred_composer.constants import phi, PHI_INVERSE` not raw `0.618`
- Output formats: `.mid`, `.ly`, `.wav`, `.orch.wav`, `.musicxml`, `.xml`
- Tests use pytest with descriptive class/method names

## Current Eval Score

**91.96/100 L1 PASS** (Bb_minor seed=43, 0 violations) — new peak as of session 10 (commit `6021902`, crescendo entry). Reproducible config: `CompositionBuilder(key="Bb_minor", tempo=72, bars=48).form(pattern="fibonacci", n_sections=5).melody(pattern="golden_spiral", instrument="violin", seed=S).bass(pattern="harmonic_series", instrument="cello", seed=S+10)`. The crescendo entry (`_apply_crescendo_entry` in `sacred_composer/builder.py`) lifted `L3.tension_arc` 79.02→88.67 with no regressions. Weakest metrics now: `L4.transition_motivation` (71.43), `L2.interval_distribution` (86.43), `L2.chord_vocabulary` (88.19). Pre-crescendo baseline was 90.78. See HANDOVER.md for session-10 findings (including why the tail-merge approach failed). Note: earlier 94.0/seed=47 claim (commit 124efef) still unreproduced — seed=47 currently 89.66.

## Key Files

- `ROADMAP.md` — 28-agent research roadmap with all future directions
- `GAMEPLAN.md` — Principles compliance plan (fully executed)
- `HANDOVER.md` — Detailed session record

## Don't

- Don't add features without tests
- Don't use global random state (always `random.Random(seed)`)
- Don't break the Pattern protocol
- Don't modify composer.py directly (use the composer/ package)
