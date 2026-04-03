# Contributing to Sacred Composer

Thank you for your interest in contributing to Sacred Composer! This project sits at the intersection of mathematics, music, and code — contributions from any of these domains are welcome.

## Quick Start

```bash
git clone https://github.com/KonradReyhe/MUSIK.git
cd MUSIK!
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## How to Contribute

### Add a New Pattern Generator

The easiest way to contribute. Every pattern generator follows the same protocol:

```python
class MyPattern:
    """One-sentence description of the pattern.
    
    Longer explanation of the mathematical source and musical application.
    """
    
    def __init__(self, param: float = 1.0) -> None:
        self._param = param
    
    @property
    def name(self) -> str:
        return f"my_pattern(param={self._param})"
    
    def generate(self, n: int) -> list[float]:
        """Return exactly n values from this pattern."""
        return [...]  # your pattern logic
    
    def __iter__(self):
        """Yield values lazily (may be infinite)."""
        i = 0
        while True:
            yield ...
            i += 1
```

Then:
1. Add the class to `sacred_composer/patterns.py`
2. Add it to `sacred_composer/__init__.py` imports and `__all__`
3. Add a test class in `tests/test_patterns.py`
4. Add an entry in `builder.py` `PATTERN_GENERATORS` dict

### Improve the Evaluation Score

Our best score is 86.5/100. The weakest metrics:
- `tension_arc` (77.2) — needs better dynamic/pitch contour shaping
- `repetition_variation` (72.4) — needs more motivic development
- `transition_motivation` (66.7) — needs smoother section transitions

Changes to `constraints.py`, `builder.py`, or `harmony.py` that push these metrics up are highly valued.

### Add a World Music System

See `sacred_composer/world_music.py` for the existing 7 systems. New systems should:
- Use fractional MIDI for non-12-TET tunings (via `pitch_bend`)
- Include scale/tuning data, melodic rules, and rhythmic patterns
- Add tests in `tests/test_world_music.py`

### Improve Audio Quality

The WAV renderer (`wav_renderer.py`) uses additive + Karplus-Strong + FM synthesis. Ideas:
- Better instrument models (physical modeling for specific instruments)
- Improved reverb (convolution with real impulse responses)
- FluidSynth integration for SoundFont rendering

## Running Tests

```bash
python -m pytest tests/ -v          # all 241 tests
python -m pytest tests/ -k pattern  # just pattern tests
python -m pytest tests/ --tb=short  # compact output
```

## Code Style

- Python 3.10+ with type hints
- Follow existing patterns in the codebase
- No unnecessary dependencies — core package needs only `midiutil` and `numpy`
- Every note must be traceable to its generating pattern

## Project Structure

```
sacred_composer/     # Core package (20 modules)
composer/            # Decomposed 9-pass pipeline (24 files)
tests/               # pytest suite (11 files, 241 tests)
examples/            # Example scripts and sonification demos
viz/                 # Remotion visualization scaffold
api.py               # FastAPI REST service
discord_bot.py       # Discord bot
playground.py        # Streamlit interactive UI
```

## License

MIT — see `LICENSE`.
