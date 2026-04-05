# Handover — Sacred Composer Session 2026-04-05 (Session 7)

## Summary

Session focused on pushing eval score past 95/100 per user's "perfection" request (+ PRINCIPLES.md reference). **Net result: no gain, baseline remains 92.42** (Bb_minor golden_spiral seed=43, NOT seed=47 as claimed in previous HANDOVER). Tried 7 distinct approaches (duration scaling, tail padding, tapering tail, bass rhythm changes, form sections, inner voice, drone) — every one net-hurt the overall score due to structural metric conflicts. Working tree clean, all 327 tests passing. **Most important finding: the 94.0 claim in the previous handover is unreproducible on current HEAD — actual best is 92.42.** Also identified the metric conflict that blocks 95+ without multi-hour architectural work.

## Completed

- [x] **Reproduced baseline** — confirmed 92.42/100 L1 PASS (Bb_minor seed=43, NOT seed=47)
- [x] **Diagnosed weak metrics**: transition_motivation 71.4 (tail-off, bars 40-48 empty), chord_vocabulary 84.6 (ratio 0.11, 45/242 chords are single-pc Bb)
- [x] **Identified structural metric conflict**: tension_arc (wt 0.20) rewards density falling at end; transition_motivation (wt 0.10) penalizes the same fall as "abrupt jump"
- [x] **Traced density tail-off to source**: `apply_developing_variation` in variation.py shrinks phrase durations by ~20% (184.6→149.9 beats for a 192-beat piece)
- [x] **Classified inner-voice violations**: 45 voice_crossing, 15 leading_tone_res, 13 leap_recovery, 6 voice_spacing, 3 parallel_5ths across 20 seeds
- [x] **Tested 7 approaches** (all reverted — see Decisions table)
- [x] **Working tree clean**, 327 tests passing

## In Progress

- [ ] **Push eval past 95** — blocked by structural metric conflicts. Needs multi-hour architectural changes (see Next Steps).
- [ ] **Correct CLAUDE.md** — still claims 94.0 for seed=47; actual measured best is 92.42 for seed=43. Unclear whether 94.0 was from a different Python/music21 version or simply misreported.

## Decisions Made

| Decision | Why | Alternatives Rejected | Why Rejected |
|----------|-----|-----------------------|--------------|
| Keep baseline unchanged | No simple change net-improved score | (7 attempts below) | All net-hurt final score |
| Measure seed=43 as best, not seed=47 | On current HEAD, seed=43 scores 92.42 vs seed=47's 92.12 | Trust handover claim of seed=47→94.0 | Unreproducible on current environment |
| Don't scale variation phrase durations | Score dropped 92.4→86.9 | Preserve total phrase duration via multiplicative scaling | Stretched notes by 1.22x, broke bar alignment → tension_arc 87→54 |
| Don't pad tail with repeated phrases | Score 92.4→90.2 | Cycle through phrases from n//4 to n | Repeated content hurts repetition_variation (93→84) and phrase_boundaries (100→70) |
| Don't add tapering tail | Score 92.4→91.8 | Decaying velocity + density over remaining bars | Still hurt tension_arc (87→71), repetition_variation (93→84) |
| Don't change bass to euclidean_4_8 | Score 92.4→91.85 | +7 chord_vocabulary but -7 tension_arc | Net negative, same-magnitude tradeoff |
| Don't add inner_voice | L1 PASS dropped 22/50 → 2/50 | cv=96 but 45 voice_crossing violations | Requires per-beat melody floor tracking to fix — multi-hour work |
| Don't add drone | cadence_placement 100→40 | Drone sustains root → hides V-I bass motion | Destroys cadence detection |
| Don't use form(n_sections=3) | Score 92.4→91.4 | tension_arc +8, L1 PASS 23→32 | repetition_variation drops 93→70, phrase_boundaries 100→85 |
| Don't trust 94.0 baseline claim | Cannot reproduce on clean HEAD | Accept handover at face value | Best seed=47 gives 92.12; best overall is seed=43 at 92.42 |

## Known Issues

- **CLAUDE.md eval claim is wrong** — states 94.0/100 for seed=47, actual is 92.12. True best: 92.42 for seed=43. Needs correction.
- **transition_motivation ↔ tension_arc conflict** — These two metrics cannot both hit 100 with current architecture (density falloff at end is good for one, bad for the other).
- **Inner voice coordinator uses note ONSETS, not SUSTAINED pitches** — `_coordinate_with_melody` in builder.py:840 checks melody pitches in a ±2 beat window, but misses sustained melody notes that span multiple inner notes. This is the root cause of inner-voice voice_crossing violations.
- **Density tail-off (bars 40-48 empty)** — Root cause: `apply_developing_variation` in variation.py:240 replaces `out_durations[idx] = var_durations[j]` without preserving original phrase total duration. Variations are ~20% shorter than motif.
- **seed=43 vs seed=47 discrepancy** — handover says seed=47 gives 94.0; actual measurement gives seed=43→92.42, seed=47→92.12. Unclear cause.

## Next Steps (Priority Order)

1. **Fix CLAUDE.md eval claim** — Update to reflect measured 92.42/seed=43 OR investigate why 94.0 was claimed (try `git log --all` across branches, check for different music21/python versions). 5-minute task.
2. **Per-beat melody floor tracking for inner voice** — Multi-hour. Replace `_melody_beats: list[tuple[float, int]]` with a `dict[int, int]` mapping each beat position to the sounding melody pitch. Use it in `_coordinate_with_melody` and a post-processing global clamp. **This is the single biggest lever** — if inner voice L1 holds, chord_vocabulary jumps from 84→96.
3. **True ritardando tail** — Multi-hour. Design: in the final 20% of the piece, progressively lengthen note durations via a ramp (not the existing cosine bell). Would satisfy BOTH transition_motivation (smooth decline) and tension_arc (low energy at end).
4. **Bar-aligned phrase_length** — 1-hour. Change `_add_phrase_breaths` phrase_length from 12 to 16 (= 2 bars at 4/4 with 0.5-beat notes). Phrase breaths would land on bar lines, stabilizing density.
5. **Move from handover's list**: Make repo public + activate GitHub Pages, download Aegean Symphonic Orchestra SoundFont, Render.com deployment.

## Rollback Info

- Last known good state: `49a5dc9` (current HEAD on master) — all changes from this session were reverted
- No uncommitted changes exist (verified `git status` clean)
- No files modified in this session that persist
- If CLAUDE.md gets updated with corrected score, that's the only planned change

## Files Modified This Session

**None persisted.** All exploratory edits reverted via `git checkout --`.

Files temporarily modified during investigation (all reverted):
- `sacred_composer/variation.py` — tried scaling `var_durations` in `apply_developing_variation` to preserve phrase totals. Reverted.
- `sacred_composer/builder.py` — tried pre_cap headroom, `_final_cap()`, `_pad_to_target()`, tapering tail, global inner-voice ceiling, `_scale_step_down()`. All reverted.

## Key Numbers

- **Actual baseline eval**: 92.42/100 L1 PASS (Bb_minor seed=43 golden_spiral, 0 violations)
- **Previous handover claim**: 94.0/100 (Bb_minor seed=47) — UNREPRODUCIBLE
- **Current seed=47 actual**: 92.12
- **L1 PASS rate**: 23/50 Bb_minor seeds (vs handover's 22/50)
- **Tests**: 327 passed ✅
- **Weakest metrics** (seed=43): transition_motivation 71.4, interval_distribution 87.6, tension_arc 88.8, chord_vocabulary 84.6
- **Perfect metrics** (seed=43): entropy, cadence_placement, phrase_length, phrase_boundaries, thematic_development (all 100)

## Metric Conflict Map (for next session)

```
chord_vocabulary↑  →  needs denser bass OR inner voice
                  →  denser bass hurts tension_arc
                  →  inner voice breaks L1 (voice_crossing)

transition_motivation↑  →  needs flat density across all bars
                        →  filling the tail hurts tension_arc
                        →  variation phrase-shrinkage creates the tail

tension_arc↑  →  needs density/velocity FALL at end
              →  directly opposes transition_motivation
```

**To break the conflict**: implement a tail that has LOW density but HIGH consistency (e.g., one whole note per bar in bars 40-47). Both metrics could win simultaneously.
