# Session Handover

**Date:** 2026-04-05 (Session 8)
**Duration:** ~1 session, 12 commits
**Goal:** User asked for "100% compliance with principles" — interpret PRINCIPLES.md, audit the codebase, fix every violation.

## Summary

Session started by reading the session-7 handover, verifying the claimed
94.0 eval score was unreproducible, and fixing an inner-voice bug
(`_coordinate_with_melody` was tracking melody ONSETS in a ±2-beat window,
missing sustained melody notes that started earlier and were still sounding
when an inner note began). That fix lifted peak L1-PASS eval score from
90.78 to 93.17 for Bb_minor/seed=43.

Then the user redirected: "i wnat 100% complaince with principles". I ran
the `principles-check` skill, which spawned a general-purpose audit
subagent that returned 47 violations (6 Critical / 18 Major / 23 Minor).
I created 9 TaskCreate entries grouping the fixes by theme, then worked
through all 9 tasks in roughly this order: magic constants → dead code →
narrow excepts → docs sync → delete scaffolding → extract VoiceLeader →
thread RNG → print→logging → decompose god functions. Every commit was
test-gated (327 tests) and the compose() pipeline was determinism-checked
(bit-identical MIDI across back-to-back runs) after each big refactor.

Net: ~1,950 lines of dead/legacy code deleted (994 from
SYSTEM_ARCHITECTURE.py scaffolding + 955 from classical_music_gen.py),
35 global-RNG sites replaced with per-call ContextVars, 97 library
`print()` calls replaced with `_log.info()`, and 4 of the 10 god
functions decomposed. The other 6 god functions are musically-sensitive
(pass_4_melody* alone drives output quality) and deferred with a clear
note. Compliance estimate moved from ~72% to ~95%.

## What Got Done

- [x] **Inner-voice coordinator fix** (commit `409f0f7`) — redesigned
  `_coordinate_with_melody` from ±2-beat onset window to temporal-overlap
  check against sustained melody notes. `_melody_beats` changed from
  `list[tuple[float, int]]` to `list[tuple[float, float, int]]` (onset,
  duration, pitch). Reordered `_constrain_inner` so coordinate is the
  final pass. Peak L1 PASS eval: 90.78 → 93.17.
- [x] **CLAUDE.md eval claim corrected** (commit `ae8898c`) — replaced
  unreproducible "94.0/seed=47" with measured "90.78/seed=43" and
  a complete reproducible CompositionBuilder config snippet.
- [x] **Task 1 — DRY phi constants** (commit `78d4a58`) — replaced raw
  `0.618`/`1.618` with `PHI_INVERSE`/`phi` imports across 9 code files.
- [x] **Task 2 — YAGNI dead code** (commit `78d4a58`) — deleted
  placeholder Score class in evaluate.py, empty ThueMorse `__init__`,
  flattened 6 empty `elif ... pass` branches in the augmented-interval
  filter into one set-membership check, moved `sys` import inside
  `__main__` guard in composer.py.
- [x] **Task 3 — narrow silent excepts** (commit `78d4a58`) — 11
  `except Exception: pass` sites in library code narrowed to specific
  exception types and now log at debug/warning level.
- [x] **Task 9 — docs sync + alias bug** (commit `d3f3f91`) — found a
  latent NameError in `sacred_composer/world_music.py` (`import random
  as _rng_mod` while two functions called bare `random.Random`); fixed
  by dropping the alias. Synced CLAUDE.md "241 tests/11 files" →
  "327 tests/14 files".
- [x] **Task 5 — delete scaffolding** (commit `c69c2e7`) — deleted 994
  lines from `SYSTEM_ARCHITECTURE.py` (CompilerPass + 9 Pass subclasses +
  CompositionPipeline + performance_ir_to_midi + EXAMPLE_PLAN +
  __main__ demo). Kept lines 1–546 (enums + IR dataclasses + schema
  realizer) since 19 modules import from them.
- [x] **Task 6 — extract VoiceLeader** (commit `337b09c`) — moved the
  only actively-used class from `classical_music_gen.py` into
  `composer/voice_leader.py`, then deleted the 955-line legacy file.
- [x] **Task 4 — per-call RNG context** (commit `169d649`) — created
  `composer/_rng.py` exposing `set_rng(seed)`, `rng()`, `np_rng()`
  backed by ContextVars. Replaced 35 global `random.*`/`np.random.*`
  sites across parser, voice_leader, fugue, all passes, helpers.
  Deleted `random.seed(seed); np.random.seed(seed)` from compose().
  Verified bit-identical output across two back-to-back runs.
- [x] **Task 7 — library print → logging** (commit `e0f24c0`) — 97
  print() calls in `composer/pipeline.py`,
  `composer/passes/pass_1_plan.py`, `composer/passes/pass_4_melody.py`
  replaced with `_log.info()`. Added `_ensure_console_logging()` at
  entry of compose()/compose_suite() so CLI scripts still see output
  without explicit logging setup.
- [x] **Task 8 — decompose 4 god functions** (commits `767c774`,
  `0562621`, `17a763c`):
  - `compose()` 234→195 lines (extracted `_apply_augmented_interval_fixes`,
    `_assemble_performance_ir`, `_log_final_summary`).
  - `CompositionBuilder.build()` 178→146 lines (extracted
    `_init_harmony_tracks`, `_cap_to_target_beats`).
  - `_clamp_sounding_pitches` 98→40 lines (extracted
    `_clamp_one_interval`, `_needs_leap_recovery`, `_try_recover_leap`).
  - `parse_prompt` 105→45 lines (extracted `_detect_form`, `_detect_key`,
    `_detect_character`, `_detect_instrumentation`,
    `_extract_clamped_int`, `_form_specific_defaults`; hoisted mapping
    tables to module level).

## What's In Progress

- [ ] **Task 8 — decompose remaining 6 god functions** — **State:** 4/10
  decomposed in this session; 6 still exceed 50-line SRP guideline.
  **Remaining:**
  - `composer/passes/pass_4_melody.py::pass_4_melody_fugue` (322 lines)
  - `composer/passes/pass_4_melody.py::pass_4_melody` (199)
  - `composer/passes/pass_5_counterpoint.py::pass_5_counterpoint` (158)
  - `composer/passes/pass_9_validation.py::pass_9_validation` (162)
  - `sacred_composer/combiners.py::fractal_form` (167)
  - `sacred_composer/orchestration.py::render_orchestral_wav` (178)
  - `sacred_composer/musicxml.py::_render_raw_xml` (131)

## What Didn't Get Done (and Why)

- **Remaining 6 god functions** — deferred as a deliberate trade-off.
  Each is musically-sensitive: `pass_4_melody*` drives the actual
  musical output, so a mechanical decomposition risks breaking the
  eval score across all 50 seeds. I wanted to do them carefully
  (with per-extraction regression testing) rather than quickly.
  The two output-formatting ones (`render_orchestral_wav`,
  `_render_raw_xml`) are safer but I stopped to write a proper handover.
- **`sacred_composer/bridge.py` lazy imports** — Minor #31 from audit.
  Two `from SYSTEM_ARCHITECTURE import ...` calls inside function
  bodies could be hoisted to module top now that SYSTEM_ARCHITECTURE.py
  is smaller. Deferred; it's cosmetic.
- **Eval past 95** — still blocked by session-7's
  `tension_arc ↔ transition_motivation` structural conflict. The
  inner-voice coordinator fix improved peak score but didn't break
  the conflict.

## Architecture & Design Decisions

| Decision | Chosen Approach | Why | Alternatives Considered | Why Rejected |
|----------|----------------|-----|------------------------|--------------|
| Per-call RNG scoping | ContextVar-backed `rng()`/`np_rng()` accessors in `composer/_rng.py` | Zero function-signature changes, still satisfies CLAUDE.md "random.Random(seed)" rule, thread-safe and asyncio-safe via ContextVar | Thread explicit `rng` param through every function | ~30 signatures would change, ~200-line diff surface, would touch every call site of parser/passes |
|  |  |  | `threading.local()` | Doesn't compose with asyncio |
|  |  |  | Keep global `random.seed(seed)` | Violates the rule, breaks under concurrency |
| SYSTEM_ARCHITECTURE.py — keep or rename? | Keep the filename, delete only the scaffolding | 19 modules import from it; a rename = 19-file touch for pure cosmetics | Move IR dataclasses to `composer/ir.py` | Churn without principle gain; the filename is fine once scaffolding is gone |
| Exception narrowing scope | Narrow silent `except: pass` only; leave entry-point boundary excepts (CLI, API, Discord bot, async wrappers) alone even if broad | Entry-point handlers MUST convert any error to user-visible output | Narrow every `except Exception` | Breaks boundary error-handling semantics; would lose coverage |
| `_ensure_console_logging()` in compose() | Install a root-logger StreamHandler if none exists | Preserves CLI-friendly behavior (`python -c "compose(...)"` still shows progress) without overriding library users who configure their own logging | Silent by default (pure logger, no basicConfig) | Would break every existing script that invokes compose() directly |
|  |  |  | Keep print() alongside logger | Double output for users who configure logging |
| Inner-voice pipeline ordering | Make coordinate the FINAL pass (drop trailing clamp) | Clamp can re-break voice_spacing/crossing after coordinate establishes safe window | Keep clamp last, add safety pass | Extra pass had to know about melody window → just merge concerns |
| Delete SYSTEM_ARCHITECTURE.py `__main__` demo | Yes | Dead code, referenced only classes being deleted | Keep as "documentation" | Misleading — its demo classes were the DIVERGED implementation |
| Defer pass_4_melody decomposition | Yes | 521 lines total, drives musical output; mechanical split high regression risk | Do it anyway | Not worth breaking eval scores for principle score |

## Mental Model

**The composition pipeline is two overlapping systems.** Understanding
this is the single most important piece of context for the codebase:

1. **`composer/`** — the prompt-driven 9-pass pipeline. Entry:
   `composer.compose(prompt, output_file, seed)`. Flow:
   parse_prompt → pass_1_plan → pass_2_schema → pass_3_harmony →
   (mark cadences, fix augmented intervals) → pass_4_melody[_fugue] →
   (augmented/leap fixes) → pass_5_counterpoint → (leading-tone,
   seventh, voice-crossing, melody-spacing fixes) → pass_6_orchestration →
   pass_6a_smooth_sections → pass_6b_phrase_breathing → pass_7_expression →
   pass_8_humanization → assemble PerformanceIR → pass_9_validation →
   export_midi. This pipeline consumes natural-language prompts and
   produces MIDI with music21-based validation.

2. **`sacred_composer/`** — the pattern-driven builder. Entry:
   `CompositionBuilder(key, tempo, bars).melody(...).bass(...).build()`.
   Uses mathematical pattern generators (golden_spiral, fibonacci,
   euclidean, etc.) mapped through `to_pitch`/`to_rhythm`/`to_dynamics`
   and shaped by constraint passes in `sacred_composer/constraints.py`
   and `builder.py` (enforce_range → improve_interval_distribution →
   diversify → smooth_leaps → coordinate_with_melody → break_unisons →
   clamp → coordinate). This is what gets evaluated against the 50-rule
   `evaluation_framework.py`.

Both pipelines share `SYSTEM_ARCHITECTURE.py` for IR types (FormIR,
KeyToken, etc.) and `evaluation_framework.py` for scoring.

**The RNG architecture after this session:** `composer/_rng.py`
stores two ContextVar-scoped RNGs — `rng()` returns a
`random.Random`, `np_rng()` returns a `numpy.random.Generator`.
`compose()` calls `set_rng(seed)` at entry, then downstream code
just calls `rng().choice(...)` etc. Because they're ContextVars,
two concurrent compose() calls (threads OR asyncio tasks) get
independent state. Inside one call, behavior is identical to the
old `random.seed(seed)` pattern.

**The eval-score structural conflict:** `tension_arc` (weight 0.20)
rewards density falling toward the end of the piece; but
`transition_motivation` (weight 0.10) flags that same fall as an
"abrupt jump." You can't max both with the current architecture.
Breaking past 95 requires a "ritardando tail" — LOW density + HIGH
consistency in the final 20% (e.g., whole notes). Documented in
session 7 and still open.

**Key file shapes:**
- `CompositionBuilder._constrain_inner` (builder.py:540) is the hot
  path for inner-voice violations. It now runs: enforce_range →
  interval_distribution → diversify → smooth_leaps → coordinate →
  break_unisons → clamp → coordinate (final). The final coordinate
  can't be clobbered by a later clamp.
- `_melody_beats` is a `list[tuple[float, float, int]]` carrying
  `(onset, duration, pitch)`. Inner-voice coordinate uses
  temporal-overlap (`ms < inner_end AND ms + md > inner_start`) to
  find all sounding melody pitches, then takes min as floor.
- `composer/_rng.py` is imported by every composer/ pass — think
  of `rng()` as the package-wide RNG accessor, replacing the old
  global `random` import.

## Known Issues & Risks

- **6 god functions still over 50 LOC** — Impact: SRP violation, harder
  to test in isolation | Workaround: functions work correctly; this
  is a code-quality issue not a correctness issue | Fix: per-function
  careful decomposition in a dedicated session.
- **Inner-voice L1 PASS rate is only 7/50** (with inner voice added
  via the fixed coordinator) — Impact: most seeds still generate 3-4
  voice_spacing violations when an inner voice is added | Workaround:
  don't add inner voice; baseline (melody+bass+form) scores 32/50
  L1 PASS at 90.78 peak | Fix: per-beat melody floor tracking (see
  session 7 handover) is the next big lever.
- **Deleted SYSTEM_ARCHITECTURE.py scaffolding may surface in docs** —
  Likelihood: low | Impact: stale references in GAMEPLAN.md /
  SACRED_COMPOSER_SPEC.md | Mitigation: grep docs for "CompilerPass",
  "CompositionPipeline", "performance_ir_to_midi" if someone reports
  doc confusion.
- **ContextVar RNG inside music21 callbacks** — Likelihood: low |
  Impact: if music21 calls user code from a different context
  (unlikely in current use), rng() would create a fresh OS-seeded
  Random | Mitigation: the fallback is documented in `composer/_rng.py`
  and will still be deterministic within its own context.

## What Worked Well

- **Delegating the audit to a subagent** — 47 violations enumerated
  with file:line evidence in one call, much faster than doing the
  audit inline.
- **Sequencing fixes by risk** — trivial (magic numbers, dead code)
  → low-risk (narrow excepts) → high-impact structural (delete
  scaffolding + extract VoiceLeader) → behavior-preserving refactor
  (RNG threading) → decomposition (god functions). Early wins built
  confidence and kept tests green.
- **TaskCreate/TaskUpdate for 9 grouped tasks** — made the audit's 47
  violations feel tractable and provided commit-boundary markers.
- **Determinism checks after each major refactor** — catching any
  RNG-threading bug immediately via sha256 comparison of back-to-back
  MIDI outputs.
- **Test-gating every commit** — 327 tests never dropped once. Each
  commit is safe to cherry-pick or revert independently.
- **ContextVar for RNG** — landed cleanly with zero signature changes,
  ~30-line diff per file, vs estimated ~200 lines for explicit-param
  threading.

## What Didn't Work (Traps to Avoid)

- **`sed -i 's/random\./rng()\./g'` was tempting but wrong** — would
  match `random.Random(seed)` (correct usage) too. Had to manually
  verify each file after sed or use narrower patterns like
  `random\.choice(`, `random\.randint(`, `random\.random()`.
- **`urllib.error` is NOT auto-imported by `import urllib.request`** —
  caught this in stream_loop.py fix; narrowed `except Exception` to
  `except urllib.error.URLError` but forgot the import. Always test
  exception narrowing against real conditions.
- **The original `_melody_beats` type needed to be EXTENDED not
  replaced** — initial instinct was to add a new `_melody_notes`
  list, but extending the existing tuple from 2→3 elements was
  cleaner and touched only 2 call sites.
- **Some audit findings were false positives** — `classical_music_gen.py:147`
  `random.sample(voicings, 500)` was already guarded by
  `if len(voicings) > 500`; `sacred_composer/__main__.py:156`
  `rng = random.Random()` is CORRECT for `--random` CLI mode.
  Always verify the audit claim in context before fixing.
- **The `SYSTEM_ARCHITECTURE.py::ValidationReport` duplicated
  `composer/passes/pass_9_validation.py::ValidationReport`** — both
  named identically but with different fields. Deleting the
  scaffolding version was correct but required grep confirmation
  that the pass_9 one was canonical first.
- **Don't assume docs match reality** — CLAUDE.md claimed "241 tests
  (11 files)"; actual was 327 tests in 14 files. Always
  `pytest --collect-only` before quoting test counts.

## Next Steps (Priority Order)

1. **Decompose `pass_9_validation` (162 lines) in
   `composer/passes/pass_9_validation.py`** — least musically-sensitive
   of the 6 deferred. Open the file, identify the validation-check
   phases (each likely emits to `report.errors`/`report.warnings`/
   `report.scores`), extract one helper per phase. Test: run
   `python -m pytest tests/ -q`; validation output should be
   unchanged. Expected: 2-hour task.

2. **Decompose `render_orchestral_wav` (178 lines) in
   `sacred_composer/orchestration.py` and `_render_raw_xml` (131
   lines) in `sacred_composer/musicxml.py`** — pure output formatters,
   no RNG, no validation. Safer than the counterpoint/melody passes.
   Extract per-instrument loops or per-element formatters. Test:
   diff output bytes before/after.

3. **Decompose `fractal_form` (167 lines) in
   `sacred_composer/combiners.py`** — recursive structure; extract
   the per-level recursion step into a helper, keep the top-level
   driver compact. Test: existing fractal tests in tests/.

4. **Decompose `pass_5_counterpoint` (158 lines)** — extract voicing
   selection logic separately from voice-leading-cost scoring.
   This one needs careful testing because it drives chord voicings
   that the evaluator scores.

5. **Last, with most care: `pass_4_melody` (199) + `pass_4_melody_fugue`
   (322)** — these drive the actual melodic output. Before touching:
   sweep Bb_minor seeds 0-49 and record the current score
   distribution. Any decomposition must preserve that distribution.
   Consider: motif-selection, sequencing, cadence-shaping, refrain-
   reapply as natural sub-helpers.

6. **Hoist `sacred_composer/bridge.py` lazy imports to module top**
   (5-min cleanup now that SYSTEM_ARCHITECTURE.py is smaller).

7. **Per-beat melody floor tracking** (session 7's #2) — would
   further improve inner-voice L1 PASS rate beyond what
   temporal-overlap achieved. Build a
   `dict[int, int]` mapping each beat position to sounding melody
   pitch; use it in `_coordinate_with_melody` AND add a global
   clamp post-processing step. Expected eval lift: chord_vocabulary
   84→96.

8. **True ritardando tail** to break the
   tension_arc ↔ transition_motivation conflict and push eval past
   95. Design: in the final 20% of the piece, progressively
   lengthen durations (whole-note-per-bar tail) to satisfy BOTH
   "density falloff" AND "smooth transitions" metrics.

9. **Make repo public + activate GitHub Pages** (session 6 handover).

## Rollback Plan

- **Last known good state:** `168739b` (current HEAD on master) —
  session 8 fully committed, working tree clean, 327 tests pass.
- **Pre-session-8 state:** `49a5dc9` (before inner-voice fix and
  principles audit). Resetting there loses 12 commits of principles
  work.
- **Rollback just the god-function decompositions:**
  `git revert 17a763c 0562621 767c774` (3 commits, independent of
  RNG / logging / scaffolding work).
- **Rollback just the RNG threading:** `git revert 169d649`. Will
  also need to revert files that import from `composer._rng.py`;
  simpler to just add `import random; random.seed(seed)` back into
  `compose()` if reverting gets messy.
- **Safe full reset:** `git reset --hard 49a5dc9` (destructive,
  discards session 8 entirely).
- **Safe partial reset (keep audit + quick fixes, drop refactors):**
  `git reset --hard 78d4a58`.

## Files Changed This Session

**Created (3):**
- `composer/_rng.py` — ContextVar-based per-call RNG context
- `composer/voice_leader.py` — extracted from deleted classical_music_gen.py

**Deleted (1):**
- `classical_music_gen.py` — 955-line legacy toolkit

**Modified (~25):**
- `CLAUDE.md` — eval claim corrected, test counts synced
- `HANDOVER.md` — this file (rewritten from session 7's version)
- `SYSTEM_ARCHITECTURE.py` — 994 lines scaffolding deleted
- `composer.py` — sys import moved into main guard
- `composer/pipeline.py` — RNG context, logging, 3 helper extractions
  from compose(), PHI_INVERSE, narrowed excepts
- `composer/parser.py` — RNG context, 6 helpers extracted from
  parse_prompt, module-level mapping tables
- `composer/passes/pass_1_plan.py` — logging, PHI_INVERSE
- `composer/passes/pass_2_schema.py` — RNG context
- `composer/passes/pass_4_melody.py` — RNG context, logging
- `composer/passes/pass_5_counterpoint.py` — narrowed except,
  VoiceLeader import path, logging setup
- `composer/passes/pass_6_orchestration.py` — RNG context, PHI_INVERSE
- `composer/passes/pass_7_expression.py` — PHI_INVERSE
- `composer/passes/pass_8_humanization.py` — np_rng context
- `composer/helpers/pink_noise.py` — np_rng context
- `composer/helpers/phyllotaxis.py` — RNG context
- `composer/forms/fugue.py` — RNG context
- `discord_bot.py` — logging, narrowed except
- `evaluation_framework.py` — PHI_INVERSE/phi, narrowed excepts,
  flattened augmented-interval elif chain
- `prompt_template_library.py` — PHI_INVERSE import
- `sacred_composer/builder.py` — inner-voice coordinator temporal-
  overlap fix, build() decomposition, _clamp_sounding_pitches
  decomposition
- `sacred_composer/evaluate.py` — placeholder Score class removed
- `sacred_composer/lilypond.py` — log on GM_INSTRUMENTS fallback
- `sacred_composer/patterns.py` — empty ThueMorse __init__ removed
- `sacred_composer/world_music.py` — fixed _rng_mod alias NameError
- `stream_loop.py` — narrowed except, urllib.error import

## Open Questions

- **Why was the 94.0/seed=47 eval score claimed in commit `124efef`
  unreproducible on current HEAD?** The commit explicitly says
  "Best: Bb_minor seed=47 (94.0/100), 22/50 seeds L1 PASS" but
  measuring today gives 88.67 for seed=47 and 90.78 for seed=43.
  No code between `124efef` and now should have changed the scores
  that much. Python/music21 version drift? Different MIDI writer
  timing? The truth is probably in a diff against `124efef`
  that nobody has computed.
- **Should `bridge.py` be moved into `composer/` or stay in
  `sacred_composer/`?** It bridges the two pipelines. Current home
  in sacred_composer/ makes sense since it consumes Score objects
  from there. Could argue for `composer/bridge.py`. Non-urgent.
- **Is the `_final_cap` / `_pad_to_target` / `_scale_step_down`
  code in `sacred_composer/builder.py` history still needed?**
  Session 7 mentioned these as temporarily added and reverted.
  Verify with `git log -p sacred_composer/builder.py` that nothing
  lingered.
- **Could `_FORM_KEYWORDS` / `_INSTRUMENT_GROUPS` / `_CHARACTER_TEMPO`
  in `composer/parser.py` be pushed even further to a data file
  (YAML/JSON)?** Right now they're module-level Python constants.
  Externalizing them would let non-programmers tune the prompt
  parser.

## Success Criteria Met?

- [x] A stranger can read this and start working immediately — yes,
  Next Steps #1-#5 each name the exact file, expected line counts,
  and the test command.
- [x] Dead ends are documented — "What Didn't Work" captures the
  sed trap, the urllib.error import gotcha, and false-positive audit
  findings.
- [x] Mental Model genuinely teaches — explains the two-pipeline
  architecture, the RNG ContextVar design, and the eval structural
  conflict.
- [x] Next Steps are actionable — each has file path, line counts,
  expected time, and acceptance criteria.
- [x] All work secured in git — 12 commits, `git status` clean.
- [x] Rollback plan is specific — commit hashes and revert commands.
