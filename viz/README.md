# Sacred Composer Visualization

Remotion-based music video renderer for Sacred Composer compositions.

## Setup

### 1. Generate composition data

```bash
cd ..
python -c "
from sacred_composer import *
c = fibonacci_prelude()
import json, pathlib
pathlib.Path('viz/src/data/composition.json').write_text(json.dumps(c.to_visualization_json(), indent=2))
c.render('viz/public/composition.wav')
"
```

### 2. Install dependencies

```bash
npm install
```

### 3. Preview in Remotion Studio

```bash
npm start
```

### 4. Render to MP4

```bash
npm run render
```

Output will be written to `out/SacredComposition.mp4`.

## Project structure

```
viz/
  src/
    Root.tsx                  — Remotion entry, registers composition
    SacredComposition.tsx     — Main scene layout (audio + layers)
    components/
      PianoRoll.tsx           — Canvas-based scrolling piano roll
      FormTimeline.tsx        — Section labels + progress bar
      FibonacciSpiral.tsx     — Golden-angle spiral lit by notes
    lib/
      timing.ts               — Timing utilities + types
    data/
      sample.json             — Sample composition for preview
  public/
    composition.wav           — Audio file (generate with sacred_composer)
```

## Customization

- **visibleWindowSec** in `SacredComposition.tsx` controls how many seconds of notes are visible at once (default: 8).
- Voice colours are defined in `lib/timing.ts` — edit `VOICE_COLORS` to match your palette.
- The spiral point count and glow intensity can be tuned in `FibonacciSpiral.tsx`.
