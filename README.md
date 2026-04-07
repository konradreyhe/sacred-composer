# Sacred Composer

Deterministic music composition from mathematical patterns. Python, no ML, no GPU. Every note traceable to a generating equation.

## Sacred Geometry Vol. 1

A 10-track album where each track is driven by a different mathematical structure:

| # | Title | Pattern | Score |
|---|-------|---------|-------|
| 01 | Threshold | Fibonacci sequence | 92.24 |
| 02 | The Infinite Series | Norgard's infinity series | 92.57 |
| 03 | Golden Spiral | Phi-derived contour | 91.77 |
| 04 | Harmonic Series | Overtone physics | 92.33 |
| 05 | Logistic Map (r=3.7) | Edge of chaos | 92.43 |
| 06 | Mandelbrot Boundary | Fractal boundary walk | 91.73 |
| 07 | Rossler's Strange Attractor | Chaotic system | 88.41 |
| 08 | Cantor's Dust | Fractal silence | 91.55 |
| 09 | Zipf's Law | Power-law distribution | 91.51 |
| 10 | Thue-Morse Resolution | Anti-self-similarity | 93.41 |

**Album average: 91.79/100** across 14 music-theory metrics with zero rule violations.

The entire album is reproducible from `examples/album/seeds.json`. One command regenerates it bit-identically.

## What It Does

- **23 pattern generators**: Fibonacci, golden spiral, harmonic series, infinity series, Euclidean rhythm, pink noise, logistic map, Lorenz attractor, phyllotaxis, L-systems, flocking, 1/f rubato, Mandelbrot, Rossler, Cantor, Zipf, Thue-Morse, and more
- **Harmony engine**: constraint-aware voice leading, counterpoint rules, cadence placement, tension arcs
- **Output formats**: MIDI, LilyPond scores, WAV audio (Karplus-Strong + FM synthesis + Freeverb), orchestral WAV, MusicXML
- **Evaluation**: 14-metric automated scoring framework (album peak: 92.57/100)
- **329 tests passing**

## Quick Start

```bash
pip install midiutil numpy scipy
```

```python
from sacred_composer.builder import CompositionBuilder

piece = (
    CompositionBuilder(key="C_major", tempo=72, bars=48, title="Sacred Offering")
    .form(pattern="fibonacci", n_sections=5)
    .melody(pattern="infinity_series", instrument="violin", seed=1)
    .bass(pattern="harmonic_series", instrument="cello", seed=11)
    .build()
)
piece.render("output.mid")
```

## Package Structure

The `sacred_composer/` package contains 20 modules (~8,600 lines):

| Module | Purpose |
|--------|---------|
| `core.py` | Composition, Voice, Note data structures, MIDI rendering |
| `patterns.py` | 23 mathematical pattern generators |
| `mappers.py` | Map raw pattern values to pitch, rhythm, dynamics, form |
| `constraints.py` | Voice leading rules, range enforcement, leap recovery |
| `harmony.py` | Chord progressions, harmonic rhythm, cadences |
| `builder.py` | High-level `CompositionBuilder` API |
| `constants.py` | Golden ratio, scales, intervals |
| `evaluate.py` | Multi-level scoring framework |
| `lilypond.py` | LilyPond score export |
| `musicxml.py` | MusicXML export |
| `wav_renderer.py` | Audio synthesis (Karplus-Strong, FM, Freeverb) |
| `orchestration.py` | 14 instruments, timbre matching, orchestral WAV |
| `combiners.py` | Merge and layer multiple pattern streams |
| `psychoacoustics.py` | Sethares dissonance, frisson, groove, earworm |
| `world_music.py` | Raga, maqam, gamelan, West African, Japanese scales |
| `adaptive.py` | Game/film adaptive composition |
| `optimizer.py` | Parameter search for score optimization |
| `osc_bridge.py` | OSC/MIDI for installations |
| `bridge.py` | PerformanceIR bridge to 9-pass pipeline |
| `__init__.py` | Package exports |

## Web Player

Live at **https://konradreyhe.github.io/sacred-composer/**

- **[Album page](https://konradreyhe.github.io/sacred-composer/album.html)** — listen to Tone.js previews of all 10 tracks
- **[Name composer](https://konradreyhe.github.io/sacred-composer/)** — type your name, hear its unique composition

## Rendering the Album

```bash
# Render master WAVs (requires FluidSynth + MuseScore General SoundFont)
python examples/album/render_masters.py

# Normalize to -14 LUFS (Spotify target)
python examples/album/normalize_masters.py

# Render music videos (requires Remotion, ~16 hours at 60fps)
cd viz && bash render_album.sh
```

## Tests

```bash
python -m pytest tests/ -v
```

All 329 tests pass. No external services required.

## Evaluation

Score any generated MIDI on a 0-100 scale:

```python
from sacred_composer.evaluate import evaluate_composition
from sacred_composer.core import Composition

comp = Composition.from_midi("output.mid")
report = evaluate_composition(comp)
print(f"Score: {report['total']}/100")
```

Four evaluation levels:
1. **Rule Compliance** (gate) -- parallel fifths/octaves, voice crossing, range violations
2. **Statistical Quality** -- pitch/rhythm distributions vs. corpus norms
3. **Structural Quality** -- harmonic rhythm, phrase structure, cadence placement
4. **Perceptual Quality** -- tension curve shape, dynamic range, textural variety

## Documentation

- `PRINCIPLES.md` -- 12 engineering principles governing the codebase
- `ROADMAP.md` -- 28-agent research roadmap
- `examples/album/liner_notes/README.md` -- Album liner notes
- `examples/album/launch_copy.md` -- Social media launch copy

## License

Not yet specified.
