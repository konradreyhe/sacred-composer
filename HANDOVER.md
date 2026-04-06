# Session Handover

**Date:** 2026-04-06 (Session 14, Three.js 3D sacred geometry + visual polish)
**Duration:** ~1 hour
**Goal:** Replace 2D canvas with Three.js 3D sacred geometry per pattern, then iteratively polish layout and visuals.

## Summary

Session 14 had two phases:

**Phase 1 — Three.js 3D Engine:** Replaced the web player's 2D canvas visualization
with a full Three.js 3D engine. Each of the 6 patterns now renders a unique
sacred/nature geometry that rotates, breathes, and reacts to the music.

**Phase 2 — Visual Iteration & Polish:** Ran a systematic visual iteration loop
(7 cycles) to refine layout, spacing, and visual quality across desktop and mobile.

**Visualizations (per pattern):**
- Fibonacci → Phyllotaxis Sphere (sunflower seeds on sphere, dual icosahedra, equatorial ring)
- Golden Spiral → Flower of Life (25 torus rings, 3 layers, vesica piscis highlights)
- Harmonic → Cymatics (vertex-colored Chladni plate, dual wave modes, particle sand on nodes)
- Logistic → Lorenz Attractor (5000-point gradient trail, glowing head + additive aura)
- Thue-Morse → Fractal Tree (color-gradient branches, pollen particles, wind sway)
- Mandelbrot → 3D Terrain (banded fractal coloring, edge-glow particles, 80x80 mesh)

**Shared 3D effects (all patterns):**
- Starfield background (300 golden particles on rotating sphere shell)
- Progress ring (golden arc fills during playback)
- Camera breathing (subtle z/x/y oscillation)
- Additive glow auras on active notes (pool of 8 sprites)
- Sacred connection lines between simultaneous notes
- Ambient dust particles per pattern

**Layout/CSS improvements:**
- Desktop (720px+): wider container (800px max), 2:1 viz aspect ratio
- Everything above the fold — no scrolling needed to reach Play button
- Empty state: vertically centered for inviting first impression
- Play button: gold glow + shadow as clear primary action
- Controls card: gradient background + drop shadow
- Stronger overlay gradient + text shadow for readability
- Tighter spacing throughout (header, inputs, cards)

3 commits landed this session (now 52 ahead of origin).

## What Got Done

- [x] Three.js 3D engine replacing 2D canvas (viz.js complete rewrite)
- [x] 6 distinct sacred geometry visualizations (one per pattern)
- [x] Starfield background, progress ring, camera breathing
- [x] Glow auras, sacred connections, ambient dust
- [x] Enhanced cymatics (vertex colors, dual waves, particle sand)
- [x] Desktop responsive layout (800px wide, 2:1 aspect)
- [x] Empty state vertical centering
- [x] Play button prominence (glow + shadow)
- [x] Controls card visual upgrade (gradient + shadow)
- [x] Overlay text readability (stronger gradient + text shadow)
- [x] Visual verification: all 6 patterns on desktop
- [x] Visual verification: mobile (375px) layout
- [x] Visual verification: playback state with active notes
- [x] All pattern buttons on one line (desktop)

## What's In Progress

Nothing. All work completed and committed.

## What Didn't Get Done

- **Human listening** — still needed
- **Video rendering** — `cd viz && bash render_album.sh` (~7.5 hours)
- **DistroKid signup** — requires human
- **Push to origin** — 52 commits ahead, waiting for user

## Architecture & Design Decisions

| Decision | Chosen | Why | Rejected | Why Rejected |
|---|---|---|---|---|
| 3D engine | Three.js v0.160.0 from CDN | Proven, no build step, UMD global | R3F/WebGPU | Needs bundler, overkill for standalone HTML |
| Viz aspect ratio | 2:1 on desktop, 1:1 on mobile | Fits everything above fold on 768px viewport | Square everywhere | Wastes vertical space on desktop |
| Note glow | Additive-blended sprite pool (8) | Reusable, no per-frame allocation, visible glow | Per-note glow mesh | Too many objects, expensive dispose |
| Cymatics color | Vertex colors (gold peaks, blue nodes) | Shows wave structure clearly, visually rich | Uniform wireframe | Lost the interesting Chladni topology |
| Starfield | 300 points on golden-angle sphere shell | Consistent with sacred geometry theme, subtle depth | Random distribution | Less aesthetically coherent |
| Empty state | CSS :has() vertical centering | Modern, no JS, seamless transition when viz appears | JS-based toggle | More complex, flash of wrong layout |

## Known Issues & Risks

- **No human listening feedback** — eval ≠ taste
- **Track 7 still weakest** (87.81) — structural Rossler limitations
- **Track 8 second-weakest** (86.93) — tension_arc and repetition_variation
- **10 videos not rendered** — ~7.5 hours overnight
- **52 commits not pushed** — `git push origin master`
- **CSS :has() selector** — supported in all modern browsers but not IE/old Edge

## Next Steps (Priority Order)

### 1. **Listen to all 10 normalized tracks** (~30 min, human task)
```
examples/album/normalized/
  01_threshold.wav through 10_thue-morse_resolution.wav
```

### 2. **Render all 10 videos** (~7.5 hours, run overnight)
```bash
cd C:/Users/kreyh/Projekte/MUSIK/viz && bash render_album.sh
```

### 3. **Push 52 commits to origin**
```bash
git push origin master
```

### 4. **DistroKid signup + upload** (~2 hours + 2-4 week propagation)

### 5. **Social launch** — copy in `examples/album/launch_copy.md`

### 6. **Deploy web player** — fully standalone HTML/JS, could go on GitHub Pages or Netlify

## Rollback Plan

- **Last known good:** `5a6dbf7` (current HEAD) — CSS polish
- **Rollback CSS polish only:** `git reset --hard 99b5083` — Three.js viz without layout changes
- **Rollback session 14 entirely:** `git reset --hard 1dcf1a9` — back to session 13 (2D canvas)
- **Rollback session 13+14:** `git reset --hard fc86047` — back to session 12 end

## Files Changed This Session

**Modified (4 files):**
- `web/viz.js` — complete rewrite: Three.js 3D engine, 6 sacred geometry patterns, starfield, glow, connections, dust (~700 lines)
- `web/player.js` — added `patternKey` field to composition object
- `web/index.html` — added Three.js v0.160.0 CDN script tag
- `web/style.css` — responsive layout (800px/2:1), vertical centering, button polish, overlay readability

## Open Questions (inherited)

1. **Artist name** — kreyh, "Chorda", or "Sacred Composer"?
2. **License** — commercial or CC-BY?
3. **Release cadence** — all 10 at once, or singles?
4. **Video quality** — 60fps (45 min/track) or 30fps (22 min/track)?
5. **Deploy web player?** — GitHub Pages, Netlify, or Vercel?
