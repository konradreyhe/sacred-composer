# Sacred Geometry Vol. 1 — Album Production

**Status:** Week 1 ✅ · Week 2 ✅ · Week 3 ✅ complete · Week 4 pending

## Current Progress

| Week | Task | Status |
|---|---|---|
| 1 | Grid-search 9 patterns × 15 seeds × 12 keys (1,620 candidates) | ✅ |
| 1 | Lock tracklist in `seeds.json` | ✅ |
| 2 | Implement Goosebump Engine (`.frisson()`) | ✅ |
| 2 | Render 9 master WAVs via FluidSynth | ✅ |
| 2 | FFmpeg loudnorm to -14 LUFS (Spotify target) | ✅ |
| 3 | A/B test frisson on Track 6 | ✅ verified safe |
| 3 | Cover art (Mandelbrot 3000×3000) | ✅ `cover_art.jpg` |
| 3 | Remotion 10-track video pipeline | ✅ wired + test render passed |
| 3 | Wire ThueMorse + add Track 10 | ✅ 92.46 (highest score) |
| 3 | Add tension arc to builder | ✅ avg +1.46, zero regressions |
| 3 | Re-render all 10 masters with tension arc | ✅ |
| 3 | Normalize all 10 to -14 LUFS | ✅ |
| 3 | Complete liner notes | ✅ |
| 3 | Distribution metadata + launch copy | ✅ |
| 4 | Render 10 videos | ⏳ `cd viz && bash render_album.sh` |
| 4 | DistroKid signup + upload | ⏳ |
| 4 | Social launch | ⏳ |

## Tracklist

All 10 tracks pass L1 (zero rule violations). Average eval score **90.68/100**.

| # | Track | Pattern | Key | Seed | Eval | Tension |
|---|---|---|---|---|---|---|
| 1 | Threshold | fibonacci | Bb_minor | 3 | 91.01 | 87.6 |
| 2 | The Infinite Series | infinity_series | C_major | 1 | **92.57** | 92.4 |
| 3 | Golden Spiral | golden_spiral | A_minor | 11 | 90.81 | 86.7 |
| 4 | Harmonic Series | harmonic_series | E_minor | 11 | 92.33 | 91.7 |
| 5 | Logistic Map (r=3.7) | logistic | D_major | 3 | 90.99 | 88.3 |
| 6 | Mandelbrot Boundary | mandelbrot | E_minor | 2 | 91.48 ⭐ | 88.4 |
| 7 | Rössler's Strange Attractor | rossler | E_minor | 10 | 87.81 | 77.4 |
| 8 | Cantor's Dust | cantor | F#_minor | 3 | 86.93 | 70.2 |
| 9 | Zipf's Law | zipf | F#_minor | 8 | 90.38 | **95.4** |
| 10 | Thue-Morse Resolution | thue_morse | G_major | 11 | 92.46 | 89.7 |

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
├── cover_art.jpg               (3000×3000, gitignored)
├── metadata.json               (distribution metadata)
├── launch_copy.md              (social launch drafts)
├── seeds/                      (search results, top-20 per pattern)
├── masters/                    (raw FluidSynth renders, gitignored)
├── normalized/                 (FFmpeg loudnorm -14 LUFS, gitignored)
└── liner_notes/
    └── README.md               (album notes with track descriptions)
```

## Remotion Video Pipeline

```bash
# 1. Export composition data
python examples/album/export_viz_data.py

# 2. Copy audio to viz/public/
python examples/album/copy_audio_to_viz.py

# 3. Render all 10 videos (~45 min each at 60fps)
cd viz && bash render_album.sh
```

## Reproducibility

Every track is regeneratable bit-identically from `seeds.json`:
```bash
python examples/album/render_masters.py
```

## Runtime

~28 minutes total (9 tracks at ~2:43, track 7 at ~3:43, track 10 at ~2:46).
