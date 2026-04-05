"""Grid search for the best seed/key combination per pattern.

For each pattern in PATTERNS, render N_SEEDS × len(KEYS) compositions
with the canonical voice setup (melody+bass), run the evaluator, and
record the top candidates in a CSV.

Later steps (listen, lock, render to WAV) are manual — this script
just narrows the search space from thousands to a human-auditionable
top-10 per pattern.

Usage:
    python examples/album/search_seeds.py --pattern fibonacci --seeds 100
    python examples/album/search_seeds.py --all      # search every pattern
    python examples/album/search_seeds.py --pattern golden_spiral --seeds 50 --keys Bb_minor,D_minor
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sacred_composer.builder import CompositionBuilder
from evaluation_framework import evaluate_midi


# Patterns that run cleanly in the current builder (no harmony mode).
PATTERNS = [
    "fibonacci",
    "infinity_series",
    "golden_spiral",
    "harmonic_series",
    "logistic",
    "mandelbrot",
    "rossler",
    "cantor",
    "zipf",
]

# Keys spanning minor/major, sharps/flats. Bb_minor is our known peak.
KEYS_DEFAULT = [
    "C_minor", "D_minor", "E_minor", "G_minor", "A_minor",
    "Bb_minor", "C#_minor", "F#_minor",
    "C_major", "D_major", "F_major", "G_major",
]

OUT_DIR = Path(__file__).parent / "seeds"
OUT_DIR.mkdir(exist_ok=True)


def evaluate_config(pattern: str, key: str, seed: int) -> tuple[float, bool, dict]:
    """Render one composition, return (final_score, L1_pass, per_metric_dict)."""
    tmp = OUT_DIR / "_tmp_search.mid"
    comp = (
        CompositionBuilder(key=key, tempo=72, bars=48)
        .form(pattern="fibonacci", n_sections=5)
        .melody(pattern=pattern, instrument="violin", seed=seed)
        .bass(pattern="harmonic_series", instrument="cello", seed=seed + 10)
        .build()
    )
    comp.render(str(tmp))
    rep = evaluate_midi(str(tmp))
    metrics = {m.name: round(m.score, 2) for m in rep.metrics}
    os.remove(tmp)
    return rep.final_score, rep.level1_pass, metrics


def search_pattern(pattern: str, seeds: int, keys: list[str]) -> list[dict]:
    """Run grid search for one pattern. Returns sorted list of top candidates."""
    results = []
    total = seeds * len(keys)
    print(f"  Searching {pattern}: {total} candidates ({seeds} seeds × {len(keys)} keys)")
    i = 0
    for key in keys:
        for seed in range(1, seeds + 1):
            i += 1
            try:
                score, l1, metrics = evaluate_config(pattern, key, seed)
            except Exception as e:
                print(f"    ERR seed={seed} key={key}: {e}")
                continue
            results.append({
                "pattern": pattern, "key": key, "seed": seed,
                "score": score, "l1_pass": l1, **metrics,
            })
            if i % 50 == 0:
                print(f"    {i}/{total}  best-so-far: {max(r['score'] for r in results):.2f}")
    # Sort by score desc, L1 pass first
    results.sort(key=lambda r: (-int(r["l1_pass"]), -r["score"]))
    return results


def save_csv(results: list[dict], pattern: str, top_n: int = 20) -> Path:
    path = OUT_DIR / f"search_{pattern}.csv"
    if not results:
        print(f"  No results for {pattern}")
        return path
    fields = list(results[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results[:top_n]:
            w.writerow(r)
    print(f"  Saved top {min(top_n, len(results))} to {path}")
    # Print top 5 summary
    print(f"  TOP 5 for {pattern}:")
    for r in results[:5]:
        mark = "L1" if r["l1_pass"] else ".."
        print(f"    {mark}  seed={r['seed']:3d}  key={r['key']:10s}  score={r['score']:.2f}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", type=str, default=None,
                        help="Single pattern to search (default: all)")
    parser.add_argument("--all", action="store_true",
                        help="Search every pattern in PATTERNS")
    parser.add_argument("--seeds", type=int, default=40,
                        help="How many seeds per key (default: 40)")
    parser.add_argument("--keys", type=str, default=None,
                        help="Comma-separated keys (default: 12 standard)")
    args = parser.parse_args()

    keys = args.keys.split(",") if args.keys else KEYS_DEFAULT

    if args.all:
        patterns = PATTERNS
    elif args.pattern:
        patterns = [args.pattern]
    else:
        parser.error("Specify --pattern NAME or --all")

    print(f"Keys: {keys}")
    print(f"Seeds per key: {args.seeds}")
    print(f"Patterns: {patterns}")
    print()

    for pattern in patterns:
        results = search_pattern(pattern, args.seeds, keys)
        save_csv(results, pattern)
        print()


if __name__ == "__main__":
    main()
