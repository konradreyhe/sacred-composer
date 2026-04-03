"""Parameter optimization for Sacred Composer.

Uses the evaluation framework as a fitness function to find the best
CompositionBuilder parameters automatically, targeting 95+ scores.

Optuna (TPE sampler) is used when available; falls back to random search.
"""

from __future__ import annotations

import math
import random
import time
from collections import Counter
from typing import Any

from sacred_composer.core import Composition
from sacred_composer.builder import CompositionBuilder
from sacred_composer.evaluate import evaluate_composition


# ---------------------------------------------------------------------------
# 1. Search space definition
# ---------------------------------------------------------------------------

SEARCH_SPACE: dict[str, Any] = {
    "key": [
        "C_minor", "D_minor", "E_minor", "G_minor", "A_minor",
        "C_major", "F_major", "G_major", "Bb_major", "D_major",
    ],
    "tempo": (52, 132),           # int range
    "bars": (24, 64),             # int range, step 8
    "melody_pattern": [
        "infinity_series", "fibonacci", "golden_spiral",
        "logistic", "mandelbrot", "rossler",
    ],
    "melody_rhythm": ["euclidean_5_8", "euclidean_3_8", "euclidean_7_12"],
    "melody_base_dur": [0.25, 0.5, 0.75, 1.0],
    "melody_seed": (0, 50),       # int range
    "bass_pattern": ["harmonic_series", "fibonacci", "golden_spiral"],
    "bass_base_dur": [1.0, 2.0, 4.0],
    "n_sections": (3, 7),         # int range
    "use_harmony": [True, False],
}


# ---------------------------------------------------------------------------
# 2. Build a Composition from a flat parameter dict
# ---------------------------------------------------------------------------

def build_from_params(params: dict) -> Composition:
    """Construct a Composition from an optimizer parameter dict."""
    builder = CompositionBuilder(
        key=params["key"],
        tempo=params["tempo"],
        bars=params["bars"],
        title="Optimized Composition",
    )
    builder.form(pattern="fibonacci", n_sections=params["n_sections"])

    if params.get("use_harmony"):
        builder.harmony()

    builder.melody(
        pattern=params["melody_pattern"],
        rhythm_pattern=params["melody_rhythm"],
        base_duration=params["melody_base_dur"],
        seed=params["melody_seed"],
    )
    builder.bass(
        pattern=params["bass_pattern"],
        base_duration=params["bass_base_dur"],
    )
    return builder.build()


# ---------------------------------------------------------------------------
# 3. Fast heuristic evaluation (~<10 ms, no music21)
# ---------------------------------------------------------------------------

def evaluate_fast(composition: Composition) -> float:
    """Estimate a composition score 0-100 using cheap heuristics.

    Analyses the Composition's in-memory note data directly:
      - step_ratio   : fraction of melodic intervals <= 2 semitones
      - rest_ratio   : fraction of notes that are rests (phrase boundaries)
      - harm_rhythm  : how often the bass pitch changes (harmonic rhythm)
      - entropy      : Shannon entropy of pitch-class distribution
    """
    voices = composition.score.voices
    if not voices:
        return 0.0

    # --- Gather all notes from the first (melody) voice ---
    melody_notes = [n for n in voices[0].notes if not n.is_rest]
    all_notes = []
    for v in voices:
        all_notes.extend(v.notes)

    total = len(all_notes)
    if total == 0:
        return 0.0

    # 1) Step ratio (target ~0.65-0.80)
    pitches = [n.pitch for n in melody_notes]
    intervals = [abs(pitches[i] - pitches[i - 1]) for i in range(1, len(pitches))]
    step_count = sum(1 for iv in intervals if iv <= 2)
    step_ratio = step_count / max(len(intervals), 1)
    # Score peaks at 0.70, falls off on both sides
    step_score = max(0.0, 1.0 - abs(step_ratio - 0.70) / 0.30) * 25

    # 2) Rest / phrase boundary ratio (target ~0.05-0.15)
    rest_count = sum(1 for n in all_notes if n.is_rest)
    rest_ratio = rest_count / total
    rest_score = max(0.0, 1.0 - abs(rest_ratio - 0.10) / 0.10) * 25

    # 3) Harmonic rhythm — bass pitch change frequency (target ~0.30-0.60)
    if len(voices) >= 2:
        bass_notes = [n for n in voices[1].notes if not n.is_rest]
        bass_pitches = [n.pitch for n in bass_notes]
        bass_changes = sum(
            1 for i in range(1, len(bass_pitches)) if bass_pitches[i] != bass_pitches[i - 1]
        )
        harm_ratio = bass_changes / max(len(bass_pitches) - 1, 1)
    else:
        harm_ratio = 0.5  # neutral if no bass voice
    harm_score = max(0.0, 1.0 - abs(harm_ratio - 0.45) / 0.35) * 25

    # 4) Pitch-class entropy (target ~2.5-3.2 bits for 7-note scale usage)
    pc_counts = Counter(p % 12 for p in pitches)
    total_pc = sum(pc_counts.values())
    entropy = 0.0
    if total_pc > 0:
        for count in pc_counts.values():
            prob = count / total_pc
            if prob > 0:
                entropy -= prob * math.log2(prob)
    # Max entropy for 12 pitch classes is ~3.58; target ~2.8
    entropy_score = max(0.0, 1.0 - abs(entropy - 2.8) / 1.5) * 25

    return step_score + rest_score + harm_score + entropy_score


# ---------------------------------------------------------------------------
# 4. Main optimization loop
# ---------------------------------------------------------------------------

def _sample_random(rng: random.Random) -> dict:
    """Draw one random parameter set from SEARCH_SPACE."""
    params: dict[str, Any] = {}
    for key, spec in SEARCH_SPACE.items():
        if isinstance(spec, list):
            params[key] = rng.choice(spec)
        elif isinstance(spec, tuple) and len(spec) == 2:
            lo, hi = spec
            if key == "bars":
                params[key] = rng.choice(range(lo, hi + 1, 8))
            else:
                params[key] = rng.randint(lo, hi)
        else:
            params[key] = spec
    return params


def optimize(
    n_trials: int = 100,
    timeout: int = 600,
    use_full_eval: bool = False,
    seed: int = 42,
) -> dict:
    """Find optimal CompositionBuilder parameters.

    Parameters
    ----------
    n_trials : Number of parameter combinations to try.
    timeout : Maximum wall-clock seconds.
    use_full_eval : If True, use evaluate_composition (slow, needs music21).
                    If False (default), use evaluate_fast (~<10 ms).
    seed : Random seed for reproducibility.

    Returns
    -------
    dict with keys ``params`` (best parameter dict) and ``score`` (float).
    """

    def _objective_fn(params: dict) -> float:
        comp = build_from_params(params)
        if use_full_eval:
            report = evaluate_composition(comp, verbose=False)
            return report["final_score"]
        return evaluate_fast(comp)

    # --- Try optuna first ---------------------------------------------------
    try:
        import optuna  # type: ignore[import-untyped]

        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial: optuna.Trial) -> float:
            params = {
                "key": trial.suggest_categorical("key", SEARCH_SPACE["key"]),
                "tempo": trial.suggest_int("tempo", *SEARCH_SPACE["tempo"]),
                "bars": trial.suggest_int("bars", *SEARCH_SPACE["bars"], step=8),
                "melody_pattern": trial.suggest_categorical(
                    "melody_pattern", SEARCH_SPACE["melody_pattern"],
                ),
                "melody_rhythm": trial.suggest_categorical(
                    "melody_rhythm", SEARCH_SPACE["melody_rhythm"],
                ),
                "melody_base_dur": trial.suggest_categorical(
                    "melody_base_dur", SEARCH_SPACE["melody_base_dur"],
                ),
                "melody_seed": trial.suggest_int(
                    "melody_seed", *SEARCH_SPACE["melody_seed"],
                ),
                "bass_pattern": trial.suggest_categorical(
                    "bass_pattern", SEARCH_SPACE["bass_pattern"],
                ),
                "bass_base_dur": trial.suggest_categorical(
                    "bass_base_dur", SEARCH_SPACE["bass_base_dur"],
                ),
                "n_sections": trial.suggest_int(
                    "n_sections", *SEARCH_SPACE["n_sections"],
                ),
                "use_harmony": trial.suggest_categorical(
                    "use_harmony", SEARCH_SPACE["use_harmony"],
                ),
            }
            return _objective_fn(params)

        sampler = optuna.samplers.TPESampler(seed=seed)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        study.optimize(objective, n_trials=n_trials, timeout=timeout)

        return {"params": study.best_params, "score": study.best_value}

    except ImportError:
        pass

    # --- Fallback: random search --------------------------------------------
    rng = random.Random(seed)
    best_params: dict = {}
    best_score = -1.0
    start = time.monotonic()

    for _ in range(n_trials):
        if time.monotonic() - start > timeout:
            break
        params = _sample_random(rng)
        score = _objective_fn(params)
        if score > best_score:
            best_score = score
            best_params = params

    return {"params": best_params, "score": best_score}


# ---------------------------------------------------------------------------
# 5. Convenience: optimize then build
# ---------------------------------------------------------------------------

def optimize_and_build(n_trials: int = 100, **kwargs: Any) -> Composition:
    """Run optimization, then build the best composition.

    All extra keyword arguments are forwarded to :func:`optimize`.
    """
    result = optimize(n_trials=n_trials, **kwargs)
    print(f"Best score: {result['score']:.1f}  params: {result['params']}")
    return build_from_params(result["params"])
