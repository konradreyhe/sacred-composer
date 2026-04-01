"""
test_compositions.py -- Ambitious stress-test for the composition pipeline.

Generates 3 compositions that push the system beyond its default
"C minor sonata" comfort zone:

  1. D minor sonata exposition for string quartet (48 bars)
  2. F major theme and 4 variations for piano (64 bars)
  3. Bb minor ternary form for orchestra (36 bars)

Each composition is timed, and basic statistics are printed.
"""

from __future__ import annotations

import sys
import time
import traceback

from composer import compose, parse_prompt, pass_1_plan


# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------

TESTS = [
    {
        "id": "sonata_d_minor",
        "prompt": "A dramatic sonata exposition in D minor, 48 bars, for string quartet",
        "output": "test_sonata_d_minor.mid",
        "seed": 42,
        "description": (
            "Tests: minor key, longer form (48 bars), 4 independent voices, "
            "modulation to relative major (F major)."
        ),
    },
    {
        "id": "variations_f_major",
        "prompt": "A serene theme and 4 variations in F major, 64 bars, for piano",
        "output": "test_variations_f_major.mid",
        "seed": 77,
        "description": (
            "Tests: variation techniques, 5 sections (theme + 4 vars), "
            "mode/texture changes per variation, 64 bars for piano."
        ),
    },
    {
        "id": "ternary_bb_minor",
        "prompt": "A mysterious ternary form in Bb minor, 36 bars, for orchestra",
        "output": "test_ternary_bb_minor.mid",
        "seed": 101,
        "description": (
            "Tests: flat key (Bb minor), orchestral scoring (10 instruments), "
            "contrasting middle section, atmospheric character."
        ),
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_test(test: dict) -> dict:
    """Run a single composition test, capturing timing and stats."""
    result = {
        "id": test["id"],
        "prompt": test["prompt"],
        "success": False,
        "error": None,
        "total_time_sec": 0.0,
        "notes": 0,
        "bars": 0,
        "voices": 0,
        "duration_sec": 0.0,
        "validation_pass": False,
        "avg_quality": 0.0,
    }

    print("\n" + "=" * 70)
    print(f"  TEST: {test['id']}")
    print(f"  {test['description']}")
    print("=" * 70)

    t0 = time.perf_counter()
    try:
        perf_ir, form_ir, report = compose(
            test["prompt"],
            output_file=test["output"],
            seed=test["seed"],
        )
        elapsed = time.perf_counter() - t0

        result["success"] = True
        result["total_time_sec"] = elapsed
        result["notes"] = len(perf_ir.notes)
        result["bars"] = form_ir.total_bars
        result["voices"] = len(set(n.instrument for n in perf_ir.notes))
        result["duration_sec"] = perf_ir.total_duration_sec
        result["validation_pass"] = report.is_valid
        import numpy as np
        result["avg_quality"] = float(np.mean(list(report.scores.values()))) if report.scores else 0.0

    except Exception as e:
        elapsed = time.perf_counter() - t0
        result["total_time_sec"] = elapsed
        result["error"] = f"{type(e).__name__}: {e}"
        print(f"\n  *** PIPELINE CRASHED ***")
        traceback.print_exc()

    return result


def print_summary(results: list):
    """Print a final summary table."""
    print("\n\n" + "=" * 70)
    print("  STRESS-TEST SUMMARY")
    print("=" * 70)
    print(f"  {'Test ID':<28s} {'Status':<8s} {'Notes':>6s} {'Bars':>5s} "
          f"{'Voices':>7s} {'Dur(s)':>7s} {'Time(s)':>8s} {'Quality':>8s}")
    print("-" * 70)

    all_pass = True
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        if not r["success"]:
            all_pass = False
        qual = f"{r['avg_quality']:.2f}" if r["success"] else "N/A"
        print(f"  {r['id']:<28s} {status:<8s} {r['notes']:>6d} {r['bars']:>5d} "
              f"{r['voices']:>7d} {r['duration_sec']:>7.1f} {r['total_time_sec']:>8.1f} {qual:>8s}")
        if r["error"]:
            print(f"    ERROR: {r['error']}")

    print("-" * 70)
    total_notes = sum(r["notes"] for r in results)
    total_time = sum(r["total_time_sec"] for r in results)
    print(f"  {'TOTAL':<28s} {'OK' if all_pass else 'FAIL':<8s} {total_notes:>6d} "
          f"{'':>5s} {'':>7s} {'':>7s} {total_time:>8.1f}")
    print("=" * 70)

    if all_pass:
        print("\n  All 3 compositions generated successfully.")
    else:
        failed = [r["id"] for r in results if not r["success"]]
        print(f"\n  FAILURES: {', '.join(failed)}")

    return all_pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("  COMPOSITION PIPELINE STRESS TEST")
    print("  3 ambitious compositions beyond the default comfort zone")
    print("=" * 70)

    results = []
    for test in TESTS:
        result = run_test(test)
        results.append(result)

    success = print_summary(results)
    sys.exit(0 if success else 1)
