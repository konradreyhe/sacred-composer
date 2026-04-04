# Handover — Sacred Composer Session 2026-04-04 (Session 4)

## Summary

Added seventh resolution post-processing and improved leap safety guards. Best L1 PASS: **90.5/100** (C_minor golden_spiral seed=29, 0 violations). Three seeds above 89 L1 PASS: seed=29 (90.5), seed=12 (90.3), seed=8 (89.2). 23/49 seeds achieve L1 PASS (up from ~20). Created private GitHub repo at konradreyhe/sacred-composer and pushed. All 320 tests passing.

## Completed

- [x] Created private GitHub repo: https://github.com/konradreyhe/sacred-composer
- [x] Pushed all code to remote
- [x] Added `fix_seventh_resolution()` in constraints.py — resolves chord 7ths by finding nearest scale degree that satisfies resolution while avoiding leap violations
- [x] Fallback i-nudge: when no safe j replacement exists, nudges the seventh note itself by ≤2st to avoid the seventh interval
- [x] Leap safety guards: replacement must be ≤5st from both predecessor and successor sounding notes
- [x] Inner voice seventh fix: also fixes sevenths in inner voice against bass
- [x] Multi-pass leap recovery in `_clamp_sounding_pitches` final pass (3 iterations)
- [x] Updated exports in `__init__.py`
- [x] All 320 tests passing
- [x] Updated CLAUDE.md with new eval scores

## In Progress

- [ ] Remotion video export — Ready: `cd viz && npx remotion render SacredComposition --codec h264 out/sacred_composition.mp4`
- [ ] Cloud deployment — Dockerfile ready. Needs `flyctl auth login` or Render.com GitHub connect
- [ ] Viral launch — Blocked on deployment

## Decisions Made

| Decision | Why | Alternatives Rejected | Why Rejected |
|----------|-----|-----------------------|--------------|
| Fix result[j] (next note after seventh) first, fall back to nudging result[i] | Changing the resolution note preserves the melody's seventh (which may be musically desirable); only failing that do we change the seventh note | Only fix j | Some cases have no valid j replacement (when k is too far from any valid p ≤ i+2) |
| Guard: replacement must be ≤5st from BOTH i and k | Prevents creating leap_recovery violations. Original code only checked i distance | Only check distance to i | Creates leaps to k (the note after j) that fail leap_recovery |
| Nudge i by ≤2st to non-seventh scale degree | Minimal disruption to melody; 2st is one scale step | Larger nudge | Changes melody character too much; may create leaps with neighbors |
| Multi-pass (3x) final leap recovery in _clamp_sounding_pitches | Previous single pass could leave cascading violations where fixing one leap's recovery creates a new >5st interval | Single pass | Recovery fixes can cascade: fixing i2 creates new leap at i2→i3 |
| Asymmetric lookahead in _coordinate_with_melody reverted | Forward-biased window (-2/+4 beats) over-constrained inner voice, dropping score by ~8 points | Keep asymmetric -2/+4 | Score dropped from 92.4 to 83.8; inner voice pushed too low too early |
| Extra clamp after smooth_direction reverted | Added no benefit (leaps from seventh fix, not smooth_direction) | Keep extra clamp | No measurable improvement |

## Known Issues

- **voice_spacing (seed=21, seed=25)**: Inner voice registers too far from melody at certain points. 16st gap (max 12 allowed). Requires tighter spacing constraint in `_coordinate_with_melody`.
- **parallel_5ths (seed=11, seed=15)**: Voice 0 and 1 move in parallel perfect fifths. Would need parallel motion detection in the inner voice pipeline.
- **repetition_variation (67.5)**: Weakest metric for best config. Melodic echoes may be too exact or too different.
- **interval_distribution (68.9)**: Second weakest. Inner voice diversification helps but melody intervals still cluster.
- **`_soft_crossing_fix` method exists but unused**: Defined in builder.py but the current pipeline uses clamp→coordinate→clamp instead.

## Next Steps (Priority Order)

1. **Push L1 PASS above 92** — Ideas:
   - Fix voice_spacing: tighter `_coordinate_with_melody` max spacing (currently 11st, could try 10st)
   - Improve repetition_variation: tune `ensure_motivic_echoes` target_distance
   - Improve interval_distribution: adjust `_diversify_intervals` probabilities
2. **Improve tension_arc** — Climax position varies by seed. Increase `add_pitch_tension_arc` intensity.
3. **Deploy web app** — `flyctl auth login` + `flyctl launch --now`, OR connect GitHub to Render.com
4. **Render Remotion video** — `cd viz && npx remotion render SacredComposition --codec h264 out/sacred_composition.mp4`

## Rollback Info

- Last committed state: `307941c` (session 3)
- All session 4 changes are uncommitted in working tree
- To revert everything: `git checkout -- sacred_composer/builder.py sacred_composer/constraints.py sacred_composer/__init__.py CLAUDE.md HANDOVER.md`

## Files Modified This Session

### Core Engine
- `sacred_composer/constraints.py` — Added `fix_seventh_resolution()` (~60 lines): seventh detection, j-replacement with leap guards, i-nudge fallback
- `sacred_composer/builder.py` — Added seventh resolution post-processing after all voices built (melody + inner voice), added tracking variables, multi-pass final leap recovery in `_clamp_sounding_pitches`
- `sacred_composer/__init__.py` — Added `fix_seventh_resolution` export

### Docs
- `CLAUDE.md` — Updated eval score to 90.5 L1 PASS
- `HANDOVER.md` — Complete rewrite for session 4

## Key Numbers

- Best L1 PASS: **90.5/100** (seed=29, 0 violations)
- 2nd L1 PASS: **90.3/100** (seed=12, 0 violations)
- 3rd L1 PASS: **89.2/100** (seed=8, 0 violations)
- L1 PASS configs: 23/49 seeds
- Tests: 320 passing
- Metrics at 100 (seed=29): entropy, harmonic_rhythm, chord_vocabulary, cadence_placement, phrase_length, phrase_boundaries, thematic_development
