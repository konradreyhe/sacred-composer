"""Evaluation integration — score Sacred Composer output with the 50 Rules framework.

Renders a Composition to a temporary MIDI file, runs the full evaluation
pipeline, and returns the report.
"""

from __future__ import annotations

import os
import sys
import tempfile

from sacred_composer.core import Composition


def evaluate_composition(composition: Composition, verbose: bool = True) -> dict:
    """Evaluate a Sacred Composer composition using the full evaluation framework.

    Parameters
    ----------
    composition : The composition to evaluate.
    verbose : Print summary to stdout.

    Returns
    -------
    dict with keys: final_score, level1_pass, level2_score, level3_score,
    level4_score, rule_violations, metrics, summary.
    """
    # Import evaluation framework from project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    try:
        from evaluation_framework import evaluate_midi
    except ImportError:
        return _fallback_evaluate(composition, verbose)

    # Render to temp MIDI
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
        tmp_path = f.name

    try:
        composition.render(tmp_path)
        report = evaluate_midi(tmp_path)

        result = {
            "final_score": report.final_score,
            "level1_pass": report.level1_pass,
            "level2_score": report.level2_score,
            "level3_score": report.level3_score,
            "level4_score": report.level4_score,
            "rule_violations": len(report.rule_violations),
            "metrics": {m.name: m.score for m in report.metrics},
            "summary": report.summary() if hasattr(report, "summary") else str(report),
        }

        if verbose:
            print(f"\n  Evaluation: {composition.title}")
            print(f"  Final Score: {result['final_score']:.1f}/100")
            print(f"  Level 1 (Rules):      {'PASS' if result['level1_pass'] else 'FAIL'} ({result['rule_violations']} violations)")
            print(f"  Level 2 (Structure):   {result['level2_score']:.1f}")
            print(f"  Level 3 (Expression):  {result['level3_score']:.1f}")
            print(f"  Level 4 (Performance): {result['level4_score']:.1f}")

        return result

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _fallback_evaluate(composition: Composition, verbose: bool) -> dict:
    """Basic self-evaluation when the full framework isn't available."""
    info = composition.info()
    score = Score()

    # Basic heuristic checks
    checks = {
        "has_notes": info["total_notes"] > 0,
        "reasonable_duration": 10 < info["duration_seconds"] < 600,
        "multiple_voices": info["voices"] >= 1,
        "has_form": info["form_sections"] > 0,
    }

    passed = sum(checks.values())
    total = len(checks)
    estimated_score = (passed / total) * 80  # max 80 without full eval

    result = {
        "final_score": estimated_score,
        "level1_pass": all(checks.values()),
        "level2_score": estimated_score,
        "level3_score": 0.0,
        "level4_score": 0.0,
        "rule_violations": total - passed,
        "metrics": checks,
        "summary": f"Basic eval: {passed}/{total} checks passed (full framework not available)",
    }

    if verbose:
        print(f"\n  Basic Evaluation: {composition.title}")
        print(f"  Estimated Score: {estimated_score:.0f}/100 (install music21 for full eval)")
        for name, passed in checks.items():
            print(f"    {'PASS' if passed else 'FAIL'}: {name}")

    return result


class Score:
    """Placeholder to avoid import issues."""
    pass
