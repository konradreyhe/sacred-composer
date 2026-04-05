# Session Handover

**Date:** 2026-04-05 (Session 10)
**Duration:** 1 session, 1 commit + 1 reverted experiment
**Goal:** Tackle next-step cleanups from session 9 (bridge.py hoist, ritardando tail).

## Summary

Quick session. Landed one cleanup commit (bridge.py lazy-import hoist,
session 9 Next Step #1). Attempted the ritardando-tail experiment
(session 9 Next Step #3) to break the `tension_arc ↔ transition_motivation`
conflict — it didn't work, reverted cleanly. Documented why below so the
next session doesn't retry the same approach. Baseline eval holds at
**90.78** (Bb_minor seed=43), 327 tests green, working tree clean.

## What Got Done This Session

1. **`bridge.py` lazy-import hoist** — commit `be80563`. The two
   `from SYSTEM_ARCHITECTURE import ...` calls inside
   `score_to_performance_ir` and `voice_to_performance_notes` now live at
   module top. sys.path manipulation runs once at import instead of per
   call. Tests still pass. Closes session-9 Next Step #1 (and the
   long-dangling session-8 Next Step #6).

## Experiment That Didn't Work: Ritardando Tail

Tried session 9's Next Step #3: added `_apply_ritardando_tail()` that
merges consecutive sounding notes in the final 20% of each voice, with
group size growing from 1 → 4 over the tail. Rests preserved, total
duration exactly preserved (sum of absorbed notes).

**Result on Bb_minor seed=43:** 90.78 → **89.53** (worse). Introduced
1 L1 leap_recovery violation. Breakdown:
- `tension_arc`: 79.02 → 75.89 (**worse**)
- `chord_vocabulary`: 88.19 → 89.36 (slight improvement)
- `interval_distribution`: 86.43 → 85.76 (worse)
- `repetition_variation`: 89.33 → 86.19 (worse)
- `transition_motivation`: 71.43 → 71.43 (unchanged)

**Why it didn't work** (this is the key finding for future sessions):

The piece's density curve is *already* a **flat plateau + cliff**, not
an arch. The melody voice has total=159.5 beats in a 192-beat score, so
bars 41-48 ALREADY have near-zero melody density (only bass notes).
The current density per bar (averaged across voices) is roughly flat
0.5-1.0 through bar 40, then cliff-drops. That's why
`tension_arc = 0.726` correlation — arch target wants smooth rise + fall,
piece gives plateau + cliff.

The ritardando tail made the cliff WORSE by emptying out bars 35-40 too.
It also destroyed voice leading (merging 4 notes into 1 keeps only the
first pitch, so leap-recovery notes got absorbed → L1 violation).

**The real lever for `tension_arc`:** reduce density/velocity in
bars 1-15 (create a gentle entry), NOT reshape the tail. The arch
target at t=0 is 0.0 — it wants near-silence at bar 1 growing to peak
at bar 30. Current piece starts at "mid" density/velocity. To push
`tension_arc` past 85, shape the FIRST 30% of the piece, not the last 20%.

Reverted cleanly (file restored to pre-experiment state) — no commit.

## Current Eval Baseline

**Bb_minor seed=43, 48 bars, 72 BPM, fibonacci form:** **90.78/100 L1 PASS**.

| Metric | Score | Weight |
|---|---|---|
| L2.interval_distribution | 86.43 | 0.20 |
| L2.entropy | 100.00 | 0.10 |
| L2.harmonic_rhythm | 95.16 | 0.10 |
| L2.chord_vocabulary | 88.19 | 0.10 |
| L2.cadence_placement | 100.00 | 0.10 |
| L2.repetition_variation | 89.33 | 0.15 |
| L2.phrase_length | 100.00 | 0.10 |
| L3.phrase_boundaries | 100.00 | 0.15 |
| L3.thematic_development | 100.00 | 0.20 |
| **L3.tension_arc** | **79.02** | **0.20** |
| L3.form_proportions | 91.39 | 0.10 |
| L4.intentionality | 91.71 | 0.15 |
| **L4.transition_motivation** | **71.43** | **0.10** |
| L4.directional_momentum | 89.89 | 0.10 |

Weakest metrics (highest leverage to improve): `tension_arc` (79.02),
`transition_motivation` (71.43). These are the structural-conflict pair
from sessions 7-9.

## Updated Next Steps (Priority Order)

1. **Shape the piece's entry, not its tail** — experiment with
   progressively RAMPING UP velocity and density over bars 1-15 so
   the piece starts quiet and sparse, then builds to climax near bar 30.
   Concretely: add a `_apply_crescendo_entry(pitches, durations, dynamics,
   entry_fraction=0.3)` that scales velocities by a sin-ramp 0→1 over
   the opening, and optionally thins note density by replacing some
   notes with rests in bars 1-5. Expected lift: `tension_arc` 79→90+.
   This directly targets the arch target's rising phase.

2. **Per-beat melody floor tracking** (session 9 #2, carried over) —
   substantive. Build `dict[int, int]` mapping beat position → sounding
   melody pitch; use it in `_coordinate_with_melody` AND add a global
   clamp post-processing step. Targets inner-voice L1 PASS rate in
   3-voice configs (not the current 2-voice peak config).

3. **Investigate unreproducible 94.0/seed=47 eval claim** (session 9 #4) —
   commit `124efef` claimed 94.0 for Bb_minor seed=47; current HEAD
   gives 88.67. A diff against `124efef` might reveal which change
   regressed that seed.

4. **Make repo public + activate GitHub Pages** (session 6).

5. **Push 22 commits to origin** — master is 22 commits ahead.
   User hasn't asked.

## Files Changed This Session

**Modified (2):**
- `sacred_composer/bridge.py` — hoisted `from SYSTEM_ARCHITECTURE import`
  to module top (2 in-function imports removed).
- `HANDOVER.md` — this file (rewritten for session 10).

**Created:** none. **Deleted:** none.

## Rollback Plan

- **Last known good state:** `be80563` (current HEAD) — bridge.py cleanup,
  327 tests, 90.78 eval.
- **Pre-session-10 state:** `be35703` (session 9 handover).
- **Rollback bridge.py change only:** `git revert be80563`.

## Traps to Avoid

- **Don't retry the ritardando-tail approach** — the piece's density
  shape is plateau+cliff, not plateau+arch. Tail work can't fix it.
  Entry work (crescendo_entry) is the right lever. See "Experiment
  That Didn't Work" section above.
- **Voice-level merging breaks voice leading** — if you absorb note
  N+1 into N, you lose N+1's pitch. That breaks leap recovery, phrase
  endings, and anything else that depends on adjacent pitches. If you
  must compress notes, use decrescendo on velocities instead.
- **Melody voice is only ~159 beats in a 192-beat piece** — the
  `_cap_to_target_beats` + phrase breaths + section rhythm variation
  chain doesn't perfectly preserve total length. Don't assume all voices
  span the full piece when computing bar-indexed proxies.

---

## Prior Sessions (Summary)

### Session 9 — 2026-04-05

**Goal:** Decompose 6 god functions deferred by session 8.

**Result:** 7 commits, all byte-verified via SHA256 of MIDI/WAV/XML output.
327 tests pass. All session-8 Next Steps #1-#5 closed.


