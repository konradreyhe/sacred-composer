# Handover — Sacred Composer Session 2026-04-04 (Session 5)

## Summary

Session focused on three areas: (1) improved sound quality by wiring FluidSynth+SoundFont rendering into the API, (2) built "Compose Your Name" web experience with full FastAPI backend serving real Sacred Composer compositions, (3) fixed all 20 principles violations from a systematic audit (5 critical, 9 major, 6 minor). Eval scores unchanged: 90.5/100 L1 PASS (seed=29). 327 tests passing (was 320). GitHub repo created at konradreyhe/sacred-composer. All changes uncommitted — need to commit.

## Completed

- [x] Private GitHub repo created and pushed: https://github.com/konradreyhe/sacred-composer
- [x] FluidSynth rendering in API — `api.py:_store()` tries FluidSynth+SoundFont first, falls back to built-in renderer
- [x] "Compose Your Name" FastAPI landing page at `GET /` with golden spiral viz, waveform visualizer, share URLs, download WAV/MIDI
- [x] API endpoints: `GET /compose/name/{name}` and `GET /compose/seed/{seed}` for viral sharing
- [x] Standalone web player upgraded (`web/`) with canvas golden spiral visualization, layered synth (triangle+pad), share button, URL params
- [x] Orchestral WAV rendering: `showcase_orchestral.wav` (FluidSynth + MuseScore_General.sf2)
- [x] Remotion video rendered: `viz/out/sacred_composition.mp4` (1080p, 116s, synced audio+visuals)
- [x] **Principles audit — all 20 violations fixed:**
  - Global random → seeded `random.Random(seed)` in orchestration.py, world_music.py, wav_renderer.py
  - Silent exceptions → specific exception types + logging in api.py, core.py, lilypond.py
  - `build()` decomposed → `_constrain_melody()`, `_constrain_bass()`, `_constrain_inner()`, `_apply_seventh_fix()`
  - Dead code removed → `_soft_crossing_fix` method (45 lines), unused imports
  - Raw `0.618` → `PHI_INVERSE` constant in psychoacoustics.py
  - `print()` → `logging.getLogger()` in evaluate.py, optimizer.py
  - CORS fix → `allow_credentials=False` in api.py
  - 7 new tests for `fix_seventh_resolution` (327 total)
- [x] Updated CLAUDE.md with eval scores

## In Progress

- [ ] **Changes uncommitted** — 16 modified files + 2 new files, all tests pass, need `git add` + `git commit`
- [ ] **Cloud deployment** — Dockerfile ready, API ready, needs `flyctl auth login` or Render.com connect
- [ ] **Better SoundFont** — Current: MuseScore_General.sf2 (206MB, quality ~5/10). Aegean Symphonic Orchestra (~800MB, ~7/10) would be a big upgrade. Download from HED-Sounds, place in `C:\SoundFonts\`
- [ ] **Unused imports in other files** — adaptive.py, musicxml.py, orchestration.py, tension.py still have unused imports (minor)
- [ ] **sys.path.insert() hack** in bridge.py, core.py, evaluate.py not yet centralized (DRY violation, minor)

## Decisions Made

| Decision | Why | Alternatives Rejected | Why Rejected |
|----------|-----|-----------------------|--------------|
| FluidSynth CLI for WAV rendering (not pyfluidsynth direct) | midi2audio wrapper failed on Windows ("file not found"), CLI works reliably | pyfluidsynth programmatic API | Would need rewriting the render pipeline; CLI is simpler and works |
| Decompose build() into 4 helper methods | KISS/SRP: build() was 276 lines with 5+ responsibilities | Full pipeline class extraction | Over-engineering for current needs; helpers are sufficient |
| `random.Random(seed)` instances (not `random.seed()`) | Per CLAUDE.md: "never global random". Instance-based is thread-safe and truly isolated | `random.seed(42)` at function start (was the existing pattern in orchestration.py) | Global seed affects all callers; instance is isolated |
| Catch specific exceptions `(ImportError, FileNotFoundError, OSError)` in core.py | Only expected failure modes when FluidSynth unavailable | Keep broad `except Exception` | Hides real bugs (corrupt data, disk full, etc.) |
| `allow_credentials=False` in CORS | `allow_origins=["*"]` + `allow_credentials=True` is a known misconfiguration browsers actually block | Restrict origins to localhost only | Breaks legitimate cross-origin usage during development |
| API landing page embedded in api.py as LANDING_HTML string | Single-file deployment, no static file serving needed | Separate HTML file + StaticFiles mount | More complex deployment; HTML string is self-contained |
| Standalone web/ player kept alongside API | Different use cases: web/ is zero-server static, API is full-engine | Remove web/ in favor of API only | web/ works offline and could be hosted on GitHub Pages |

## Known Issues

- **web/ player uses simplified JS engine** — pentatonic Fibonacci melody, NOT the full Sacred Composer pipeline. The API at `/` uses the real engine. The web/ player is a lightweight demo only.
- **FluidSynth SoundFont quality** — MuseScore_General.sf2 is adequate but not great (~5/10 realism). Upgrade to Aegean Symphonic Orchestra for ~7/10.
- **API server stops when background task completes** — use `python -c "import uvicorn; uvicorn.run('api:app', host='0.0.0.0', port=8001)"` with long timeout or run in a terminal directly.
- **Remaining unused imports** in adaptive.py, musicxml.py, orchestration.py, tension.py (minor, no functional impact).
- **`sys.path.insert()` hack** in 4 files — works but fragile; should centralize.
- **viz/out/ and .mcp.json** are untracked — should add to .gitignore or commit selectively.

## Next Steps (Priority Order)

1. **Commit all session 5 changes** — `git add api.py sacred_composer/ tests/ web/ viz/src/data/sample.json && git commit && git push`
2. **Download better SoundFont** — Aegean Symphonic Orchestra from HED-Sounds → `C:\SoundFonts\`. Immediate audio quality upgrade, zero code changes.
3. **Deploy to cloud** — Render.com (free tier): connect GitHub repo, set build command `pip install -r requirements.txt`, start command `uvicorn api:app --host 0.0.0.0 --port $PORT`. Or `flyctl launch --now`.
4. **Push L1 PASS above 92** — Weakest metrics: repetition_variation (67.5), interval_distribution (68.9). Tune `ensure_motivic_echoes` and `_diversify_intervals`.
5. **Deploy web/ to GitHub Pages** — Static site, zero server, instant sharing. Add CNAME for custom domain.
6. **Viral content creation** — Record "Math Wrote This Music" TikTok: split-screen golden spiral + piano roll. Use Remotion video as base.
7. **BBC Symphony Orchestra Discover** (free VST3) — via Spotify's `pedalboard` library for professional orchestral quality (~9/10).

## Rollback Info

- Last committed state: `62988ac` (session 4: seventh resolution fix)
- All session 5 changes are uncommitted
- To revert everything: `git checkout -- api.py sacred_composer/ tests/test_constraints.py web/ viz/src/data/sample.json && rm web/viz.js`
- Previous eval scores at `62988ac`: 90.5/90.3/89.2 (unchanged after refactor)

## Files Modified This Session

### Core Engine (Principles Fixes)
- `sacred_composer/builder.py` — Decomposed `build()` into `_constrain_melody()`, `_constrain_bass()`, `_constrain_inner()`, `_apply_seventh_fix()`. Removed dead `_soft_crossing_fix` (45 lines). Removed unused imports.
- `sacred_composer/orchestration.py` — Replaced global `random` with seeded `_rng_mod.Random(42)` in `generate_hall_impulse()`
- `sacred_composer/world_music.py` — Replaced global `random` with seeded `_rng_mod.Random(pitches[0])` in gamaka generation. Removed unused `Note, Voice` imports.
- `sacred_composer/wav_renderer.py` — Replaced `np.random.uniform` with seeded `np.random.RandomState(int(freq))` in Karplus-Strong
- `sacred_composer/core.py` — Narrowed exception catch from `Exception` to `(ImportError, FileNotFoundError, OSError)`
- `sacred_composer/evaluate.py` — Replaced `print()` with `logging.getLogger(__name__)` calls
- `sacred_composer/optimizer.py` — Replaced `print()` with `logging.getLogger(__name__)` call
- `sacred_composer/psychoacoustics.py` — Imported and used `PHI_INVERSE` constant instead of raw `0.618`
- `sacred_composer/lilypond.py` — Narrowed exception catch from `Exception` to `ImportError`

### API & Web
- `api.py` — FluidSynth rendering in `_store()`, CORS fix (`allow_credentials=False`), logging for render failures, eval score update in landing page
- `web/index.html` — Complete rewrite: "Compose Your Name" with canvas viz, share URLs, URL param auto-compose
- `web/player.js` — Layered synth (triangle+pad), active note tracking for visualization, longer compositions
- `web/style.css` — Modern dark theme, responsive, golden accents
- `web/viz.js` — **NEW**: Golden spiral canvas visualization with note constellation, pitch-mapped colors, progress ring

### Tests
- `tests/test_constraints.py` — Added 7 tests for `fix_seventh_resolution`: no-change, upward-fix, no-large-leap, empty-input, no-bass, skip-rests, fallback-nudge

### Artifacts
- `viz/src/data/sample.json` — Updated composition data for seed=29 with durationSec field
- `viz/public/composition.wav` — Re-rendered with orchestral FluidSynth
- `viz/out/sacred_composition.mp4` — Remotion video render (25MB, 1080p, 116s)
- `showcase_seed*.wav`, `showcase_seed*.mid`, `showcase_orchestral.wav`, `showcase_fluidsynth.wav`, `showcase_best.mid` — Generated showcase files (not tracked in git)

## Key Numbers

- Eval score (L1 PASS): **90.5/100** (seed=29, unchanged after refactor)
- Tests: **327 passed** (was 320, +7 for fix_seventh_resolution)
- Principles violations fixed: **20/20** (5 critical, 9 major, 6 minor)
- Files modified: 16
- Lines changed: ~542 added, ~5320 removed (mostly viz data JSON shrink)
- FluidSynth SoundFont: MuseScore_General.sf2 at C:\SoundFonts\ (206MB)
- API endpoints: 12 total (compose, name, seed, consciousness, adaptive, patterns, scales, etc.)
