# Sacred Geometry Vol. 1 — Album Production

**Status:** Week 1 ✅ complete · Week 2 ✅ rendering complete · Week 3 pending

## Current Progress

| Week | Task | Status |
|---|---|---|
| 1 | Grid-search 9 patterns × 15 seeds × 12 keys (1,620 candidates) | ✅ |
| 1 | Lock tracklist in `seeds.json` | ✅ |
| 2 | Implement Goosebump Engine (`.frisson()`) | ✅ |
| 2 | Render 9 master WAVs via FluidSynth | ✅ |
| 2 | FFmpeg loudnorm to -14 LUFS (Spotify target) | ✅ |
| 3 | Remotion video per-track | ⏳ |
| 3 | Cover art | ⏳ |
| 3 | DistroKid signup + upload | ⏳ |
| 4 | Social launch | ⏳ |

## Tracklist

All 9 tracks pass L1 (zero rule violations). Average eval score 89.22/100.

| # | Track | Pattern | Key | Seed | Eval |
|---|---|---|---|---|---|
| 1 | Threshold | fibonacci | Bb_minor | 3 | 90.17 |
| 2 | The Infinite Series | infinity_series | C_major | 1 | 90.17 |
| 3 | Golden Spiral | golden_spiral | A_minor | 11 | 89.97 |
| 4 | Harmonic Series | harmonic_series | E_minor | 11 | **91.09** |
| 5 | Logistic Map (r=3.7) | logistic | D_major | 3 | 90.26 |
| 6 | Mandelbrot Boundary | mandelbrot | E_minor | 2 | 89.40 ⭐ |
| 7 | Rössler's Strange Attractor | rossler | E_minor | 10 | 85.54 |
| 8 | Cantor's Dust | cantor | F#_minor | 3 | 86.44 |
| 9 | Zipf's Law | zipf | F#_minor | 8 | 89.90 |

⭐ Track 6 gets the Goosebump Engine — a deliberate appoggiatura at
the golden-section climax (Sloboda 1991 chill trigger).

## File Layout

```
examples/album/
├── README.md                   (this file)
├── seeds.json                  (locked tracklist, reproducibility spec)
├── search_seeds.py             (grid search over (seed, key) space)
├── render_candidates.py        (top-3 auditioning renders)
├── render_masters.py           (final master-WAV renders)
├── seeds/                      (search results, top-20 per pattern)
│   ├── search_fibonacci.csv
│   ├── search_infinity_series.csv
│   ├── search_golden_spiral.csv
│   ├── search_harmonic_series.csv
│   ├── search_logistic.csv
│   ├── search_mandelbrot.csv
│   ├── search_rossler.csv
│   ├── search_cantor.csv
│   └── search_zipf.csv
├── masters/                    (raw FluidSynth renders, gitignored)
│   └── 01_threshold.wav ... 09_zipfs_law.wav
├── normalized/                 (FFmpeg loudnorm -14 LUFS, gitignored)
│   └── 01_threshold.wav ... 09_zipfs_law.wav
├── audition/                   (top-3 per pattern, gitignored)
├── videos/                     (Week 3: Remotion renders, gitignored)
└── liner_notes/
    └── README.md               (album notes template)
```

## Reproducibility

Every track on this album can be regenerated, note-for-note, from
`seeds.json`. To rebuild:

```bash
python examples/album/render_masters.py
ffmpeg -i masters/<file>.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 normalized/<file>.wav
```

## Runtime

~25 minutes total (8 tracks at 2:40, track 7 at 3:43). Below the
~40min target in ALBUM_PLAN.md. Options to extend:
- Increase `bars` from 48 to 64 (would add ~30% runtime)
- Add a 10th track (wire ThueMorse pattern into the builder)
- Ship as-is; EP-length albums are legitimate

## Next Steps

1. **Listen to all 9 masters.** Flag any that feel too static / too
   busy / too thin. Option to re-search those patterns.
2. **A/B test frisson on Track 6.** Render with and without
   `.frisson()`, listen blind, verify the appoggiatura is audibly
   present and pleasant.
3. **Cover art.** Single Fibonacci-spiral still from Remotion, or
   commissioned.
4. **Begin Week 3:** Remotion video pipeline.
