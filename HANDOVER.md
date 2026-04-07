# Session Handover

**Date:** 2026-04-07 (Session 15)
**Duration:** ~1 hour
**Goal:** Boost weakest album tracks and advance toward release readiness.

## Summary

Session 15 focused on raising the album's eval score by finding better
seed/key combinations for the weaker tracks. I ran grid searches across
300–600 candidates per pattern (seeds × 12 keys), which found significantly
better configs for 5 of the 10 tracks. The album average rose from 90.70
to **91.22** — the biggest single-session improvement since the tension arc
was added in session 12.

I also attempted three builder-level improvements (enhanced smooth_direction,
increased pitch_tension_arc intensity, density-smoothing post-process), but
all caused regressions on other tracks and were reverted. The key insight:
the constraint pipeline is well-balanced — any change that helps one pattern
breaks another. Seed selection is the right lever for per-track optimization.

After locking the new seeds, I re-rendered all 10 master WAVs via FluidSynth,
normalized them to -14 LUFS (Spotify target), added a GitHub Pages deployment
workflow for the web player, created an OG image for social sharing, and
updated all documentation (liner notes, metadata, CLAUDE.md).

5 commits landed. The project is now fully release-ready pending human
listening and a `git push`.

## What Got Done

- [x] Grid search optimization — 5 tracks improved, album average 90.70 → 91.22
- [x] Re-rendered all 10 master WAVs with updated seeds via FluidSynth
- [x] Normalized all 10 tracks to -14 LUFS via FFmpeg loudnorm
- [x] GitHub Pages deployment workflow (`.github/workflows/pages.yml`)
- [x] OG image for web player (1200×630, resized from Mandelbrot cover art)
- [x] Updated `web/index.html` with OG/twitter:image meta tags
- [x] Updated `seeds.json`, `metadata.json`, liner notes, CLAUDE.md
- [x] End-to-end verification: all 10 tracks match seeds.json scores exactly
- [x] All 329 tests passing

## What's In Progress

Nothing. All work completed and committed.

## What Didn't Get Done (and Why)

- **Human listening** — requires a human with headphones (~30 min)
- **Video rendering** — ~7.5 hours, needs to run overnight
- **Push to origin** — waiting for user decision (57+ commits ahead)
- **DistroKid signup** — requires human account creation
- **GitHub Pages enablement** — requires push first, then repo Settings toggle

## Architecture & Design Decisions

| Decision | Chosen | Why | Rejected | Why Rejected |
|---|---|---|---|---|
| Track improvement | Seed search | Per-track, zero regression risk | Builder changes | Every builder change regressed other tracks |
| enhanced smooth_direction | Reverted | 2-note blip fix + 3st nudge caused -4.81 to -8.02 regressions on 7/10 tracks | — | Pitch changes cascade through interval_distribution, repetition_variation |
| pitch_tension_arc 0.65 | Reverted | Track 4 regressed -6.74, Track 7 -5.67 | — | Too aggressive for patterns that already have good arcs |
| density smoothing | Reverted | Removing notes hurt other metrics more than helped transition_motivation; Track 8 TM dropped from 66.7 to 62.5 | — | Note removal is destructive to phrase structure |
| Rossler score | Accept 87.81 | 600 candidates searched; chaotic attractor inherently produces zigzag melody (mean_run=1.56) and density spikes (TM=66.67) | — | No seed/key found above 87.81 with L1 pass |
| GitHub Pages | Static deploy of web/ | No build step needed, standalone HTML/JS/CSS + CDN | Netlify/Vercel | Overkill for static files in existing GitHub repo |

## Mental Model

### How the Eval Metrics Interact

The 14-metric evaluation framework creates a complex optimization landscape.
The key constraint: **metrics are coupled through the music**. Changing pitches
to improve `directional_momentum` (needs mean_run ≥ 2.0) wrecks
`interval_distribution` (needs step ratio ~50%) and `repetition_variation`
(needs motivic echoes of the opening). Similarly, removing notes to smooth
`transition_motivation` (density jumps) destroys `phrase_boundaries` and
`repetition_variation`.

**The current constraint pipeline is a careful balance.** Each step was
tuned to not regress other metrics. Adding new steps or modifying parameters
requires testing ALL 10 tracks — a single-track improvement that regresses
the average is a net loss.

### Per-Pattern Limitations

Some patterns have inherent metric ceilings:
- **Rossler**: Chaotic attractor produces zigzag pitch sequences (mean_run ≈ 1.56).
  No amount of `smooth_direction` nudging can fix this without breaking other metrics.
  `transition_motivation` and `directional_momentum` are structurally limited.
- **Cantor**: Fractal rhythm creates sparse/dense alternation. Better than rossler
  but still limited on density metrics.
- **Infinity series / Thue-Morse**: These patterns naturally produce good directional
  runs and tension arcs. They score 92+ easily.

### Seed Search Economics

Diminishing returns kick in around 300 candidates. The best seeds typically
emerge within the first 15 seeds per key, and across 8-12 keys. Going to 50
seeds × 12 keys (600 candidates) is thorough but rarely finds anything beyond
what 20 × 12 finds. Seed 10, 18, and 26 recurred as strong seeds across
multiple patterns.

### The transition_motivation Metric

This metric is effectively quantized at 66.67, 71.43, 83.33 because it
uses p90 of bar-to-bar density jumps, and with integer note counts in 48
bars, the possible jump values are discrete. Moving a track from the 66.67
bucket to 71.43 requires reducing the 5th-largest density jump by ~1 note.
This is nearly impossible to do surgically.

## Known Issues & Risks

- **Track 7 (rossler) at 87.81** — structural ceiling, not a bug. Accept it.
- **Track 8 (cantor) at 88.04** — improved but still below 90. Inherent pattern limitation.
- **Masters are gitignored** — re-render with `python examples/album/render_masters.py` if lost
- **57+ commits not pushed** — `git push origin master` when ready
- **GitHub Pages needs manual enablement** — Settings > Pages > Source: GitHub Actions
- **search_seeds.py temp file contention** — concurrent runs share `_tmp_search.mid`, causing ~30% error rate. Use unique temp files if running multiple searches.

## What Worked Well

- **Grid search** — simple, reliable, zero-regression way to optimize per-track scores
- **End-to-end verification** — running all 10 tracks after each change catches regressions early
- **Detailed metric breakdowns** — comparing specific metrics across all tracks reveals patterns
- **Background searches** — running multiple searches in parallel while analyzing results

## What Didn't Work (Traps to Avoid)

- **Modifying `smooth_direction`** — any pitch changes cascade through 5+ downstream metrics. Don't touch unless you have a very surgical change and test all 10 tracks.
- **Increasing `add_pitch_tension_arc` intensity** — above 0.50, some patterns (harmonic_series, rossler) regress badly. The current 0.50 is well-tuned.
- **Density smoothing via note removal** — removing even 1 note per bar in 6 bars wrecked phrase structure and repetition patterns. Note-level surgery is too destructive.
- **Concurrent `search_seeds.py`** — the script uses a shared temp file. Run one at a time, or modify to use unique temp paths.

## Next Steps (Priority Order)

### 1. Listen to all 10 normalized tracks (~30 min, human task)
```
examples/album/normalized/
  01_threshold.wav          (Bb_minor, fibonacci)
  02_the_infinite_series.wav (C_major, infinity_series)
  03_golden_spiral.wav      (D_major, golden_spiral)
  04_harmonic_series.wav    (E_minor, harmonic_series)
  05_logistic_map_r3_7.wav  (C#_minor, logistic)
  06_mandelbrot_boundary.wav (E_minor, mandelbrot) [FRISSON]
  07_rosslers_strange_attractor.wav (E_minor, rossler)
  08_cantors_dust.wav       (F#_minor, cantor)
  09_zipfs_law.wav          (Bb_minor, zipf)
  10_thue-morse_resolution.wav (G_major, thue_morse)
```

### 2. Push to origin + enable GitHub Pages
```bash
git push origin master
```
Then: GitHub repo → Settings → Pages → Source: "GitHub Actions"
Web player will be live at `https://<user>.github.io/MUSIK/`

### 3. Render 10 music videos (~7.5 hours, overnight)
```bash
cd C:/Users/kreyh/Projekte/MUSIK/viz && bash render_album.sh
```

### 4. DistroKid signup + upload (~2 hours + 2–4 week propagation)
Need to decide: artist name, license, release cadence (see Open Questions)

### 5. Social launch — copy ready in `examples/album/launch_copy.md`

## Rollback Plan

- **Last known good (pre-session 15):** `7e0a904`
- **Rollback only seed changes:** `git checkout 7e0a904 -- examples/album/seeds.json CLAUDE.md examples/album/metadata.json examples/album/liner_notes/README.md`
- **Rollback entire session 15:** `git reset --hard 7e0a904`
- **Rollback to session 13:** `git reset --hard 1dcf1a9`

## Files Changed This Session

**Commits (5):**
1. `822c66d` — `examples/album/seeds.json`, `CLAUDE.md`, search CSVs — seed optimization
2. `78a19e8` — `.github/workflows/pages.yml` — GitHub Pages deployment
3. `7ddce34` — `web/index.html`, `web/og-image.jpg`, `examples/album/metadata.json` — OG image + durations
4. `35cb103` — `examples/album/liner_notes/README.md` — updated seeds/keys/scores
5. `909e6a4` — `HANDOVER.md` — session handover

**Re-rendered (gitignored):**
- `examples/album/masters/*.wav` — all 10 tracks
- `examples/album/normalized/*.wav` — all 10 tracks at -14 LUFS

## Open Questions (inherited from previous sessions)

1. **Artist name** — kreyh, "Chorda", or "Sacred Composer"?
2. **License** — commercial or CC-BY?
3. **Release cadence** — all 10 at once, or singles?
4. **Video quality** — 60fps (45 min/track) or 30fps (22 min/track)?
5. **Web player URL** — will be `https://<user>.github.io/MUSIK/` after Pages setup
