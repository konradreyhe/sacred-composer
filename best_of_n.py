"""
BEST-OF-N Composition Selector
===============================
Generates N compositions with different seeds, evaluates each, picks the winner.

Usage:
    python best_of_n.py "A dramatic sonata exposition in C minor, heroic, 40 bars, for piano" --n 10
    python best_of_n.py --all-forms --n 5

Library:
    from best_of_n import compose_best
    path, score, report = compose_best("A dramatic sonata in C minor", n=10)
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import tempfile
from typing import List, Optional, Tuple

from composer import compose
from evaluation_framework import EvaluationReport, evaluate_midi


# Default prompts per form for --all-forms mode
FORM_PROMPTS = {
    "sonata":     "A dramatic sonata exposition in C minor, heroic character, 40 bars, for piano",
    "ternary":    "A lyrical ternary piece in Bb minor, expressive, 32 bars, for piano",
    "variations": "A theme and variations in F major, elegant, 48 bars, for piano",
}


def compose_best(
    prompt: str,
    n: int = 10,
    output_path: str = "best_composition.mid",
) -> Tuple[str, float, EvaluationReport]:
    """Generate n compositions, evaluate each, return the best."""
    candidates: List[Tuple[int, float, EvaluationReport, str]] = []
    tmpdir = tempfile.mkdtemp(prefix="best_of_n_")

    print(f"\n{'='*60}")
    print(f"  BEST-OF-{n}: Generating {n} candidates")
    print(f"{'='*60}")
    print(f"  Prompt: \"{prompt}\"\n")

    for i in range(n):
        seed = i * 37 + 7
        tmp_path = os.path.join(tmpdir, f"candidate_{i}.mid")
        print(f"\n--- Candidate {i+1}/{n} (seed={seed}) ---")
        try:
            random.seed(seed)
            compose(prompt, output_file=tmp_path, seed=seed)
            report = evaluate_midi(tmp_path)
            score = report.final_score
            candidates.append((seed, score, report, tmp_path))
            print(f"  -> Score: {score:.1f}/100")
        except Exception as e:
            print(f"  -> FAILED: {e}")

    if not candidates:
        raise RuntimeError("All candidates failed to generate.")

    # Sort descending by score
    candidates.sort(key=lambda c: c[1], reverse=True)

    # Print leaderboard
    print(f"\n{'='*60}")
    print(f"  LEADERBOARD")
    print(f"{'='*60}")
    print(f"  {'Rank':<6} {'Seed':<8} {'Score':<10} {'L1':>4} {'L2':>6} {'L3':>6} {'L4':>6}")
    print(f"  {'-'*50}")
    for rank, (seed, score, report, _) in enumerate(candidates, 1):
        l1 = "PASS" if report.level1_pass else "FAIL"
        print(f"  {rank:<6} {seed:<8} {score:<10.1f} {l1:>4} {report.level2_score:>6.1f} "
              f"{report.level3_score:>6.1f} {report.level4_score:>6.1f}")

    # Copy winner to output path
    best_seed, best_score, best_report, best_tmp = candidates[0]
    shutil.copy2(best_tmp, output_path)
    print(f"\n  WINNER: seed={best_seed}, score={best_score:.1f}/100")
    print(f"  Saved to: {output_path}\n")

    # Clean up temp files
    shutil.rmtree(tmpdir, ignore_errors=True)

    return output_path, best_score, best_report


def run_all_forms(n: int = 5) -> None:
    """Generate n candidates for each form and pick the best of each."""
    for form_name, prompt in FORM_PROMPTS.items():
        out = f"best_{form_name}.mid"
        path, score, _ = compose_best(prompt, n=n, output_path=out)
        print(f"  Best {form_name}: {score:.1f}/100 -> {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Best-of-N composition selector")
    parser.add_argument("prompt", nargs="?", default=None, help="Composition prompt")
    parser.add_argument("--n", type=int, default=10, help="Number of candidates (default: 10)")
    parser.add_argument("--output", "-o", default="best_composition.mid", help="Output MIDI path")
    parser.add_argument("--all-forms", action="store_true", help="Test multiple forms, pick best of each")
    args = parser.parse_args()

    if args.all_forms:
        run_all_forms(n=args.n)
    elif args.prompt:
        compose_best(args.prompt, n=args.n, output_path=args.output)
    else:
        parser.print_help()
