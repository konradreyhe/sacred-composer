"""
COMPOSER.PY -- Compatibility shim
===================================
This file re-exports everything from the composer/ package so that
existing imports continue to work unchanged:

    from composer import compose, compose_suite
    from composer import compose, parse_prompt, pass_1_plan

The actual implementation lives in the composer/ package directory.
"""

# Re-export the full public API from the package
from composer import *  # noqa: F401, F403

# Explicit re-exports for anything that other files import by name
from composer import compose, compose_suite, parse_prompt, pass_1_plan
from composer import ValidationReport, SAMPLE_PROMPTS


if __name__ == "__main__":
    import sys
    from composer.parser import SAMPLE_PROMPTS as _PROMPTS

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = _PROMPTS[0]
        print(f"No prompt given; using default: \"{prompt}\"\n")

    perf_ir, form_ir, report = compose(
        prompt,
        output_file="composed_output.mid",
        seed=42,
    )

    print("\n\n" + "#" * 60)
    print("# SECOND EXAMPLE")
    print("#" * 60 + "\n")

    compose(
        "A string quartet theme and 3 variations in G major, lyrical",
        output_file="composed_variations.mid",
        seed=123,
    )

    print("\n\n" + "#" * 60)
    print("# RONDO TEST")
    print("#" * 60 + "\n")

    compose(
        "A lively rondo in A major, 40 bars, for piano",
        output_file="output/rondo_test.mid",
        seed=42,
    )

    print("\n\n" + "#" * 60)
    print("# IMPROVED FUGUE TEST")
    print("#" * 60 + "\n")

    compose(
        "A Bach-style fugue in D minor, 28 bars, for piano",
        output_file="output/fugue_improved.mid",
        seed=42,
    )

    print("\n\n" + "#" * 60)
    print("# MULTI-MOVEMENT SUITE TEST")
    print("#" * 60 + "\n")

    compose_suite(
        "A classical suite in D minor, 3 movements, for piano",
        output_path="output/suite.mid",
        seed=42,
    )
