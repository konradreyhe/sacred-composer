# MUSIK! -- Sacred Composer

AI-assisted classical music composition using sacred geometry and nature-inspired algorithms. No neural networks, no training data -- music theory and mathematical patterns encoded as Python.

## What It Does

- **12 pattern generators**: Fibonacci, golden spiral, harmonic series, infinity series, Euclidean rhythm, pink noise, logistic map, Lorenz attractor, phyllotaxis, L-systems, flocking, 1/f rubato
- **Harmony engine**: constraint-aware voice leading, counterpoint rules, cadence placement, tension arcs
- **Output formats**: MIDI, LilyPond scores, WAV audio (Karplus-Strong synthesis, FM synthesis, Freeverb reverb), orchestral WAV
- **Evaluation**: automated scoring framework (current best: 86.5/100)
- **155 tests passing**

## Package Structure

The `sacred_composer/` package contains 16 modules:

| Module | Purpose |
|--------|---------|
| `core.py` | Composition, Voice, Note data structures, MIDI rendering |
| `patterns.py` | 12 mathematical pattern generators |
| `mappers.py` | Map raw pattern values to pitch, rhythm, dynamics, form |
| `constraints.py` | Voice leading rules, range enforcement, leap recovery |
| `harmony.py` | Chord progressions, harmonic rhythm, cadences |
| `builder.py` | High-level `CompositionBuilder` API |
| `constants.py` | Golden ratio, scales, intervals |
| `evaluate.py` | Multi-level scoring (rule compliance, statistical, structural, perceptual) |
| `lilypond.py` | LilyPond score export |
| `wav_renderer.py` | Audio synthesis (Karplus-Strong, FM, Freeverb) |
| `orchestration.py` | Instrument assignment and register mapping |
| `combiners.py` | Merge and layer multiple pattern streams |
| `psychoacoustics.py` | Perceptual models (roughness, brightness, masking) |
| `bridge.py` | Integration with the legacy 9-pass compiler pipeline |
| `world_music.py` | Non-Western scales and tuning systems |
| `__init__.py` | Package exports |

## Quick Start

```bash
pip install midiutil numpy scipy
```

```python
from sacred_composer.builder import CompositionBuilder

piece = (
    CompositionBuilder(key="C_minor", tempo=72, bars=48, title="Sacred Offering")
    .melody(pattern="infinity_series", instrument="violin")
    .bass(pattern="harmonic_series")
    .inner_voice(pattern="golden_spiral", instrument="viola")
    .build()
)
piece.render("output.mid")
```

## Examples

Example scripts live in `examples/`:

```bash
python examples/sacred_showcase.py      # Showcase compositions with WAV + LilyPond
python examples/sacred_examples.py      # Phase 1 pattern demos
python examples/sacred_examples_phase2.py  # Phase 2 harmony + constraints
python examples/sacred_examples_phase3.py  # Phase 3 full pipeline
python examples/demo.py                 # Legacy compiler pipeline demo
```

## How to Run Tests

```bash
python -m pytest tests/ -v
```

All 155 tests should pass. No external services required.

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

## Legacy Pipeline

The original 9-pass compiler pipeline (`composer.py`) is still available:

```python
from composer import compose

perf, form, report = compose(
    "A dramatic sonata exposition in C minor, heroic, 40 bars, for piano",
    "output.mid"
)
```

## Documentation

- `KNOWLEDGE_BASE.md` -- 42-part reference (~350 KB) covering music theory, neuroscience, orchestration, AI composition
- `SACRED_COMPOSER_SPEC.md` -- Full specification for the sacred_composer package
- `SACRED_GEOMETRY_AND_MUSIC.md` -- The mathematical foundations
- `PATTERNS_OF_CREATION.md` -- Pattern generator design and philosophy
- `PRINCIPLES.md` -- 12 engineering principles governing the codebase
- `LISTENING_GUIDE.md` -- What to listen for in generated compositions
- `GAMEPLAN.md` / `ROADMAP.md` -- Development plans

## License

Not yet specified.
