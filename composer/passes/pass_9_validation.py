"""PASS 9: Validation (check rules, report violations)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from SYSTEM_ARCHITECTURE import (
    FormIR, PerformanceIR,
)
from composer.parser import INSTRUMENT_RANGES


@dataclass
class ValidationReport:
    """Validation results from Pass 9."""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = ["=" * 60]
        lines.append("  VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append(f"  Status: {'PASS' if self.is_valid else 'FAIL'}")
        lines.append(f"  Errors:   {len(self.errors)}")
        lines.append(f"  Warnings: {len(self.warnings)}")
        if self.errors:
            lines.append("\n  Errors:")
            for e in self.errors[:15]:
                lines.append(f"    - {e}")
            if len(self.errors) > 15:
                lines.append(f"    ... and {len(self.errors) - 15} more")
        if self.warnings:
            lines.append("\n  Warnings:")
            for w in self.warnings[:10]:
                lines.append(f"    - {w}")
            if len(self.warnings) > 10:
                lines.append(f"    ... and {len(self.warnings) - 10} more")
        lines.append("\n  Scores:")
        for k, v in sorted(self.scores.items()):
            lines.append(f"    {k:35s}: {v:.2f}")
        lines.append("=" * 60)
        return "\n".join(lines)


def _check_range_compliance(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    range_violations = 0
    for n in perf_ir.notes:
        lo, hi = INSTRUMENT_RANGES.get(n.instrument, (21, 108))
        if n.midi_pitch < lo or n.midi_pitch > hi:
            range_violations += 1
            if range_violations <= 5:
                report.errors.append(
                    f"Range: {n.instrument} note {n.midi_pitch} "
                    f"at t={n.start_time_sec:.2f}s (range {lo}-{hi})")
    if range_violations > 5:
        report.errors.append(f"  ... {range_violations - 5} more range violations")
    report.scores["range_compliance"] = 1.0 - (range_violations / max(len(perf_ir.notes), 1))


def _check_velocity_bounds(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    vel_violations = sum(1 for n in perf_ir.notes if n.velocity < 1 or n.velocity > 127)
    report.scores["velocity_bounds"] = 1.0 - (vel_violations / max(len(perf_ir.notes), 1))
    if vel_violations:
        report.errors.append(f"Velocity: {vel_violations} notes outside [1, 127]")


def _check_timing_validity(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    neg_times = sum(1 for n in perf_ir.notes if n.start_time_sec < 0)
    if neg_times:
        report.errors.append(f"Timing: {neg_times} notes with negative start time")
    report.scores["timing_validity"] = 1.0 - (neg_times / max(len(perf_ir.notes), 1))


def _check_bass_spacing(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    bass_notes = defaultdict(list)
    for n in perf_ir.notes:
        if n.midi_pitch < 48:
            bass_notes[round(n.start_time_sec, 2)].append(n.midi_pitch)
    spacing_warnings = 0
    for t, pitches in bass_notes.items():
        if len(pitches) >= 2:
            sorted_p = sorted(pitches)
            for i in range(len(sorted_p) - 1):
                if sorted_p[i + 1] - sorted_p[i] < 7:
                    spacing_warnings += 1
    if spacing_warnings:
        report.warnings.append(f"Bass spacing: {spacing_warnings} close intervals below C3")
    report.scores["bass_spacing"] = 1.0 - min(1.0, spacing_warnings / 20.0)


def _check_parallel_motion(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    by_time = defaultdict(list)
    for n in perf_ir.notes:
        by_time[round(n.start_time_sec, 2)].append(n.midi_pitch)
    times = sorted(by_time.keys())
    parallel_count = 0
    for ti in range(min(len(times) - 1, 200)):
        t1, t2 = times[ti], times[ti + 1]
        p1 = sorted(by_time[t1])
        p2 = sorted(by_time[t2])
        if len(p1) >= 2 and len(p2) >= 2:
            for i in range(min(len(p1), len(p2)) - 1):
                for j in range(i + 1, min(len(p1), len(p2))):
                    int1 = (p1[j] - p1[i]) % 12
                    int2 = (p2[j] - p2[i]) % 12
                    if int1 in (0, 7) and int1 == int2:
                        if p1[i] != p2[i] and p1[j] != p2[j]:
                            parallel_count += 1
    if parallel_count:
        report.warnings.append(f"Parallel 5ths/8ves detected: ~{parallel_count} instances")
    report.scores["voice_leading"] = max(0.0, 1.0 - parallel_count / 50.0)


def _check_humanization(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    nonzero_offsets = sum(1 for n in perf_ir.notes if abs(n.timing_offset_ms) > 0.1)
    humanization_ratio = nonzero_offsets / max(len(perf_ir.notes), 1)
    report.scores["humanization"] = min(1.0, humanization_ratio / 0.8)
    if humanization_ratio < 0.5:
        report.warnings.append("Low humanization: fewer than 50% of notes have timing offsets")


def _check_melodic_intervals(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    melody_notes = sorted(
        [n for n in perf_ir.notes if n.instrument in ("violin1", "flute", "piano", "piano_rh", "piano_s")],
        key=lambda n: n.start_time_sec)
    if len(melody_notes) > 2:
        intervals = [abs(melody_notes[i+1].midi_pitch - melody_notes[i].midi_pitch)
                     for i in range(len(melody_notes) - 1)]
        steps = sum(1 for iv in intervals if iv <= 2)
        step_ratio = steps / max(len(intervals), 1)
        report.scores["melodic_steps_ratio"] = min(1.0, step_ratio / 0.45)
        if step_ratio < 0.3:
            report.warnings.append(f"Melody has too few stepwise intervals: {step_ratio:.1%}")
    else:
        report.scores["melodic_steps_ratio"] = 0.5


def _check_duration_sanity(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    dur_issues = sum(1 for n in perf_ir.notes if n.duration_sec < 0.01 or n.duration_sec > 30)
    report.scores["duration_sanity"] = 1.0 - (dur_issues / max(len(perf_ir.notes), 1))
    if dur_issues:
        report.warnings.append(f"Duration: {dur_issues} notes with extreme durations")


def _check_dynamic_range(perf_ir: PerformanceIR, report: ValidationReport) -> None:
    velocities = [n.velocity for n in perf_ir.notes]
    vel_range = max(velocities) - min(velocities)
    report.scores["dynamic_range"] = min(1.0, vel_range / 40.0)
    if vel_range < 15:
        report.warnings.append(f"Narrow dynamic range: only {vel_range} velocity units")


def _check_total_duration(perf_ir: PerformanceIR, form_ir: FormIR,
                          report: ValidationReport) -> None:
    tempo = form_ir.tempo_bpm
    expected_duration = form_ir.total_bars * 4 * 60.0 / tempo
    actual_duration = perf_ir.total_duration_sec
    duration_ratio = actual_duration / max(expected_duration, 1)
    if duration_ratio < 0.5 or duration_ratio > 2.0:
        report.warnings.append(
            f"Duration mismatch: expected ~{expected_duration:.0f}s, got {actual_duration:.0f}s")
    report.scores["duration_match"] = max(0.0, 1.0 - abs(1.0 - duration_ratio))


def pass_9_validation(perf_ir: PerformanceIR,
                      form_ir: FormIR) -> ValidationReport:
    """
    PASS 9: Check the 50 rules. Returns a validation report.
    """
    report = ValidationReport()

    if not perf_ir.notes:
        report.errors.append("No notes in performance IR!")
        return report

    _check_range_compliance(perf_ir, report)
    _check_velocity_bounds(perf_ir, report)
    _check_timing_validity(perf_ir, report)
    _check_bass_spacing(perf_ir, report)
    _check_parallel_motion(perf_ir, report)
    _check_humanization(perf_ir, report)
    _check_melodic_intervals(perf_ir, report)
    _check_duration_sanity(perf_ir, report)
    _check_dynamic_range(perf_ir, report)
    _check_total_duration(perf_ir, form_ir, report)

    return report
