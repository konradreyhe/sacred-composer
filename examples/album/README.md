# Sacred Geometry Vol. 1 — Album Production

**Status:** Week 1 ✅ · Week 2 ✅ · Week 3 🔧 in progress · Week 4 pending

## Current Progress

| Week | Task | Status |
|---|---|---|
| 1 | Grid-search 9 patterns × 15 seeds × 12 keys (1,620 candidates) | ✅ |
| 1 | Lock tracklist in `seeds.json` | ✅ |
| 2 | Implement Goosebump Engine (`.frisson()`) | ✅ |
| 2 | Render 9 master WAVs via FluidSynth | ✅ |
| 2 | FFmpeg loudnorm to -14 LUFS (Spotify target) | ✅ |
| 3 | A/B test frisson on Track 6 | ✅ verified: -0.18 eval, +0.5 tension |
| 3 | Cover art (Mandelbrot 3000×3000) | ✅ `cover_art.jpg` |
| 3 | Remotion 9-track video pipeline | ✅ wired + test render passed |
| 3 | Export viz data for all 9 tracks | ✅ `viz/src/data/track_*.json` |
| 3 | Render all 9 full videos | ⏳ `cd viz && bash render_album.sh` |
| 3 | DistroKid signup + upload | ⏳ |
| 4 | Social launch | ⏳ |

## Tracklist

All 9 tracks pass L1 (zero rule violations). Average eval score 89.20/100.

| # | Track | Pattern | Key | Seed | Eval | Tension |
|---|---|---|---|---|---|---|
| 1 | Threshold | fibonacci | Bb_minor | 3 | 90.17 | 80.8 |
| 2 | The Infinite Series | infinity_series | C_major | 1 | 90.17 | 72.9 |
| 3 | Golden Spiral | golden_spiral | A_minor | 11 | 89.97 | 79.9 |
| 4 | Harmonic Series | harmonic_series | E_minor | 11 | **91.09** | 81.6 |
| 5 | Logistic Map (r=3.7) | logistic | D_major | 3 | 90.26 | 82.3 |
| 6 | Mandelbrot Boundary | mandelbrot | E_minor | 2 | 89.22 ⭐ | 70.0 |
| 7 | Rössler's Strange Attractor | rossler | E_minor | 10 | 85.54 | 59.0 |
| 8 | Cantor's Dust | cantor | F#_minor | 3 | 86.44 | 66.3 |
| 9 | Zipf's Law | zipf | F#_minor | 8 | 89.90 | 91.4 |

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
├── export_viz_data.py          (export viz JSON for Remotion)
├── copy_audio_to_viz.py        (copy normalized WAVs to viz/public/)
├── cover_art.py                (Mandelbrot cover art generator)
├── cover_art.jpg               (3000×3000, gitignored, regenerate with cover_art.py)
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
└── liner_notes/
    └── README.md               (album notes template)
```

## Remotion Video Pipeline

```bash
# 1. Export composition data (already done)
python examples/album/export_viz_data.py

# 2. Copy audio to viz/public/ (already done)
python examples/album/copy_audio_to_viz.py

# 3. Render all 9 videos (~5 min each at 60fps)
cd viz && bash render_album.sh

# Or render one track:
cd viz && bash render_album.sh --track 6
```

Compositions registered in Remotion: `Track01-Threshold` through `Track09-ZipfsLaw`.

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

1. **Listen to all 9 masters.** Flag any that sound too static / busy / thin.
2. **Render full videos.** `cd viz && bash render_album.sh`
3. **DistroKid signup + metadata upload.**
4. **Social launch.** Templates in `ALBUM_PLAN.md` §Week-4.
