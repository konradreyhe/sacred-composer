"""Render WAV previews of the top-3 candidates per pattern.

Reads examples/album/seeds/search_<pattern>.csv, renders the top 3
as orchestral WAVs for human auditioning. The human picks one, and
its (pattern, seed, key) goes into examples/album/seeds.json (the
locked album spec).

Usage:
    python examples/album/render_candidates.py --pattern fibonacci
    python examples/album/render_candidates.py --all
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sacred_composer.builder import CompositionBuilder


SEEDS_DIR = Path(__file__).parent / "seeds"
AUDITION_DIR = Path(__file__).parent / "audition"
AUDITION_DIR.mkdir(exist_ok=True)


def render_candidate(pattern: str, seed: int, key: str, rank: int) -> Path:
    out = AUDITION_DIR / f"{pattern}__{rank:02d}__seed{seed}_{key}.wav"
    comp = (
        CompositionBuilder(key=key, tempo=72, bars=48,
                           title=f"{pattern} · seed={seed} · {key}")
        .form(pattern="fibonacci", n_sections=5)
        .melody(pattern=pattern, instrument="violin", seed=seed)
        .bass(pattern="harmonic_series", instrument="cello", seed=seed + 10)
        .build()
    )
    comp.render(str(out))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", type=str, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--top", type=int, default=3,
                        help="Render top-N candidates per pattern (default: 3)")
    args = parser.parse_args()

    csvs = sorted(SEEDS_DIR.glob("search_*.csv"))
    if not args.all and args.pattern:
        csvs = [SEEDS_DIR / f"search_{args.pattern}.csv"]
    if not csvs:
        print("No search_*.csv files found. Run search_seeds.py first.")
        return

    for path in csvs:
        if not path.exists():
            print(f"Missing: {path}")
            continue
        pattern = path.stem.replace("search_", "")
        print(f"Rendering top-{args.top} for {pattern}")
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for rank, row in enumerate(rows[:args.top], start=1):
            seed = int(row["seed"])
            key = row["key"]
            score = float(row["score"])
            out = render_candidate(pattern, seed, key, rank)
            print(f"  {rank}. score={score:.2f} seed={seed:3d} {key:10s} -> {out.name}")
        print()


if __name__ == "__main__":
    main()
