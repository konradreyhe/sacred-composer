"""Psychoacoustic models for perceptually optimal composition.

Research-backed algorithms that exploit how the brain processes music.
Each function includes citations and numerical targets from the literature.

References:
    Huron (2006) Sweet Anticipation — expectation/surprise 75/25 rule
    Sloboda (1991) JRSMPE — frisson triggers (appoggiatura, enharmonic)
    Bregman (1990) Auditory Scene Analysis — stream segregation
    Plomp & Levelt (1965) JASA — roughness/critical bandwidth
    Sethares (2005) Tuning, Timbre, Spectrum, Scale — dissonance curves
    Parncutt (1989) Harmony: A Psychoacoustical Approach — pitch commonality
    London (2012) Hearing in Time — groove and micro-timing
    Iyer (2002) Music Perception — micro-timing deviations
    Kahneman (2000) peak-end rule applied to musical experience
    Jakubowski et al. (2017) Psychology of Aesthetics — earworm features
    Huron & Margulis (2010) — information-theoretic surprise
    Chabris (1999) — 1/f spectral slope in music
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import numpy as np


# =============================================================================
# 1. EXPECTATION / SURPRISE — THE 75/25 RULE (Huron 2006)
# =============================================================================
#
# Huron's ITPRA theory: listeners derive pleasure from both confirmed
# predictions (75%) and violated expectations (25%). The sweet spot is
# ~2.0-3.0 bits of entropy per event (Shannon, measured on pitch-class
# bigrams). Too low = boring (< 1.5 bits), too high = random (> 3.5 bits).
#
# "Surprise" in each domain:
#   Pitch:   interval not predicted by bigram model (IC > 2 bits)
#   Rhythm:  syncopation, unexpected duration change
#   Harmony: non-diatonic chord, deceptive cadence (V -> vi)
#
# Target: information content (IC) of ~25% of events > 2.0 bits

def information_content(sequence: Sequence[int], order: int = 1) -> list[float]:
    """Compute information content (surprise) for each event in a sequence.

    IC(x_i) = -log2(P(x_i | context))

    Uses an n-gram model of the given order. Order=1 means bigram
    (each event conditioned on one previous event).

    Returns IC in bits for each event (first `order` events get 0.0).

    Reference: Huron & Margulis (2010), Pearce (2005) IDyOM model.
    """
    ic_values = [0.0] * order

    # Build transition counts
    ngram_counts: dict[tuple, Counter] = {}
    for i in range(order, len(sequence)):
        context = tuple(sequence[i - order:i])
        if context not in ngram_counts:
            ngram_counts[context] = Counter()
        ngram_counts[context][sequence[i]] += 1

    # Compute IC for each event using add-delta smoothing (delta=0.1)
    # This prevents zero probabilities without inflating surprise for common events
    delta = 0.1
    vocab_size = len(set(sequence))  # number of distinct symbols observed
    for i in range(order, len(sequence)):
        context = tuple(sequence[i - order:i])
        counts = ngram_counts.get(context)
        if counts is None:
            ic_values.append(4.0)  # max surprise for unseen context
            continue
        total = sum(counts.values()) + delta * vocab_size
        count = counts.get(sequence[i], 0) + delta
        prob = count / total
        ic_values.append(-math.log2(prob) if prob > 0 else 8.0)

    return ic_values


def surprise_ratio(sequence: Sequence[int], threshold_bits: float | None = None) -> float:
    """Fraction of events that are "surprising" (IC > threshold).

    Target: 0.20 - 0.30 (the 75/25 rule).
    Huron (2006) Sweet Anticipation ch. 12.

    If threshold_bits is None, uses adaptive threshold: mean IC + 0.5 * std.
    This adapts to the piece's own statistical profile.

    Returns ratio in [0, 1].
    """
    ic = information_content(sequence, order=1)
    # Skip first event (no context)
    ic_scored = ic[1:]
    if not ic_scored:
        return 0.0

    if threshold_bits is None:
        # Adaptive threshold: events above mean + 0.5*std are "surprising"
        mean_ic = sum(ic_scored) / len(ic_scored)
        var_ic = sum((v - mean_ic) ** 2 for v in ic_scored) / len(ic_scored)
        std_ic = var_ic ** 0.5
        threshold_bits = mean_ic + 0.5 * std_ic

    surprising = sum(1 for v in ic_scored if v > threshold_bits)
    return surprising / len(ic_scored)


def expectation_score(pitch_classes: Sequence[int]) -> float:
    """Score how well a melody hits the 75/25 expectation sweet spot.

    Uses two metrics:
    1. Mean IC should be in [1.0, 2.5] bits (not too boring, not too random)
    2. IC variance should be moderate (mix of expected and surprising events)

    Returns 0-100. Combines both criteria.
    Reference: Pearce & Wiggins (2006), Temperley (2007).
    """
    ic = information_content(pitch_classes, order=1)
    ic_scored = ic[1:]  # skip first (no context)
    if len(ic_scored) < 4:
        return 50.0

    mean_ic = sum(ic_scored) / len(ic_scored)
    var_ic = sum((v - mean_ic) ** 2 for v in ic_scored) / len(ic_scored)

    # Mean IC score: target 1.0-2.5 bits (Pearce 2005: natural melodies ~1.5-2.0)
    if 1.0 <= mean_ic <= 2.5:
        mean_score = 100.0
    elif mean_ic < 1.0:
        mean_score = max(0.0, 100.0 - (1.0 - mean_ic) * 100.0)
    else:
        mean_score = max(0.0, 100.0 - (mean_ic - 2.5) * 60.0)

    # Variance score: target 0.3-2.0 (needs SOME contrast between expected/surprising)
    if 0.3 <= var_ic <= 2.0:
        var_score = 100.0
    elif var_ic < 0.3:
        var_score = max(0.0, 100.0 - (0.3 - var_ic) * 200.0)
    else:
        var_score = max(0.0, 100.0 - (var_ic - 2.0) * 50.0)

    return mean_score * 0.6 + var_score * 0.4


# =============================================================================
# 2. FRISSON / MUSICAL CHILLS (Sloboda 1991, Blood & Zatorre 2001)
# =============================================================================
#
# Dopamine release triggers (from Sloboda's empirical data):
#   - Appoggiatura (dissonant note resolving stepwise): 82% of reported chills
#   - Sudden dynamic change (pp->ff or ff->pp): 67%
#   - Unexpected harmonic shift (chromatic mediant, Neapolitan): 54%
#   - Crescendo into silence: 41%
#   - Enharmonic reinterpretation (e.g., Ab becomes G#): 38%
#   - Melodic sequence ascending then breaking pattern: 31%
#
# Physiological: 4-8 second buildup, peak at the "violation moment,"
# resolution within 2-4 seconds. Needs musical context (not effective cold).

@dataclass
class FrissonEvent:
    """A moment designed to trigger musical chills."""
    beat: float
    device: str           # e.g. "appoggiatura", "subito_piano", "chromatic_mediant"
    intensity: float      # 0.0-1.0, how strong the trigger
    setup_beats: float    # how many beats of buildup before the moment
    resolution_beats: float  # how many beats to resolve after


def plan_frisson_events(
    total_beats: float,
    climax_beat: float | None = None,
    density: float = 0.03,
) -> list[FrissonEvent]:
    """Plan frisson trigger points throughout a composition.

    Parameters
    ----------
    total_beats : Total length in beats.
    climax_beat : Where the main climax falls (default: golden ratio point).
    density : Fraction of beats that should have frisson events.
        Target: 0.02-0.05 (too many = habituation, Sloboda 1991).

    Returns list of FrissonEvent objects.
    """
    if climax_beat is None:
        climax_beat = total_beats * 0.618  # Golden ratio

    events = []
    # Main climax — strongest event
    events.append(FrissonEvent(
        beat=climax_beat,
        device="appoggiatura_with_crescendo",
        intensity=1.0,
        setup_beats=8.0,
        resolution_beats=4.0,
    ))

    # Secondary events distributed by golden angle (avoids clustering)
    golden_angle_beats = total_beats / (1 + (1 + math.sqrt(5)) / 2)
    n_secondary = max(0, int(total_beats * density) - 1)

    devices = [
        ("subito_piano", 0.6, 2.0, 2.0),
        ("chromatic_mediant", 0.7, 4.0, 4.0),
        ("deceptive_cadence", 0.5, 4.0, 4.0),
        ("enharmonic_pivot", 0.65, 6.0, 3.0),
        ("crescendo_to_silence", 0.8, 8.0, 2.0),
        ("sequence_break", 0.55, 6.0, 2.0),
    ]

    for i in range(n_secondary):
        beat = (golden_angle_beats * (i + 1)) % total_beats
        # Avoid too close to climax
        if abs(beat - climax_beat) < 8.0:
            beat = (beat + total_beats / 4) % total_beats
        dev = devices[i % len(devices)]
        # Scale intensity by proximity to climax (closer = stronger)
        proximity = 1.0 - abs(beat - climax_beat) / total_beats
        events.append(FrissonEvent(
            beat=beat, device=dev[0],
            intensity=dev[1] * (0.5 + 0.5 * proximity),
            setup_beats=dev[2], resolution_beats=dev[3],
        ))

    return sorted(events, key=lambda e: e.beat)


def appoggiatura_pitches(target_pitch: int, scale_pitches: list[int]) -> tuple[int, int]:
    """Generate appoggiatura: dissonant pitch resolving stepwise to target.

    Returns (appoggiatura_pitch, resolution_pitch).
    The appoggiatura is a non-scale tone one semitone above or below target.

    Sloboda (1991): appoggiaturas accounted for 82% of chill moments.
    """
    # Prefer approach from above (more common in classical idiom)
    app_above = target_pitch + 1
    app_below = target_pitch - 1

    # Choose whichever is NOT in the scale (true appoggiatura = non-chord tone)
    if app_above % 12 not in [p % 12 for p in scale_pitches]:
        return (app_above, target_pitch)
    elif app_below % 12 not in [p % 12 for p in scale_pitches]:
        return (app_below, target_pitch)
    else:
        return (app_above, target_pitch)  # default to above


# =============================================================================
# 3. AUDITORY SCENE ANALYSIS (Bregman 1990)
# =============================================================================
#
# The brain separates simultaneous sounds into "streams" based on:
#   - Pitch proximity: voices > ~15 semitones apart fuse poorly
#   - Voices < ~3 semitones apart MERGE (lose independence)
#   - Common onset: notes starting together group together
#   - Harmonicity: partials of same fundamental group
#   - Good continuation: smooth pitch trajectories maintain stream
#
# For voice leading:
#   - Maintain 3-15 semitone separation between adjacent voices
#   - Avoid parallel motion (especially parallel 3rds/6ths for > 3 beats)
#   - Use contrary/oblique motion to maintain stream segregation
#   - Crossing voices = stream confusion (already forbidden in counterpoint)

def voice_separation_score(
    voice_pitches: list[list[int]],
) -> float:
    """Score how well voices maintain perceptual independence.

    Bregman (1990): voices need 3-15 semitone separation for clear
    stream segregation. Optimal: 5-12 semitones between adjacent voices.

    Parameters
    ----------
    voice_pitches : List of pitch sequences, one per voice, from top to bottom.

    Returns 0-100 score.
    """
    if len(voice_pitches) < 2:
        return 100.0

    total_checks = 0
    good_checks = 0

    for v in range(len(voice_pitches) - 1):
        upper = voice_pitches[v]
        lower = voice_pitches[v + 1]
        min_len = min(len(upper), len(lower))

        for i in range(min_len):
            if upper[i] < 0 or lower[i] < 0:  # skip rests
                continue
            sep = abs(upper[i] - lower[i])
            total_checks += 1
            if 3 <= sep <= 15:
                good_checks += 1
                # Bonus for optimal range
                if 5 <= sep <= 12:
                    good_checks += 0.5
                    total_checks += 0.5

    if total_checks == 0:
        return 100.0
    return min(100.0, (good_checks / total_checks) * 100.0)


def parallel_motion_ratio(voice1: list[int], voice2: list[int]) -> float:
    """Fraction of successive intervals where both voices move in same direction.

    Target: < 0.35 (Bregman: parallel motion causes stream fusion).
    Counterpoint tradition targets < 0.30.
    """
    parallel = 0
    total = 0
    min_len = min(len(voice1), len(voice2))

    for i in range(1, min_len):
        if any(p < 0 for p in [voice1[i-1], voice1[i], voice2[i-1], voice2[i]]):
            continue
        dir1 = voice1[i] - voice1[i-1]
        dir2 = voice2[i] - voice2[i-1]
        total += 1
        if dir1 != 0 and dir2 != 0 and (dir1 > 0) == (dir2 > 0):
            parallel += 1

    return parallel / total if total > 0 else 0.0


# =============================================================================
# 4. TEMPORAL PERCEPTION & GROOVE (London 2012, Iyer 2002)
# =============================================================================
#
# Just-noticeable difference (JND) in timing: ~10-20ms (Friberg & Sundberg 1995)
# Groove = systematic micro-timing deviations from the grid.
#
# Research findings (Iyer 2002, Kilchenmann & Senn 2015):
#   - Laid-back feel: melody 10-30ms BEHIND the beat
#   - Driving feel: melody 10-20ms AHEAD of the beat
#   - Swing: offbeats delayed 20-60ms (jazz), 10-30ms (classical rubato)
#   - Bass slightly ahead of melody = "grounded" feel
#   - Human JND ~10ms; deviations < 10ms = imperceptible
#   - Deviations > 50ms = sloppy (not groove)
#
# Classical micro-timing (Repp 1998):
#   - Phrase-final ritardando: exponential deceleration
#   - Rubato: ~5-15% tempo variation within phrases
#   - Downbeat emphasis: ~5-10ms early arrival

@dataclass
class GrooveTemplate:
    """Micro-timing offsets in milliseconds for each beat position."""
    name: str
    offsets_ms: list[float]      # one per subdivision (e.g., 8 for eighth notes in 4/4)
    velocity_weights: list[float]  # multiplier for velocity at each position

    def apply_to_beat_times(
        self,
        beat_times_ms: list[float],
        subdivisions_per_beat: int = 2,
    ) -> list[float]:
        """Apply groove offsets to quantized beat times.

        Returns new times with micro-timing applied.
        """
        result = []
        n = len(self.offsets_ms)
        for i, t in enumerate(beat_times_ms):
            offset = self.offsets_ms[i % n]
            result.append(t + offset)
        return result


# Pre-built groove templates from research
GROOVE_TEMPLATES = {
    # Classical rubato feel — slight push on beats 2,4, pull on 1,3
    # Based on Repp (1998) analysis of Chopin performances
    "classical_rubato": GrooveTemplate(
        name="classical_rubato",
        offsets_ms=[0.0, -5.0, 8.0, -3.0, 5.0, -8.0, 12.0, -5.0],
        velocity_weights=[1.0, 0.85, 0.95, 0.80, 0.98, 0.82, 0.90, 0.78],
    ),
    # Baroque inégalité — paired notes with first lengthened
    # Ratio approximately 5:3 to 2:1 (Hefling 1993)
    "baroque_inegalite": GrooveTemplate(
        name="baroque_inegalite",
        offsets_ms=[0.0, 25.0, 0.0, 25.0, 0.0, 25.0, 0.0, 25.0],
        velocity_weights=[1.0, 0.75, 0.95, 0.72, 1.0, 0.75, 0.95, 0.72],
    ),
    # Viennese waltz — beat 2 early, beat 3 late
    # Bengtsson & Gabrielsson (1983)
    "viennese_waltz": GrooveTemplate(
        name="viennese_waltz",
        offsets_ms=[0.0, -20.0, 15.0, 0.0, -20.0, 15.0],
        velocity_weights=[1.0, 0.88, 0.85, 0.98, 0.88, 0.85],
    ),
    # Subtle humanization — within JND range for "perfect but not robotic"
    "subtle_human": GrooveTemplate(
        name="subtle_human",
        offsets_ms=[0.0, 3.0, -2.0, 5.0, -3.0, 4.0, -1.0, 2.0],
        velocity_weights=[1.0, 0.92, 0.97, 0.90, 0.99, 0.91, 0.96, 0.89],
    ),
}


def phrase_ritardando(
    beat_durations_ms: list[float],
    phrase_length: int,
    rit_fraction: float = 0.15,
    rit_amount: float = 0.25,
) -> list[float]:
    """Apply phrase-final ritardando using exponential curve.

    Repp (1992): pianists decelerate at phrase endings following
    an approximately quadratic curve: t(x) = t0 * (1 + a*x^2)
    where x goes from 0 to 1 over the ritardando portion.

    Parameters
    ----------
    beat_durations_ms : Original durations.
    phrase_length : Notes per phrase.
    rit_fraction : Last fraction of phrase to slow down (0.10-0.20).
    rit_amount : Maximum slowdown fraction (0.15-0.35 typical).
    """
    result = list(beat_durations_ms)
    for phrase_start in range(0, len(result), phrase_length):
        phrase_end = min(phrase_start + phrase_length, len(result))
        rit_start = phrase_end - max(1, int(phrase_length * rit_fraction))
        rit_len = phrase_end - rit_start

        for i in range(rit_start, phrase_end):
            x = (i - rit_start + 1) / rit_len  # 0 to 1
            slowdown = 1.0 + rit_amount * (x ** 2)
            result[i] *= slowdown

    return result


# =============================================================================
# 5. CONSONANCE MODELS (Plomp & Levelt 1965, Sethares 2005, Parncutt 1989)
# =============================================================================
#
# Simple ratio consonance (Pythagoras) is incomplete. Perceptual consonance
# depends on the critical bandwidth of the basilar membrane.
#
# Plomp & Levelt (1965): maximum roughness at ~25% of critical bandwidth.
# Critical bandwidth ≈ 1.72 * f^0.65 Hz (Greenwood 1961).
#
# Sethares (2005): total dissonance = sum of roughness between all partial pairs.
# For standard harmonic timbres, this reproduces the usual consonance ranking.
# For inharmonic timbres (bells, metallophones), different tunings become consonant.

def critical_bandwidth(freq_hz: float) -> float:
    """Critical bandwidth in Hz at a given frequency.

    Greenwood (1961) / Glasberg & Moore (1990) ERB formula:
    ERB(f) = 24.7 * (4.37 * f/1000 + 1)
    """
    return 24.7 * (4.37 * freq_hz / 1000.0 + 1.0)


def plomp_levelt_roughness(f1: float, f2: float) -> float:
    """Roughness/dissonance between two pure tones.

    Plomp & Levelt (1965): dissonance follows a bell curve peaking at
    ~25% of the critical bandwidth, returning to zero at ~100% CB.

    d(f1,f2) = exp(-3.5*s) - exp(-5.75*s)  where s = |f1-f2| / CB
    (Sethares approximation)

    Returns value in [0, 1] where 1 = maximum roughness.
    """
    if f1 <= 0 or f2 <= 0:
        return 0.0
    f_min, f_max = min(f1, f2), max(f1, f2)
    s = (f_max - f_min) / critical_bandwidth(f_min)
    if s > 1.2:
        return 0.0  # beyond critical band
    d = math.exp(-3.5 * s) - math.exp(-5.75 * s)
    return max(0.0, d)


def midi_to_freq(midi_note: int) -> float:
    """MIDI note number to frequency in Hz. A4 = 69 = 440 Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def sethares_dissonance(
    midi_notes: list[int],
    n_partials: int = 6,
    rolloff: float = 0.88,
) -> float:
    """Total sensory dissonance for a set of MIDI notes with harmonic timbres.

    Sethares (2005) ch. 3: sum roughness between all pairs of partials
    across all notes. Amplitude-weighted.

    Parameters
    ----------
    midi_notes : MIDI note numbers sounding simultaneously.
    n_partials : Number of harmonic partials per note (6-8 typical).
    rolloff : Amplitude decay per partial (0.88 = natural harmonic series).

    Returns total dissonance (lower = more consonant). Scale depends on
    number of notes/partials. Compare relatively, not absolutely.
    """
    # Build list of (frequency, amplitude) for all partials
    partials = []
    for note in midi_notes:
        f0 = midi_to_freq(note)
        for h in range(1, n_partials + 1):
            amp = rolloff ** (h - 1)
            partials.append((f0 * h, amp))

    # Sum pairwise roughness
    total = 0.0
    for i in range(len(partials)):
        for j in range(i + 1, len(partials)):
            f1, a1 = partials[i]
            f2, a2 = partials[j]
            roughness = plomp_levelt_roughness(f1, f2)
            total += roughness * a1 * a2  # amplitude weighting

    return total


def consonance_ranking(midi_notes: list[int], reference: int = 60) -> list[tuple[int, float]]:
    """Rank intervals from a reference note by perceptual consonance.

    Useful for choosing which notes to use in a chord voicing.
    Returns list of (midi_note, dissonance) sorted low to high dissonance.
    """
    results = []
    for note in midi_notes:
        d = sethares_dissonance([reference, note])
        results.append((note, d))
    return sorted(results, key=lambda x: x[1])


# =============================================================================
# 6. PEAK-END RULE (Kahneman 2000, applied to music)
# =============================================================================
#
# Kahneman's research: remembered experience = average of peak intensity
# and end intensity, NOT the integral of the whole experience.
#
# Musical implications:
#   - The single most intense moment matters more than sustained quality
#   - The ending is disproportionately remembered
#   - A mediocre middle with great climax + satisfying ending > uniformly good
#
# Compositional strategies:
#   - Climax at golden ratio point (0.618) with HIGHEST tension ever in piece
#   - Last 10-15% should resolve fully, ending on tonic with clear cadence
#   - Peak should be multidimensional: highest pitch + loudest + densest texture
#   - Ending should be 1-2 dynamic levels quieter than climax (contrast)

def peak_end_score(
    tension_curve: list[float],
    peak_target: float = 0.618,
    end_fraction: float = 0.12,
) -> float:
    """Score a tension curve for peak-end rule compliance.

    Parameters
    ----------
    tension_curve : List of tension values (0-1) at regular intervals.
    peak_target : Where the peak should fall (fraction of total length).
        Default 0.618 (golden ratio). Kahneman: peak must be memorable.
    end_fraction : Last fraction to evaluate as "ending."

    Returns 0-100 score.
    """
    if not tension_curve:
        return 0.0

    n = len(tension_curve)
    peak_idx = int(max(range(n), key=lambda i: tension_curve[i]))
    peak_pos = peak_idx / n

    # Score 1: Is peak near golden ratio? (40 points)
    peak_deviation = abs(peak_pos - peak_target)
    peak_score = max(0, 40.0 * (1.0 - peak_deviation / 0.3))

    # Score 2: Is peak truly outstanding? (30 points)
    peak_val = tension_curve[peak_idx]
    mean_val = sum(tension_curve) / n
    if mean_val > 0:
        peak_prominence = peak_val / mean_val
        prominence_score = min(30.0, 30.0 * min(1.0, (peak_prominence - 1.0) / 1.0))
    else:
        prominence_score = 0.0

    # Score 3: Does ending resolve? (30 points)
    end_start = max(0, n - int(n * end_fraction))
    end_values = tension_curve[end_start:]
    if end_values:
        end_mean = sum(end_values) / len(end_values)
        # Ending should be lower than peak, ideally 20-40% of peak
        if peak_val > 0:
            end_ratio = end_mean / peak_val
            # Best: 0.15-0.35 (resolved but not zero = satisfying)
            if 0.15 <= end_ratio <= 0.35:
                end_score = 30.0
            else:
                end_score = max(0, 30.0 * (1.0 - abs(end_ratio - 0.25) / 0.4))
        else:
            end_score = 15.0
        # Bonus: final value should decrease (not increase)
        if len(end_values) >= 2 and end_values[-1] <= end_values[0]:
            end_score = min(30.0, end_score + 5.0)
    else:
        end_score = 0.0

    return peak_score + prominence_score + end_score


# =============================================================================
# 7. EARWORM ENGINEERING (Jakubowski et al. 2017)
# =============================================================================
#
# Features of involuntary musical imagery ("earworms"):
#   1. Arch-shaped pitch contour (rise then fall): 73% of earworms
#   2. Narrow pitch range (< 10 semitones): easier to sing internally
#   3. Unexpected intervals after predictable ones: 68%
#   4. Rhythmic repetition with variation: 81%
#   5. Simple metric structure (4/4 strongly preferred): 89%
#   6. Tempo 100-130 BPM: matches internal motor rhythms (Moelants 2002)
#   7. Length 4-8 bars: fits working memory (Miller's 7±2)
#
# Additional (Müllensiefen et al. 2014):
#   - Long initial note or rest: creates anticipation
#   - Interval pattern: mostly steps (2nds) with one or two leaps (4th/5th)
#   - Phrase ends on tonic or dominant

def earworm_score(pitches: list[int], durations: list[float]) -> float:
    """Score a melody for "stickiness" — earworm potential.

    Based on Jakubowski et al. (2017) and Müllensiefen et al. (2014).
    Returns 0-100.
    """
    if len(pitches) < 4:
        return 0.0

    score = 0.0

    # 1. Arch-shaped contour (20 points)
    n = len(pitches)
    mid = n // 2
    first_half_trend = sum(pitches[i+1] - pitches[i] for i in range(mid) if i+1 < n)
    second_half_trend = sum(pitches[i+1] - pitches[i] for i in range(mid, n-1))
    if first_half_trend > 0 and second_half_trend < 0:
        score += 20.0
    elif first_half_trend > 0 or second_half_trend < 0:
        score += 10.0

    # 2. Narrow pitch range (15 points)
    pitch_range = max(pitches) - min(pitches)
    if pitch_range <= 10:
        score += 15.0
    elif pitch_range <= 14:
        score += 10.0
    elif pitch_range <= 17:
        score += 5.0

    # 3. Mostly steps with occasional leaps (20 points)
    intervals = [abs(pitches[i+1] - pitches[i]) for i in range(n-1)]
    if intervals:
        steps = sum(1 for iv in intervals if iv <= 2)
        step_ratio = steps / len(intervals)
        leaps = sum(1 for iv in intervals if 5 <= iv <= 7)
        # Target: 70-85% steps, 1-2 leaps of 4th/5th
        if 0.65 <= step_ratio <= 0.90 and 1 <= leaps <= 3:
            score += 20.0
        elif 0.55 <= step_ratio:
            score += 10.0

    # 4. Rhythmic repetition with variation (20 points)
    if durations:
        dur_patterns = [tuple(durations[i:i+4]) for i in range(0, len(durations)-3)]
        if dur_patterns:
            pattern_counts = Counter(dur_patterns)
            repeated = sum(1 for c in pattern_counts.values() if c > 1)
            repeat_ratio = repeated / len(pattern_counts) if pattern_counts else 0
            # Want some repetition (0.2-0.5) but not too much
            if 0.15 <= repeat_ratio <= 0.55:
                score += 20.0
            elif repeat_ratio > 0:
                score += 10.0

    # 5. Singable range — fits within an octave + minor 3rd (10 points)
    if pitch_range <= 15:  # octave + m3
        score += 10.0

    # 6. Ends on strong scale degree (15 points)
    # Check if last pitch is tonic or dominant (relative to lowest pitch)
    last_pc = pitches[-1] % 12
    root_candidates = [pitches[0] % 12, min(pitches) % 12]
    for root in root_candidates:
        interval_from_root = (last_pc - root) % 12
        if interval_from_root == 0:  # tonic
            score += 15.0
            break
        elif interval_from_root == 7:  # dominant
            score += 10.0
            break

    return min(100.0, score)


# =============================================================================
# COMBINED PERCEPTUAL OPTIMIZER
# =============================================================================

@dataclass
class PerceptualReport:
    """Complete psychoacoustic analysis of a musical passage."""
    expectation_balance: float    # 0-100, how well it hits 75/25
    surprise_ratio: float         # actual ratio of surprising events
    frisson_potential: int        # number of frisson trigger points
    voice_separation: float       # 0-100, Bregman stream segregation
    peak_end_quality: float       # 0-100, Kahneman peak-end rule
    earworm_potential: float      # 0-100, melody stickiness
    total_score: float            # weighted combination 0-100

    def summary(self) -> str:
        lines = [
            f"Perceptual Analysis Report",
            f"  Expectation balance: {self.expectation_balance:.1f}/100 (surprise ratio: {self.surprise_ratio:.2f})",
            f"  Frisson triggers:    {self.frisson_potential} planned events",
            f"  Voice separation:    {self.voice_separation:.1f}/100 (Bregman ASA)",
            f"  Peak-end quality:    {self.peak_end_quality:.1f}/100 (Kahneman)",
            f"  Earworm potential:   {self.earworm_potential:.1f}/100 (Jakubowski)",
            f"  TOTAL PERCEPTUAL:    {self.total_score:.1f}/100",
        ]
        return "\n".join(lines)


def analyze_perceptual(
    melody_pitches: list[int],
    melody_durations: list[float],
    all_voice_pitches: list[list[int]] | None = None,
    tension_curve: list[float] | None = None,
    total_beats: float = 192.0,
) -> PerceptualReport:
    """Run full psychoacoustic analysis on a composition.

    Parameters
    ----------
    melody_pitches : Main melody MIDI pitches.
    melody_durations : Melody durations in beats.
    all_voice_pitches : All voices for separation analysis.
    tension_curve : Pre-computed tension values (0-1) over time.
    total_beats : Total length for frisson planning.
    """
    # 1. Expectation
    pcs = [p % 12 for p in melody_pitches if p >= 0]
    exp_score = expectation_score(pcs)
    s_ratio = surprise_ratio(pcs)

    # 2. Frisson
    frisson_events = plan_frisson_events(total_beats)

    # 3. Voice separation
    if all_voice_pitches and len(all_voice_pitches) >= 2:
        sep_score = voice_separation_score(all_voice_pitches)
    else:
        sep_score = 80.0  # default for single voice

    # 4. Peak-end
    if tension_curve:
        pe_score = peak_end_score(tension_curve)
    else:
        pe_score = 60.0  # neutral

    # 5. Earworm
    ew_score = earworm_score(melody_pitches, melody_durations)

    # Weighted total
    total = (
        exp_score * 0.25 +
        sep_score * 0.20 +
        pe_score * 0.25 +
        ew_score * 0.15 +
        min(100.0, len(frisson_events) * 15.0) * 0.15
    )

    return PerceptualReport(
        expectation_balance=exp_score,
        surprise_ratio=s_ratio,
        frisson_potential=len(frisson_events),
        voice_separation=sep_score,
        peak_end_quality=pe_score,
        earworm_potential=ew_score,
        total_score=total,
    )
