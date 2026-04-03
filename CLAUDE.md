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
tests/               # 241 pytest tests (11 files)
examples/            # Example scripts and sonification demos
viz/                 # Remotion visualization scaffold
web/                 # Standalone generative player (HTML/JS)
```

## Key Commands

```bash
python -m pytest tests/ -v          # Run 241 tests
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

88.5/100 (best with L1 PASS, seed=13). Strongest: thematic_development (100), phrase_boundaries (100), directional_momentum (93.0), tension_arc (85.1). Weakest: repetition_variation (58.9).

## Key Files

- `ROADMAP.md` — 28-agent research roadmap with all future directions
- `GAMEPLAN.md` — Principles compliance plan (fully executed)
- `HANDOVER.md` — Detailed session record

## Don't

- Don't add features without tests
- Don't use global random state (always `random.Random(seed)`)
- Don't break the Pattern protocol
- Don't modify composer.py directly (use the composer/ package)
