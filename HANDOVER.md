# Session Handover

**Date:** 2026-04-07 (Session 15, Album seed optimization)
**Duration:** ~45 min
**Goal:** Boost weakest album tracks via grid search + builder improvements.

## Summary

Session 15 focused on raising the album's average eval score by finding
better seed/key combinations for the weaker tracks. Ran grid searches
(300-600 candidates per pattern) across all 12 keys × 20-30 seeds.

**5 tracks improved**, album average: **91.22** (was 90.70, +0.52):

| Track | Pattern | Old | New | Delta | Change |
|-------|---------|-----|-----|-------|--------|
| 1 | fibonacci | 91.01 | 92.24 | +1.23 | seed 3→26 |
| 3 | golden_spiral | 90.81 | 91.12 | +0.31 | A_minor s11→D_major s9 |
| 5 | logistic | 90.99 | 92.43 | +1.44 | D_major s3→C#_minor s18 |
| 8 | cantor | 86.93 | 88.04 | +1.11 | seed 3→10 |
| 9 | zipf | 90.38 | 91.51 | +1.13 | F#_minor s8→Bb_minor s26 |

**Builder improvements attempted but reverted:**
- Enhanced `smooth_direction` (2-note blip fix + 3st nudge): caused regressions on 7/10 tracks
- Increased `add_pitch_tension_arc` intensity (0.50→0.65): -6.74 regression on Track 4
- Density-smoothing post-process: removed notes hurt other metrics more than helped TM

**Key finding:** Rossler (Track 7, 87.81) is at its ceiling. 600-candidate search found nothing better. The chaotic attractor inherently produces zigzag melodies (mean_run=1.56) and abrupt density changes (transition_motivation=66.67) that no builder tweak could fix without breaking other tracks.

## What Got Done

- [x] Grid search: rossler 600 candidates (no improvement found, confirmed 87.81 ceiling)
- [x] Grid search: cantor 600 candidates → seed 10 at 88.04 (+1.11)
- [x] Grid search: zipf 300 candidates → Bb_minor seed 26 at 91.51 (+1.13)
- [x] Grid search: fibonacci 360 candidates → seed 26 at 92.24 (+1.23)
- [x] Grid search: golden_spiral 240 candidates → D_major seed 9 at 91.12 (+0.31)
- [x] Grid search: logistic 240 candidates → C#_minor seed 18 at 92.43 (+1.44)
- [x] Updated seeds.json with all new configs
- [x] Updated CLAUDE.md eval score section
- [x] All 329 tests passing
- [x] Full end-to-end verification: all 10 tracks match seeds.json scores
- [x] Re-rendered all 10 master WAVs via FluidSynth
- [x] Normalized all 10 tracks to -14 LUFS (Spotify target) via FFmpeg
- [x] GitHub Pages workflow (`.github/workflows/pages.yml`)
- [x] OG image for web player social sharing (1200x630 from Mandelbrot cover)
- [x] Updated metadata.json track durations from actual renders
- [x] Updated liner notes with new seeds/keys/scores

## What's In Progress

Nothing. All work completed.

## What Didn't Get Done

- **Human listening** — still needed (tracks in `examples/album/normalized/`)
- **Video rendering** — `cd viz && bash render_album.sh` (~7.5 hours)
- **DistroKid signup** — requires human
- **Push to origin** — now 57+ commits ahead; after push, GitHub Pages will auto-deploy
- **Enable GitHub Pages** — after push, go to repo Settings > Pages > Source: GitHub Actions

## Architecture & Design Decisions

| Decision | Chosen | Why | Rejected | Why Rejected |
|---|---|---|---|---|
| Rossler improvement | Accept 87.81 ceiling | 600 candidates searched, chaotic pattern inherently limits TM/DM metrics | Builder modifications | Every attempted change (smooth_direction, pitch_tension_arc, density smoothing) caused regressions on other tracks |
| Seed search breadth | 20-30 seeds × 8-12 keys per pattern | Diminishing returns beyond this; key findings emerge within first 300 candidates | Exhaustive 100+ seeds | Diminishing returns, time cost |
| Keep Bb_minor for Track 9 | Key reuse is OK | Album already has 3× E_minor, 2× F#_minor — uniqueness not required | Unique keys only | Would sacrifice 91.51 score for aesthetic constraint |

## Known Issues & Risks

- **Track 7 (rossler) still weakest** at 87.81 — structural limitation of the pattern
- **Track 8 (cantor) second-weakest** at 88.04 — improved but still below 90
- **Masters need re-rendering** since seeds changed for 5 tracks
- **52+ commits not pushed** — `git push origin master`
- **No human listening feedback** yet

## Next Steps (Priority Order)

### 1. **Listen to all 10 normalized tracks** (~30 min, human task)
```
examples/album/normalized/
```

### 2. **Push commits to origin** (deploys web player via GitHub Pages)
```bash
git push origin master
```
Then: repo Settings > Pages > Source: GitHub Actions

### 3. **Render all 10 videos** (~7.5 hours, run overnight)
```bash
cd C:/Users/kreyh/Projekte/MUSIK/viz && bash render_album.sh
```

### 4. **DistroKid signup + upload** (~2 hours + 2-4 week propagation)

### 5. **Social launch** — copy in `examples/album/launch_copy.md`

## Rollback Plan

- **Last known good:** `7e0a904` (session 14 HEAD) — before seed changes
- **Rollback seed changes:** `git checkout 7e0a904 -- examples/album/seeds.json CLAUDE.md`
- **Rollback session 14:** `git reset --hard 1dcf1a9`

## Files Changed This Session

**Modified (6 files):**
- `examples/album/seeds.json` — updated 5 track configs with better seeds/keys
- `examples/album/metadata.json` — corrected track durations
- `examples/album/liner_notes/README.md` — updated seeds/keys/scores for 5 tracks
- `examples/album/seeds/search_rossler.csv` — new search results
- `examples/album/seeds/search_cantor.csv` — new search results
- `CLAUDE.md` — updated eval score section

**Added (2 files):**
- `.github/workflows/pages.yml` — GitHub Pages deployment for web player
- `web/og-image.jpg` — 1200x630 OG image for social sharing

**Modified (1 file, web):**
- `web/index.html` — added OG image + twitter:image meta tags

**Re-rendered (not in git, gitignored):**
- `examples/album/masters/*.wav` — all 10 tracks
- `examples/album/normalized/*.wav` — all 10 tracks at -14 LUFS

## Open Questions (inherited)

1. **Artist name** — kreyh, "Chorda", or "Sacred Composer"?
2. **License** — commercial or CC-BY?
3. **Release cadence** — all 10 at once, or singles?
4. **Video quality** — 60fps (45 min/track) or 30fps (22 min/track)?
5. **Deploy web player?** — GitHub Pages, Netlify, or Vercel?
