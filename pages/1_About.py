"""About — Sacred Composer project overview."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="About | Sacred Composer", layout="wide")

st.title("About Sacred Composer")

st.markdown("""
Sacred Composer is a deterministic music composition engine that transforms
mathematical and natural patterns into expressive classical music. Every note
is derived from algorithms — no randomness, no machine-learning black boxes —
just pure mathematical beauty rendered as sound.

### How it works

1. **Choose a pattern** — Fibonacci, golden spiral, Mandelbrot, logistic map,
   Rossler attractor, harmonic series, or the Infinity Series.
2. **Map to music** — Patterns are mapped to pitch, rhythm, and dynamics using
   configurable strategies (modular, normalize, proportional).
3. **Compose** — The `CompositionBuilder` layers melody, bass, and harmony
   voices, applies rhythmic Euclidean patterns, and outputs a complete piece.
4. **Render** — Pure-NumPy WAV synthesis with additive/FM/Karplus-Strong
   timbres and Freeverb spatial processing. No external synth required.

### Available patterns

| Pattern | Source | Character |
|---------|--------|-----------|
| Infinity Series | Per Norgard | Fractal self-similarity at every scale |
| Fibonacci | Nature | Organic growth, spiraling motion |
| Golden Spiral | Phi | Smooth, ever-expanding arcs |
| Harmonic Series | Acoustics | Natural overtone consonance |
| Logistic Map | Chaos theory | Order-to-chaos transitions |
| Mandelbrot | Fractal geometry | Complex boundary exploration |
| Rossler Attractor | Dynamical systems | Gentle chaotic orbits |

### Consciousness presets

The engine includes presets tuned for specific mental states — deep sleep,
meditation, relaxation, flow, focus, and energy — each with carefully chosen
keys, tempos, and dynamic ranges.

### Links

- [GitHub repository](https://github.com/KonradReyhe/MUSIK)
- Built with Python, NumPy, MIDIUtil, and Streamlit
""")
