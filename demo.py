#!/usr/bin/env python3
"""
MUSIK! DEMO SCRIPT
==================
Showcases every supported compositional form with different keys and characters.

Usage:
    python demo.py              # full demo (best-of-5 per form)
    python demo.py --quick      # one attempt per form, no best-of-N
    python demo.py --form fugue # generate just one form
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Dict, List, NamedTuple

from composer import compose
from evaluation_framework import EvaluationReport, evaluate_midi
from best_of_n import compose_best
from render_audio import render

# ---------------------------------------------------------------------------
# Demo pieces definition
# ---------------------------------------------------------------------------

class DemoPiece(NamedTuple):
    form: str
    prompt: str
    key: str
    character: str
    midi_file: str
    listen_for: str


DEMO_PIECES: List[DemoPiece] = [
    DemoPiece(
        form="Sonata",
        prompt="A dramatic sonata exposition in C minor, heroic character, 40 bars, for piano",
        key="C minor",
        character="heroic",
        midi_file="demo_sonata.mid",
        listen_for=(
            "Listen for the bold first theme in C minor, a lyrical second theme "
            "in Eb major, and the dramatic closing group with cadential drive."
        ),
    ),
    DemoPiece(
        form="Ternary",
        prompt="A lyrical ternary piece in F major, expressive and singing, 32 bars, for piano",
        key="F major",
        character="lyrical",
        midi_file="demo_ternary.mid",
        listen_for=(
            "Listen for the warm A section melody in F major, a contrasting "
            "B section with new harmonic color, and the return of A with subtle variation."
        ),
    ),
    DemoPiece(
        form="Variations",
        prompt="A theme and variations in D major, graceful and elegant, 48 bars, for piano",
        key="D major",
        character="graceful",
        midi_file="demo_variations.mid",
        listen_for=(
            "Listen for the simple, memorable theme, then follow how each variation "
            "transforms it -- ornamentation, rhythmic change, minor-mode shift."
        ),
    ),
    DemoPiece(
        form="Fugue",
        prompt="A 3-voice fugue in G minor, Bach-style, learned and contrapuntal, 32 bars, for piano",
        key="G minor",
        character="bach",
        midi_file="demo_fugue.mid",
        listen_for=(
            "Listen for the subject entering one voice at a time, the tonal answer "
            "a fifth above, and the interplay of voices in the episodes and stretto."
        ),
    ),
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "demo")


# ---------------------------------------------------------------------------
# Core demo logic
# ---------------------------------------------------------------------------

class Result(NamedTuple):
    form: str
    key: str
    character: str
    score: float
    midi_path: str


def generate_piece(piece: DemoPiece, use_best_of: int = 5) -> Result:
    """Generate a single demo piece, evaluate it, optionally render audio."""
    midi_path = os.path.join(OUTPUT_DIR, piece.midi_file)

    print(f"\n{'#' * 60}")
    print(f"  {piece.form.upper()} -- {piece.key}, {piece.character}")
    print(f"{'#' * 60}")
    print(f"  {piece.listen_for}\n")

    if use_best_of > 1:
        _, score, report = compose_best(piece.prompt, n=use_best_of, output_path=midi_path)
    else:
        compose(piece.prompt, output_file=midi_path, seed=42)
        report = evaluate_midi(midi_path)
        score = report.final_score

    print(f"\n  Evaluation: {score:.1f}/100")
    print(f"    L1 (rules):      {'PASS' if report.level1_pass else 'FAIL'}")
    print(f"    L2 (statistical): {report.level2_score:.1f}")
    print(f"    L3 (structural):  {report.level3_score:.1f}")
    print(f"    L4 (perceptual):  {report.level4_score:.1f}")

    # Attempt audio render
    wav_path = os.path.splitext(midi_path)[0] + ".wav"
    try:
        print()
        render(midi_path, wav_path)
    except Exception as e:
        print(f"  Audio render skipped: {e}")

    return Result(piece.form, piece.key, piece.character, score, piece.midi_file)


def print_summary(results: List[Result]) -> None:
    """Print the final summary table."""
    print(f"\n\n{'=' * 64}")
    print("  DEMO RESULTS")
    print(f"{'=' * 64}")
    header = f"  {'Form':<14} {'Key':<10} {'Character':<12} {'Score':>6}   {'File'}"
    print(header)
    print(f"  {'-' * 58}")
    for r in results:
        print(f"  {r.form:<14} {r.key:<10} {r.character:<12} {r.score:>5.1f}   {r.midi_path}")
    avg = sum(r.score for r in results) / len(results) if results else 0.0
    print(f"  {'-' * 58}")
    print(f"  Average: {avg:.1f}/100")
    print(f"{'=' * 64}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MUSIK! Demo -- generate one piece in every supported form",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: one attempt per form, no best-of-N selection",
    )
    parser.add_argument(
        "--form", type=str, default=None,
        choices=[p.form.lower() for p in DEMO_PIECES],
        help="Generate only one specific form",
    )
    parser.add_argument(
        "--best-of", type=int, default=5,
        help="Number of candidates for best-of-N selection (default: 5)",
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    n = 1 if args.quick else args.best_of
    pieces = DEMO_PIECES
    if args.form:
        pieces = [p for p in pieces if p.form.lower() == args.form]

    print("=" * 64)
    print("  MUSIK! COMPREHENSIVE DEMO")
    print(f"  Forms: {len(pieces)}  |  Best-of-N: {n}  |  Output: {OUTPUT_DIR}")
    print("=" * 64)

    t0 = time.time()
    results: List[Result] = []

    for piece in pieces:
        try:
            result = generate_piece(piece, use_best_of=n)
            results.append(result)
        except Exception as e:
            print(f"\n  ERROR generating {piece.form}: {e}")

    elapsed = time.time() - t0
    print_summary(results)
    print(f"  Total time: {elapsed:.0f}s ({elapsed / 60:.1f} min)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
