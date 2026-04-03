"""CLI entry point: python -m composer [prompt]"""

from __future__ import annotations

import sys

from composer.pipeline import compose, compose_suite
from composer.parser import SAMPLE_PROMPTS


if __name__ == "__main__":
    # Accept prompt from command line or use default
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = SAMPLE_PROMPTS[0]
        print(f"No prompt given; using default: \"{prompt}\"\n")

    perf_ir, form_ir, report = compose(
        prompt,
        output_file="composed_output.mid",
        seed=42,
    )

    # Also generate a second example to demonstrate versatility
    print("\n\n" + "#" * 60)
    print("# SECOND EXAMPLE")
    print("#" * 60 + "\n")

    compose(
        "A string quartet theme and 3 variations in G major, lyrical",
        output_file="composed_variations.mid",
        seed=123,
    )

    # Rondo test
    print("\n\n" + "#" * 60)
    print("# RONDO TEST")
    print("#" * 60 + "\n")

    compose(
        "A lively rondo in A major, 40 bars, for piano",
        output_file="output/rondo_test.mid",
        seed=42,
    )

    # Improved fugue test
    print("\n\n" + "#" * 60)
    print("# IMPROVED FUGUE TEST")
    print("#" * 60 + "\n")

    compose(
        "A Bach-style fugue in D minor, 28 bars, for piano",
        output_file="output/fugue_improved.mid",
        seed=42,
    )

    # Suite test
    print("\n\n" + "#" * 60)
    print("# MULTI-MOVEMENT SUITE TEST")
    print("#" * 60 + "\n")

    compose_suite(
        "A classical suite in D minor, 3 movements, for piano",
        output_path="output/suite.mid",
        seed=42,
    )
