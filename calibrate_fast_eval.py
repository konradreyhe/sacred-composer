"""Calibrate evaluate_fast() against the full evaluation framework.

Generates diverse compositions, evaluates with both fast and full evaluators,
analyzes the correlation, and prints a calibration report.
"""

import sys
import os
import time
import math
import json
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sacred_composer.builder import CompositionBuilder
from sacred_composer.optimizer import evaluate_fast, build_from_params
from sacred_composer.evaluate import evaluate_composition

# 20 diverse configurations spanning the search space
CONFIGS = [
    {"key": "D_minor", "tempo": 72, "bars": 32, "melody_pattern": "infinity_series",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.5, "melody_seed": 0,
     "bass_pattern": "harmonic_series", "bass_base_dur": 2.0, "n_sections": 5, "use_harmony": True},

    {"key": "C_minor", "tempo": 66, "bars": 32, "melody_pattern": "fibonacci",
     "melody_rhythm": "euclidean_3_8", "melody_base_dur": 0.75, "melody_seed": 5,
     "bass_pattern": "fibonacci", "bass_base_dur": 2.0, "n_sections": 4, "use_harmony": True},

    {"key": "A_minor", "tempo": 80, "bars": 24, "melody_pattern": "golden_spiral",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.5, "melody_seed": 3,
     "bass_pattern": "golden_spiral", "bass_base_dur": 1.0, "n_sections": 3, "use_harmony": True},

    {"key": "G_minor", "tempo": 76, "bars": 32, "melody_pattern": "logistic",
     "melody_rhythm": "euclidean_7_12", "melody_base_dur": 0.25, "melody_seed": 1,
     "bass_pattern": "harmonic_series", "bass_base_dur": 4.0, "n_sections": 5, "use_harmony": True},

    {"key": "E_minor", "tempo": 60, "bars": 48, "melody_pattern": "infinity_series",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 1.0, "melody_seed": 8,
     "bass_pattern": "fibonacci", "bass_base_dur": 2.0, "n_sections": 6, "use_harmony": True},

    {"key": "C_major", "tempo": 120, "bars": 24, "melody_pattern": "fibonacci",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.25, "melody_seed": 12,
     "bass_pattern": "harmonic_series", "bass_base_dur": 1.0, "n_sections": 3, "use_harmony": False},

    {"key": "F_major", "tempo": 88, "bars": 40, "melody_pattern": "golden_spiral",
     "melody_rhythm": "euclidean_3_8", "melody_base_dur": 0.5, "melody_seed": 7,
     "bass_pattern": "golden_spiral", "bass_base_dur": 2.0, "n_sections": 5, "use_harmony": True},

    {"key": "D_major", "tempo": 100, "bars": 32, "melody_pattern": "mandelbrot",
     "melody_rhythm": "euclidean_7_12", "melody_base_dur": 0.5, "melody_seed": 15,
     "bass_pattern": "fibonacci", "bass_base_dur": 1.0, "n_sections": 4, "use_harmony": True},

    {"key": "Bb_major", "tempo": 54, "bars": 64, "melody_pattern": "rossler",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.75, "melody_seed": 20,
     "bass_pattern": "harmonic_series", "bass_base_dur": 4.0, "n_sections": 7, "use_harmony": True},

    {"key": "G_major", "tempo": 92, "bars": 24, "melody_pattern": "infinity_series",
     "melody_rhythm": "euclidean_3_8", "melody_base_dur": 0.25, "melody_seed": 30,
     "bass_pattern": "golden_spiral", "bass_base_dur": 1.0, "n_sections": 3, "use_harmony": False},

    {"key": "D_minor", "tempo": 66, "bars": 48, "melody_pattern": "logistic",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.5, "melody_seed": 42,
     "bass_pattern": "harmonic_series", "bass_base_dur": 2.0, "n_sections": 6, "use_harmony": True},

    {"key": "A_minor", "tempo": 72, "bars": 32, "melody_pattern": "fibonacci",
     "melody_rhythm": "euclidean_7_12", "melody_base_dur": 1.0, "melody_seed": 10,
     "bass_pattern": "fibonacci", "bass_base_dur": 4.0, "n_sections": 4, "use_harmony": True},

    {"key": "E_minor", "tempo": 108, "bars": 24, "melody_pattern": "golden_spiral",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.25, "melody_seed": 25,
     "bass_pattern": "harmonic_series", "bass_base_dur": 1.0, "n_sections": 3, "use_harmony": False},

    {"key": "C_minor", "tempo": 58, "bars": 56, "melody_pattern": "mandelbrot",
     "melody_rhythm": "euclidean_3_8", "melody_base_dur": 0.75, "melody_seed": 35,
     "bass_pattern": "golden_spiral", "bass_base_dur": 2.0, "n_sections": 7, "use_harmony": True},

    {"key": "G_minor", "tempo": 84, "bars": 32, "melody_pattern": "rossler",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.5, "melody_seed": 2,
     "bass_pattern": "fibonacci", "bass_base_dur": 2.0, "n_sections": 5, "use_harmony": True},

    {"key": "F_major", "tempo": 132, "bars": 24, "melody_pattern": "infinity_series",
     "melody_rhythm": "euclidean_7_12", "melody_base_dur": 0.25, "melody_seed": 18,
     "bass_pattern": "harmonic_series", "bass_base_dur": 1.0, "n_sections": 3, "use_harmony": True},

    {"key": "D_minor", "tempo": 52, "bars": 40, "melody_pattern": "fibonacci",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 1.0, "melody_seed": 44,
     "bass_pattern": "golden_spiral", "bass_base_dur": 4.0, "n_sections": 5, "use_harmony": True},

    {"key": "C_major", "tempo": 96, "bars": 32, "melody_pattern": "logistic",
     "melody_rhythm": "euclidean_3_8", "melody_base_dur": 0.5, "melody_seed": 9,
     "bass_pattern": "fibonacci", "bass_base_dur": 2.0, "n_sections": 4, "use_harmony": False},

    {"key": "A_minor", "tempo": 76, "bars": 48, "melody_pattern": "golden_spiral",
     "melody_rhythm": "euclidean_7_12", "melody_base_dur": 0.75, "melody_seed": 22,
     "bass_pattern": "harmonic_series", "bass_base_dur": 2.0, "n_sections": 6, "use_harmony": True},

    {"key": "Bb_major", "tempo": 112, "bars": 24, "melody_pattern": "mandelbrot",
     "melody_rhythm": "euclidean_5_8", "melody_base_dur": 0.25, "melody_seed": 50,
     "bass_pattern": "golden_spiral", "bass_base_dur": 1.0, "n_sections": 3, "use_harmony": True},
]


def compute_fast_features(composition):
    """Extract individual fast-eval features for analysis."""
    voices = composition.score.voices
    if not voices:
        return {}

    melody_notes = [n for n in voices[0].notes if not n.is_rest]
    all_notes = []
    for v in voices:
        all_notes.extend(v.notes)

    total = len(all_notes)
    if total == 0:
        return {}

    pitches = [n.pitch for n in melody_notes]
    intervals = [abs(pitches[i] - pitches[i - 1]) for i in range(1, len(pitches))]
    step_count = sum(1 for iv in intervals if iv <= 2)
    step_ratio = step_count / max(len(intervals), 1)

    rest_count = sum(1 for n in all_notes if n.is_rest)
    rest_ratio = rest_count / total

    if len(voices) >= 2:
        bass_notes = [n for n in voices[1].notes if not n.is_rest]
        bass_pitches = [n.pitch for n in bass_notes]
        bass_changes = sum(
            1 for i in range(1, len(bass_pitches)) if bass_pitches[i] != bass_pitches[i - 1]
        )
        harm_ratio = bass_changes / max(len(bass_pitches) - 1, 1)
    else:
        harm_ratio = 0.5

    pc_counts = Counter(p % 12 for p in pitches)
    total_pc = sum(pc_counts.values())
    entropy = 0.0
    if total_pc > 0:
        for count in pc_counts.values():
            prob = count / total_pc
            if prob > 0:
                entropy -= prob * math.log2(prob)

    # Additional features that might correlate better
    # Leap ratio (intervals > 4 semitones)
    leap_count = sum(1 for iv in intervals if iv > 4)
    leap_ratio = leap_count / max(len(intervals), 1)

    # Direction changes (melodic contour variety)
    signed = [pitches[i] - pitches[i-1] for i in range(1, len(pitches))]
    dir_changes = sum(1 for i in range(1, len(signed)) if signed[i] * signed[i-1] < 0)
    dir_change_ratio = dir_changes / max(len(signed) - 1, 1)

    # Note count (complexity proxy)
    note_count = len(melody_notes)

    # Pitch range
    pitch_range = max(pitches) - min(pitches) if pitches else 0

    # Average velocity variation
    velocities = [n.velocity for n in melody_notes]
    vel_std = 0
    if len(velocities) > 1:
        mean_v = sum(velocities) / len(velocities)
        vel_std = math.sqrt(sum((v - mean_v)**2 for v in velocities) / len(velocities))

    # Number of distinct pitch classes used
    n_pitch_classes = len(pc_counts)

    # Bigram entropy (local predictability - matches L4 intentionality)
    bigrams = Counter()
    for i in range(1, len(pitches)):
        bigrams[(pitches[i-1] % 12, pitches[i] % 12)] += 1
    bigram_total = sum(bigrams.values())
    bigram_entropy = 0.0
    if bigram_total > 0:
        for count in bigrams.values():
            prob = count / bigram_total
            if prob > 0:
                bigram_entropy -= prob * math.log2(prob)

    return {
        "step_ratio": step_ratio,
        "rest_ratio": rest_ratio,
        "harm_ratio": harm_ratio,
        "entropy": entropy,
        "leap_ratio": leap_ratio,
        "dir_change_ratio": dir_change_ratio,
        "note_count": note_count,
        "pitch_range": pitch_range,
        "vel_std": vel_std,
        "n_pitch_classes": n_pitch_classes,
        "bigram_entropy": bigram_entropy,
    }


def main():
    results = []
    total_start = time.time()

    for i, cfg in enumerate(CONFIGS):
        print(f"\n--- Config {i+1}/{len(CONFIGS)}: {cfg['key']} {cfg['melody_pattern']} ---")
        t0 = time.time()

        try:
            comp = build_from_params(cfg)
            fast_score = evaluate_fast(comp)
            features = compute_fast_features(comp)

            print(f"  Fast eval: {fast_score:.1f} ({time.time()-t0:.2f}s)")

            t1 = time.time()
            full_report = evaluate_composition(comp, verbose=False)
            full_score = full_report["final_score"]
            full_metrics = full_report.get("metrics", {})

            print(f"  Full eval: {full_score:.1f} ({time.time()-t1:.1f}s)")
            print(f"  L1 pass: {full_report['level1_pass']}, L2: {full_report['level2_score']:.1f}, L3: {full_report['level3_score']:.1f}, L4: {full_report['level4_score']:.1f}")

            results.append({
                "config_idx": i,
                "key": cfg["key"],
                "melody_pattern": cfg["melody_pattern"],
                "fast_score": fast_score,
                "full_score": full_score,
                "level1_pass": full_report["level1_pass"],
                "level2_score": full_report["level2_score"],
                "level3_score": full_report["level3_score"],
                "level4_score": full_report["level4_score"],
                "features": features,
                "full_metrics": full_metrics,
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

        elapsed = time.time() - total_start
        print(f"  Total elapsed: {elapsed:.0f}s")

        # If taking too long, reduce to 10
        if elapsed > 360 and len(results) >= 10:
            print(f"\n*** Time budget exceeded after {len(results)} configs, stopping ***")
            break

    # Save raw data
    with open("calibration_data.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\n{'='*72}")
    print("CALIBRATION DATA")
    print(f"{'='*72}")
    print(f"\n{'Config':>8} {'Key':>10} {'Pattern':>16} {'Fast':>6} {'Full':>6} {'Delta':>6}")
    print("-" * 60)

    fast_scores = []
    full_scores = []
    for r in results:
        delta = r["fast_score"] - r["full_score"]
        print(f"{r['config_idx']:>8} {r['key']:>10} {r['melody_pattern']:>16} {r['fast_score']:>6.1f} {r['full_score']:>6.1f} {delta:>+6.1f}")
        fast_scores.append(r["fast_score"])
        full_scores.append(r["full_score"])

    # Compute correlation
    n = len(fast_scores)
    if n >= 3:
        mean_f = sum(fast_scores) / n
        mean_g = sum(full_scores) / n
        cov = sum((f - mean_f) * (g - mean_g) for f, g in zip(fast_scores, full_scores)) / n
        std_f = math.sqrt(sum((f - mean_f)**2 for f in fast_scores) / n)
        std_g = math.sqrt(sum((g - mean_g)**2 for g in full_scores) / n)

        if std_f > 0 and std_g > 0:
            r_val = cov / (std_f * std_g)
            r_sq = r_val ** 2
        else:
            r_val = 0
            r_sq = 0

        ss_res = sum((f - g)**2 for f, g in zip(fast_scores, full_scores))
        ss_tot = sum((g - mean_g)**2 for g in full_scores)

        print(f"\nPearson r:  {r_val:.4f}")
        print(f"R-squared:  {r_sq:.4f}")
        print(f"Mean fast:  {mean_f:.1f}")
        print(f"Mean full:  {mean_g:.1f}")
        print(f"Std fast:   {std_f:.1f}")
        print(f"Std full:   {std_g:.1f}")

    # Feature correlation analysis
    print(f"\n{'='*72}")
    print("FEATURE CORRELATION WITH FULL SCORE")
    print(f"{'='*72}")

    feature_names = list(results[0]["features"].keys()) if results else []
    for feat_name in feature_names:
        vals = [r["features"].get(feat_name, 0) for r in results]
        mean_v = sum(vals) / n
        std_v = math.sqrt(sum((v - mean_v)**2 for v in vals) / n)
        if std_v > 0 and std_g > 0:
            corr = sum((v - mean_v) * (g - mean_g) for v, g in zip(vals, full_scores)) / (n * std_v * std_g)
        else:
            corr = 0
        print(f"  {feat_name:>20}: r = {corr:+.4f}  mean = {mean_v:.3f}  std = {std_v:.3f}")

    # Full metric correlation with individual features
    print(f"\n{'='*72}")
    print("FULL EVAL INDIVIDUAL METRIC SCORES (sample)")
    print(f"{'='*72}")
    if results:
        metric_names = list(results[0].get("full_metrics", {}).keys())
        for mn in metric_names:
            vals = [r.get("full_metrics", {}).get(mn, 0) for r in results]
            mean_m = sum(vals) / len(vals)
            print(f"  {mn:>40}: mean = {mean_m:.1f}")

    print(f"\n\nTotal time: {time.time() - total_start:.0f}s")
    print(f"Configs evaluated: {len(results)}")


if __name__ == "__main__":
    main()
