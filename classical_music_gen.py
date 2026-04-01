"""
Classical Music Generation Toolkit
===================================
Practical, production-ready Python patterns for algorithmic classical music
composition. Uses music21 for theory and midiutil for MIDI output.

Install dependencies:
    pip install music21 midiutil numpy

Run this file directly to generate a complete 32-bar piano piece as MIDI.
"""

# pip install music21 midiutil numpy
import random
import math
import numpy as np
from copy import deepcopy
from collections import defaultdict
from typing import List, Tuple, Optional, Dict

from music21 import (
    stream, note, chord as m21chord, key, pitch, interval,
    meter, tempo, instrument, roman, scale
)
from midiutil import MIDIFile


# =============================================================================
# 1. CHORD PROGRESSION GENERATOR — Context-Free Grammar
# =============================================================================

class ChordGrammar:
    """
    Generates chord progressions using a probabilistic context-free grammar.
    Grammar rules model common tonal syntax:
        Phrase   -> Tonic Predom Dominant Tonic
        Tonic    -> I | vi | I6
        Predom   -> IV | ii | ii6
        Dominant -> V | V7 | viio
    Each rule has an associated probability weight.
    """

    RULES = {
        "Phrase": [
            (["Tonic", "Predom", "Dominant", "Tonic"], 0.4),
            (["Tonic", "Dominant", "Tonic"], 0.2),
            (["Tonic", "Predom", "Dominant", "Deceptive"], 0.15),
            (["Tonic", "Predom", "Predom", "Dominant", "Tonic"], 0.15),
            (["Tonic", "Dominant", "Deceptive", "Predom", "Dominant", "Tonic"], 0.1),
        ],
        "Tonic": [
            (["I"], 0.6),
            (["vi"], 0.2),
            (["I6"], 0.2),
        ],
        "Predom": [
            (["IV"], 0.35),
            (["ii"], 0.35),
            (["ii6"], 0.15),
            (["vi"], 0.15),
        ],
        "Dominant": [
            (["V"], 0.35),
            (["V7"], 0.40),
            (["viio"], 0.15),
            (["V/V", "V"], 0.10),   # secondary dominant chain
        ],
        "Deceptive": [
            (["vi"], 0.7),
            (["IV6"], 0.3),
        ],
    }

    def __init__(self, key_str: str = "C"):
        self.key_obj = key.Key(key_str)

    def derive(self, symbol: str = "Phrase") -> List[str]:
        """Recursively expand grammar symbols into terminal Roman numerals."""
        if symbol not in self.RULES:
            return [symbol]  # terminal symbol (a Roman numeral)
        expansions, weights = zip(*self.RULES[symbol])
        chosen = random.choices(expansions, weights=weights, k=1)[0]
        result = []
        for s in chosen:
            result.extend(self.derive(s))
        return result

    def generate_progression(self, num_phrases: int = 2) -> List[str]:
        """Generate a multi-phrase progression."""
        prog = []
        for _ in range(num_phrases):
            prog.extend(self.derive("Phrase"))
        return prog

    def realize(self, numerals: List[str]) -> List[m21chord.Chord]:
        """Convert Roman numeral strings to music21 Chord objects in the key."""
        chords = []
        for rn_str in numerals:
            rn = roman.RomanNumeral(rn_str, self.key_obj)
            chords.append(rn)
        return chords


# =============================================================================
# 2. VOICE LEADING ENGINE
# =============================================================================

class VoiceLeader:
    """
    Finds optimal voice leading between two chords.
    - Minimizes total pitch distance across all voices.
    - Penalizes parallel 5ths and octaves.
    - Ensures leading tone resolves up and 7ths resolve down.
    """

    @staticmethod
    def all_voicings(chord_pitches: List[int], num_voices: int = 4,
                     low: int = 48, high: int = 79) -> List[Tuple[int, ...]]:
        """
        Generate all possible voicings of a chord within a range.
        chord_pitches: list of pitch classes (0-11).
        Returns list of tuples of MIDI note numbers, sorted low to high.
        """
        # For each pitch class, find all octave placements in range
        candidates_per_pc = {}
        for pc in chord_pitches:
            candidates_per_pc[pc] = []
            for midi_note in range(low, high + 1):
                if midi_note % 12 == pc:
                    candidates_per_pc[pc].append(midi_note)

        # Build voicings: assign each voice to one pitch class (with doubling)
        from itertools import product
        pcs = chord_pitches
        if len(pcs) < num_voices:
            # Double the root
            pcs = pcs + [pcs[0]] * (num_voices - len(pcs))

        all_options = [candidates_per_pc[pc] for pc in pcs[:num_voices]]
        voicings = []
        for combo in product(*all_options):
            s = tuple(sorted(combo))
            if len(set(s)) == num_voices and s not in voicings:
                voicings.append(s)
        # Limit to prevent combinatorial explosion
        if len(voicings) > 500:
            voicings = random.sample(voicings, 500)
        return voicings

    @staticmethod
    def has_parallel_fifths_or_octaves(v1: Tuple[int, ...],
                                       v2: Tuple[int, ...]) -> bool:
        """Check if moving from voicing v1 to v2 creates parallel 5ths/8ves."""
        for i in range(len(v1)):
            for j in range(i + 1, len(v1)):
                interval_before = (v1[j] - v1[i]) % 12
                interval_after = (v2[j] - v2[i]) % 12
                # Both are perfect 5th (7 semitones) or unison/octave (0)
                if interval_before in (0, 7) and interval_before == interval_after:
                    # Check that both voices actually moved (parallel, not stationary)
                    if v1[i] != v2[i] and v1[j] != v2[j]:
                        return True
        return False

    @staticmethod
    def total_movement(v1: Tuple[int, ...], v2: Tuple[int, ...]) -> int:
        return sum(abs(a - b) for a, b in zip(v1, v2))

    def find_optimal(self, current_voicing: Tuple[int, ...],
                     next_chord_pcs: List[int],
                     key_obj: key.Key = None) -> Tuple[int, ...]:
        """
        Given a current voicing and the pitch classes of the next chord,
        find the smoothest voice leading without parallels.
        """
        candidates = self.all_voicings(next_chord_pcs, num_voices=len(current_voicing))
        best = None
        best_cost = float("inf")

        leading_tone_pc = key_obj.getScale().pitchFromDegree(7).pitchClass if key_obj else None

        for cand in candidates:
            cost = self.total_movement(current_voicing, cand)

            # Heavy penalty for parallel 5ths/octaves
            if self.has_parallel_fifths_or_octaves(current_voicing, cand):
                cost += 1000

            # Reward common tones held in place
            for i in range(len(current_voicing)):
                if current_voicing[i] == cand[i]:
                    cost -= 1

            # Penalize leading tone not resolving up by step
            if leading_tone_pc is not None:
                for i in range(len(current_voicing)):
                    if current_voicing[i] % 12 == leading_tone_pc:
                        # Should resolve up by 1 semitone
                        if cand[i] != current_voicing[i] + 1:
                            cost += 20

            # Penalize chord 7ths not resolving down by step
            for i in range(len(current_voicing)):
                # If this note is a 7th above the bass of current chord
                bass = min(current_voicing)
                if (current_voicing[i] - bass) % 12 in (10, 11):
                    if cand[i] > current_voicing[i]:
                        cost += 15

            if cost < best_cost:
                best_cost = cost
                best = cand

        return best if best else candidates[0]


# =============================================================================
# 3. MELODY GENERATOR WITH CONTOUR CONTROL
# =============================================================================

class MelodyGenerator:
    """
    Generates melodies that follow a target contour curve while respecting:
    - Scale membership
    - Zipfian interval distribution (mostly steps, some thirds, rare leaps)
    """

    # Zipfian interval weights: index = interval in scale degrees (0=unison, 1=step, etc.)
    INTERVAL_WEIGHTS = {
        0: 0.05,   # unison (repeat)
        1: 0.55,   # step (2nd)
        2: 0.25,   # third
        3: 0.08,   # fourth
        4: 0.04,   # fifth
        5: 0.02,   # sixth
        6: 0.01,   # seventh
    }

    def __init__(self, key_str: str = "C", octave_low: int = 4, octave_high: int = 5):
        self.key_obj = key.Key(key_str)
        sc = self.key_obj.getScale()
        # Build pool of available scale pitches across octave range
        self.pitch_pool = []
        for p in sc.getPitches(f"{sc.tonic.name}{octave_low}",
                               f"{sc.tonic.name}{octave_high + 1}"):
            self.pitch_pool.append(p)
        self.pitch_pool.sort(key=lambda p: p.midi)

    def generate(self, contour: List[float], length: int = None) -> List[pitch.Pitch]:
        """
        Generate a melody following a contour (list of values 0.0-1.0).
        Length defaults to len(contour).
        """
        if length is None:
            length = len(contour)
        # Resample contour to desired length
        contour_resampled = np.interp(
            np.linspace(0, 1, length),
            np.linspace(0, 1, len(contour)),
            contour
        )

        pool = self.pitch_pool
        min_midi = pool[0].midi
        max_midi = pool[-1].midi
        midi_range = max_midi - min_midi

        def closest_scale_pitch(target_midi):
            return min(pool, key=lambda p: abs(p.midi - target_midi))

        # Map contour to target MIDI values
        targets = [min_midi + c * midi_range for c in contour_resampled]

        melody = [closest_scale_pitch(targets[0])]

        for i in range(1, length):
            target = targets[i]
            current = melody[-1]

            # Choose interval size from Zipfian distribution
            intervals = list(self.INTERVAL_WEIGHTS.keys())
            weights = list(self.INTERVAL_WEIGHTS.values())
            chosen_interval = random.choices(intervals, weights=weights, k=1)[0]

            # Determine direction from contour
            direction = 1 if target > current.midi else -1
            if abs(target - current.midi) < 1:
                direction = random.choice([-1, 1])

            # Find candidate: move by chosen_interval scale steps in direction
            current_idx = pool.index(current) if current in pool else \
                min(range(len(pool)), key=lambda j: abs(pool[j].midi - current.midi))
            new_idx = current_idx + direction * chosen_interval
            new_idx = max(0, min(len(pool) - 1, new_idx))

            candidate = pool[new_idx]
            # Blend: if candidate strays too far from contour target, pull it back
            if abs(candidate.midi - target) > 7:
                candidate = closest_scale_pitch(target)

            melody.append(candidate)

        return melody


# =============================================================================
# 4. SPECIES COUNTERPOINT SOLVER
# =============================================================================

class CounterpointSolver:
    """
    Given a cantus firmus, generate a valid first-species counterpoint
    (note-against-note, above the cantus) using backtracking with penalties.
    """

    CONSONANCES = {0, 3, 4, 7, 8, 9, 12}  # unison, m3, M3, P5, m6, M6, P8

    def __init__(self, key_str: str = "C"):
        self.key_obj = key.Key(key_str)
        sc = self.key_obj.getScale()
        self.scale_pitches = []
        for p in sc.getPitches("C4", "C6"):
            self.scale_pitches.append(p)

    def score_note(self, cp_note: pitch.Pitch, cf_note: pitch.Pitch,
                   prev_cp: Optional[pitch.Pitch], prev_cf: Optional[pitch.Pitch],
                   is_first: bool, is_last: bool) -> float:
        """Penalty-based scoring. Lower is better. Returns inf if forbidden."""
        ivl = abs(cp_note.midi - cf_note.midi) % 12
        penalty = 0.0

        # Must be consonant
        if abs(cp_note.midi - cf_note.midi) % 12 not in {0, 3, 4, 7, 8, 9}:
            return float("inf")

        # First and last must be perfect consonance (unison, 5th, or octave)
        if is_first or is_last:
            if ivl not in {0, 7}:
                penalty += 50

        # Prefer contrary/oblique motion
        if prev_cp and prev_cf:
            cp_motion = cp_note.midi - prev_cp.midi
            cf_motion = cf_note.midi - prev_cf.midi
            # Parallel motion to perfect consonance: forbidden
            if cp_motion * cf_motion > 0 and ivl in {0, 7}:
                return float("inf")
            # Similar motion: mild penalty
            if cp_motion * cf_motion > 0:
                penalty += 5
            # Contrary motion: reward
            if cp_motion * cf_motion < 0:
                penalty -= 3

        # Penalize large leaps
        if prev_cp:
            leap = abs(cp_note.midi - prev_cp.midi)
            if leap > 7:
                penalty += 20
            elif leap > 4:
                penalty += 5
            # Penalize repeated notes
            if leap == 0:
                penalty += 10

        # Variety: slight random jitter to avoid deterministic output
        penalty += random.uniform(0, 2)

        return penalty

    def solve(self, cantus_firmus: List[pitch.Pitch]) -> Optional[List[pitch.Pitch]]:
        """Backtracking search for a valid counterpoint line."""
        n = len(cantus_firmus)
        solution = [None] * n
        pool = self.scale_pitches

        def backtrack(idx):
            if idx == n:
                return True
            # Score all candidates and try in order of ascending penalty
            candidates = []
            for p in pool:
                if p.midi <= cantus_firmus[idx].midi:
                    continue  # counterpoint above cantus
                sc = self.score_note(
                    p, cantus_firmus[idx],
                    solution[idx - 1] if idx > 0 else None,
                    cantus_firmus[idx - 1] if idx > 0 else None,
                    is_first=(idx == 0),
                    is_last=(idx == n - 1)
                )
                if sc < float("inf"):
                    candidates.append((sc, p))
            candidates.sort(key=lambda x: x[0])
            for _, p in candidates[:8]:  # try top 8 to limit branching
                solution[idx] = p
                if backtrack(idx + 1):
                    return True
            solution[idx] = None
            return False

        if backtrack(0):
            return solution
        return None


# =============================================================================
# 5. PHRASE STRUCTURE GENERATOR (Antecedent-Consequent)
# =============================================================================

class PhraseStructure:
    """
    Generates antecedent-consequent period structure:
    - Antecedent: starts on tonic, ends on half cadence (V)
    - Consequent: starts the same, diverges to end on authentic cadence (I)
    """

    def __init__(self, key_str: str = "C"):
        self.grammar = ChordGrammar(key_str)
        self.melody_gen = MelodyGenerator(key_str)
        self.key_str = key_str

    def generate_period(self, measures: int = 8) -> dict:
        """Generate an antecedent-consequent period."""
        half = measures // 2

        # Antecedent: I ... -> V (half cadence)
        ante_prog = self.grammar.derive("Phrase")
        # Force last chord to be V for half cadence
        ante_prog[-1] = "V"
        # Pad or trim to fill half the measures
        while len(ante_prog) < half:
            ante_prog.insert(-1, random.choice(["IV", "ii", "I"]))
        ante_prog = ante_prog[:half]

        # Consequent: starts same as antecedent but ends I (authentic cadence)
        cons_prog = ante_prog[:half // 2]  # same opening
        # Fill the rest with new material ending on V -> I
        remaining = half - len(cons_prog)
        filler = self.grammar.derive("Phrase")
        while len(filler) < remaining:
            filler.insert(-1, random.choice(["IV", "ii"]))
        filler = filler[:remaining]
        filler[-2] = "V7"  # penultimate = dominant
        filler[-1] = "I"   # final = tonic (PAC)
        cons_prog.extend(filler)

        # Generate melodies: consequent starts like antecedent
        # Arch contour for antecedent
        ante_contour = [math.sin(math.pi * x / (half - 1)) for x in range(half)]
        ante_melody = self.melody_gen.generate(ante_contour, half * 4)

        # Consequent contour: same start, different peak
        cons_contour = [math.sin(math.pi * x / (half - 1)) * 0.8 for x in range(half)]
        cons_contour[-1] = 0.0  # end low on tonic
        cons_melody_tail = self.melody_gen.generate(cons_contour[half // 2:],
                                                     (half - half // 2) * 4)
        cons_melody = ante_melody[:half // 2 * 4] + cons_melody_tail

        return {
            "antecedent_chords": ante_prog,
            "consequent_chords": cons_prog,
            "antecedent_melody": ante_melody,
            "consequent_melody": cons_melody,
        }


# =============================================================================
# 6. ALBERTI BASS PATTERN GENERATOR
# =============================================================================

class AlbertiBass:
    """
    Generates Alberti bass accompaniment patterns from chord symbols.
    Patterns:
        standard:  root - 5th - 3rd - 5th  (C-G-E-G)
        waltz:     root - 3rd+5th - 3rd+5th (bass note then chord)
        murky:     root - octave - root - octave
        tremolo:   root+3rd - 5th - root+3rd - 5th
    """

    PATTERNS = {
        "standard": [0, 2, 1, 2],    # indices into chord tones [root, 3rd, 5th]
        "murky":    [0, "8va", 0, "8va"],
        "tremolo":  [(0, 1), 2, (0, 1), 2],
    }

    def __init__(self, key_str: str = "C"):
        self.key_obj = key.Key(key_str)

    def generate(self, numerals: List[str], beats_per_chord: int = 4,
                 pattern_type: str = "standard",
                 octave: int = 3) -> List[List[int]]:
        """
        Returns list of (midi_notes, duration_in_eighths) for each eighth note.
        Each entry is a list of MIDI note numbers (usually 1, but can be >1 for tremolo).
        """
        pattern_def = self.PATTERNS.get(pattern_type, self.PATTERNS["standard"])
        result = []

        for rn_str in numerals:
            rn = roman.RomanNumeral(rn_str, self.key_obj)
            # Get chord tones in the bass octave
            tones = []
            for p in rn.pitches:
                new_p = pitch.Pitch(p.name + str(octave))
                tones.append(new_p.midi)

            # Ensure we have at least 3 tones (root, 3rd, 5th)
            while len(tones) < 3:
                tones.append(tones[0] + 12)

            for beat in range(beats_per_chord):
                pat_step = pattern_def[beat % len(pattern_def)]
                if pat_step == "8va":
                    result.append([tones[0] + 12])
                elif isinstance(pat_step, tuple):
                    result.append([tones[i] for i in pat_step])
                else:
                    result.append([tones[pat_step]])

        return result


# =============================================================================
# 7. ORCHESTRATION MAPPER
# =============================================================================

class OrchestrationMapper:
    """
    Maps SATB voicings to orchestral instruments respecting standard ranges.
    Outputs multi-track MIDI via midiutil.
    """

    # (name, MIDI program number, low MIDI, high MIDI)
    INSTRUMENT_RANGES = {
        "flute":    (73, 60, 96),   # C4 - C7
        "oboe":     (68, 58, 91),   # Bb3 - G6
        "clarinet": (71, 50, 89),   # D3 - F6
        "bassoon":  (70, 34, 72),   # Bb1 - C5
        "horn":     (60, 34, 77),   # Bb1 - F5
        "trumpet":  (56, 55, 82),   # G3 - Bb5
        "violin1":  (40, 55, 100),  # G3 - E7
        "violin2":  (40, 55, 93),   # G3 - A6
        "viola":    (41, 48, 88),   # C3 - E6
        "cello":    (42, 36, 76),   # C2 - E5
        "bass":     (43, 28, 60),   # E1 - C4
    }

    # Default SATB -> orchestral mapping templates
    TEMPLATES = {
        "strings": {
            "S": ["violin1"],
            "A": ["violin2"],
            "T": ["viola"],
            "B": ["cello", "bass"],
        },
        "woodwinds": {
            "S": ["flute", "oboe"],
            "A": ["clarinet"],
            "T": ["clarinet"],
            "B": ["bassoon"],
        },
        "full": {
            "S": ["violin1", "flute"],
            "A": ["violin2", "oboe"],
            "T": ["viola", "clarinet"],
            "B": ["cello", "bass", "bassoon"],
        },
    }

    def assign(self, satb_voicings: List[Tuple[int, int, int, int]],
               template: str = "strings") -> Dict[str, List[List[int]]]:
        """
        Map SATB voicings to instruments.
        Returns dict: instrument_name -> list of notes per beat.
        """
        tmpl = self.TEMPLATES[template]
        tracks = defaultdict(list)
        voice_labels = ["S", "A", "T", "B"]

        for voicing in satb_voicings:
            for i, label in enumerate(voice_labels):
                midi_note = voicing[i] if i < len(voicing) else voicing[-1]
                for inst_name in tmpl[label]:
                    _, low, high = self.INSTRUMENT_RANGES[inst_name]
                    # Transpose into range if needed
                    n = midi_note
                    while n < low:
                        n += 12
                    while n > high:
                        n -= 12
                    tracks[inst_name].append(n)

        return dict(tracks)

    def to_midi(self, tracks: Dict[str, List[int]], filename: str,
                bpm: int = 100, note_dur: float = 1.0):
        """Write orchestration to a multi-track MIDI file."""
        num_tracks = len(tracks)
        midi = MIDIFile(num_tracks)
        for track_idx, (inst_name, notes) in enumerate(tracks.items()):
            program, _, _ = self.INSTRUMENT_RANGES[inst_name]
            midi.addTrackName(track_idx, 0, inst_name)
            midi.addTempo(track_idx, 0, bpm)
            midi.addProgramChange(track_idx, track_idx, 0, program)
            for beat_idx, n in enumerate(notes):
                midi.addNote(track_idx, track_idx, n, beat_idx * note_dur,
                             note_dur, volume=80)
        with open(filename, "wb") as f:
            midi.writeFile(f)


# =============================================================================
# 8. FORM TEMPLATE ENGINE
# =============================================================================

class FormEngine:
    """
    Generates formal structures:
    - ABA ternary form with key relationships
    - Theme and variations (ornamental, rhythmic, mode change)
    """

    def __init__(self, key_str: str = "C"):
        self.key_str = key_str
        self.key_obj = key.Key(key_str)

    def ternary_keys(self) -> dict:
        """Return key relationships for ABA form."""
        # B section typically in dominant or relative minor/major
        mode = self.key_obj.mode
        if mode == "major":
            b_key = self.key_obj.getDominant().name + " major"
        else:
            b_key = self.key_obj.getRelativeMajor().tonic.name + " major"
        return {
            "A": self.key_str,
            "B": b_key,
            "A_reprise": self.key_str,
        }

    def theme_and_variations(self, theme_melody: List[pitch.Pitch],
                              theme_durations: List[float]) -> dict:
        """
        Generate 3 variations of a theme.
        Var 1: Ornamental (add passing tones between each note)
        Var 2: Rhythmic (halve/double durations in alternation)
        Var 3: Mode change (major <-> minor)
        """
        # Variation 1: Ornamental — insert passing tones
        var1_melody = []
        var1_dur = []
        sc = self.key_obj.getScale()
        all_pitches = list(sc.getPitches("C3", "C7"))
        for i, p in enumerate(theme_melody):
            var1_melody.append(p)
            var1_dur.append(theme_durations[i] / 2)
            if i < len(theme_melody) - 1:
                # Insert a passing tone between current and next
                mid_midi = (p.midi + theme_melody[i + 1].midi) // 2
                passing = min(all_pitches, key=lambda x: abs(x.midi - mid_midi))
                var1_melody.append(passing)
                var1_dur.append(theme_durations[i] / 2)

        # Variation 2: Rhythmic — dotted rhythm (long-short alternation)
        var2_melody = list(theme_melody)
        var2_dur = []
        for i, d in enumerate(theme_durations):
            if i % 2 == 0:
                var2_dur.append(d * 1.5)
            else:
                var2_dur.append(d * 0.5)

        # Variation 3: Mode change
        if self.key_obj.mode == "major":
            new_key = key.Key(self.key_obj.tonic.name, "minor")
        else:
            new_key = key.Key(self.key_obj.tonic.name, "major")
        new_scale = new_key.getScale()
        new_pitches = list(new_scale.getPitches("C3", "C7"))
        var3_melody = []
        for p in theme_melody:
            closest = min(new_pitches, key=lambda x: abs(x.midi - p.midi))
            var3_melody.append(closest)
        var3_dur = list(theme_durations)

        return {
            "theme": (theme_melody, theme_durations),
            "var1_ornamental": (var1_melody, var1_dur),
            "var2_rhythmic": (var2_melody, var2_dur),
            "var3_mode_change": (var3_melody, var3_dur),
        }


# =============================================================================
# 9. COMPLETE MINI-COMPOSITION PIPELINE
# =============================================================================

class CompositionPipeline:
    """
    Chains all components to generate a complete 32-bar piano piece as MIDI.
    Structure: A (8 bars) - A' (8 bars) - B (8 bars) - A (8 bars)
    """

    def __init__(self, key_str: str = "C", bpm: int = 108):
        self.key_str = key_str
        self.bpm = bpm
        self.grammar = ChordGrammar(key_str)
        self.voice_leader = VoiceLeader()
        self.melody_gen = MelodyGenerator(key_str)
        self.alberti = AlbertiBass(key_str)
        self.key_obj = key.Key(key_str)
        self.phrase_gen = PhraseStructure(key_str)
        self.form = FormEngine(key_str)

    def _generate_section_chords(self, bars: int, end_on: str = "I") -> List[str]:
        """Generate chords for a section, ending on a specific chord."""
        prog = []
        while len(prog) < bars:
            phrase = self.grammar.derive("Phrase")
            prog.extend(phrase)
        prog = prog[:bars]
        prog[-1] = end_on
        if bars > 1:
            prog[-2] = "V7"  # set up cadence
        return prog

    def _melody_for_section(self, bars: int, contour_type: str = "arch") -> List[pitch.Pitch]:
        """Generate melody notes for a section (4 notes per bar = quarter notes)."""
        n = bars * 4
        if contour_type == "arch":
            contour = [math.sin(math.pi * x / (n - 1)) for x in range(n)]
        elif contour_type == "descending":
            contour = [1.0 - x / (n - 1) for x in range(n)]
        elif contour_type == "wave":
            contour = [0.5 + 0.4 * math.sin(2 * math.pi * x / (n / 2)) for x in range(n)]
        else:
            contour = [0.5] * n
        return self.melody_gen.generate(contour, n)

    def _voice_lead_progression(self, chords_rn: List[str]) -> List[Tuple[int, ...]]:
        """Produce SATB voicings for a chord progression using voice leading engine."""
        realized = self.grammar.realize(chords_rn)

        # Starting voicing: close position around middle C
        first_pcs = [p.pitchClass for p in realized[0].pitches]
        voicings_pool = self.voice_leader.all_voicings(first_pcs, num_voices=4,
                                                        low=48, high=72)
        current = voicings_pool[0] if voicings_pool else (48, 52, 55, 60)

        result = [current]
        for i in range(1, len(realized)):
            next_pcs = [p.pitchClass for p in realized[i].pitches]
            current = self.voice_leader.find_optimal(current, next_pcs, self.key_obj)
            result.append(current)
        return result

    def generate(self, filename: str = "composition.mid"):
        """Generate a complete 32-bar piece and write to MIDI."""
        print(f"Generating 32-bar piece in {self.key_str}...")

        # --- FORM: AABA, 8 bars each ---
        a_chords = self._generate_section_chords(8, end_on="V")   # half cadence
        b_keys = self.form.ternary_keys()
        b_grammar = ChordGrammar(b_keys["B"].split()[0])
        b_chords_raw = b_grammar.derive("Phrase")
        while len(b_chords_raw) < 8:
            b_chords_raw.extend(b_grammar.derive("Phrase"))
        b_chords = b_chords_raw[:8]
        b_chords[-1] = "V"  # retransition
        a_final = self._generate_section_chords(8, end_on="I")  # PAC

        # Full 32-bar chord sequence (A uses same chords twice, then B, then A')
        all_chords = a_chords + a_chords + b_chords + a_final

        # --- MELODY ---
        melody_a = self._melody_for_section(8, "arch")
        melody_b = self._melody_for_section(8, "wave")
        melody_a2 = self._melody_for_section(8, "descending")
        # Consequent starts like antecedent
        melody_a2[:8] = melody_a[:8]
        all_melody = melody_a + melody_a + melody_b + melody_a2

        # --- BASS (Alberti) ---
        bass_notes = self.alberti.generate(all_chords, beats_per_chord=4,
                                            pattern_type="standard", octave=3)

        # --- VOICE LEADING for inner parts ---
        voicings = self._voice_lead_progression(all_chords)

        # --- WRITE MIDI ---
        midi = MIDIFile(3)  # Track 0: melody, Track 1: bass, Track 2: inner voices

        # Track 0 — Melody (right hand upper)
        midi.addTrackName(0, 0, "Melody")
        midi.addTempo(0, 0, self.bpm)
        midi.addProgramChange(0, 0, 0, 0)  # Acoustic Grand Piano
        for i, p in enumerate(all_melody):
            velocity = 85 + random.randint(-5, 10)
            # Quarter notes
            midi.addNote(0, 0, p.midi, i * 1.0, 0.9, velocity)

        # Track 1 — Alberti Bass (left hand)
        midi.addTrackName(1, 0, "Bass")
        midi.addTempo(1, 0, self.bpm)
        midi.addProgramChange(1, 1, 0, 0)  # Piano
        for i, notes in enumerate(bass_notes):
            for n in notes:
                midi.addNote(1, 1, n, i * 0.5, 0.45, 65)  # eighth notes

        # Track 2 — Inner voices (from voice leading, sustained per bar)
        midi.addTrackName(2, 0, "Inner Voices")
        midi.addTempo(2, 0, self.bpm)
        midi.addProgramChange(2, 2, 0, 0)  # Piano
        for bar_idx, voicing in enumerate(voicings):
            # Write alto and tenor notes (indices 1 and 2 from SATB)
            for voice_idx in [1, 2]:
                if voice_idx < len(voicing):
                    midi.addNote(2, 2, voicing[voice_idx],
                                 bar_idx * 4.0, 3.8, 60)

        with open(filename, "wb") as f:
            midi.writeFile(f)

        print(f"Written to {filename}")
        print(f"  Sections: A({a_chords}) | A({a_chords}) | B({b_chords}) | A'({a_final})")
        print(f"  Total melody notes: {len(all_melody)}")
        print(f"  Total bass events:  {len(bass_notes)}")
        return filename


# =============================================================================
# DEMO / MAIN — Run all components
# =============================================================================

def demo_individual_components():
    """Demonstrate each component independently."""
    print("=" * 70)
    print("CLASSICAL MUSIC GENERATION TOOLKIT — Component Demo")
    print("=" * 70)

    # 1. Grammar
    print("\n[1] Chord Progression Grammar")
    g = ChordGrammar("C")
    prog = g.generate_progression(2)
    print(f"  Generated: {' - '.join(prog)}")
    realized = g.realize(prog)
    print(f"  Realized pitches: {[str(c.pitches) for c in realized[:4]]}...")

    # 2. Voice Leading
    print("\n[2] Voice Leading")
    vl = VoiceLeader()
    v1 = (48, 55, 60, 64)  # C major close position
    next_pcs = [7, 11, 2]  # G major triad pitch classes
    v2 = vl.find_optimal(v1, next_pcs, key.Key("C"))
    print(f"  C major voicing:  {v1}")
    print(f"  G major optimal:  {v2}")
    print(f"  Total movement:   {vl.total_movement(v1, v2)} semitones")
    print(f"  Parallel 5th/8ve: {vl.has_parallel_fifths_or_octaves(v1, v2)}")

    # 3. Melody with contour
    print("\n[3] Melody Generator (arch contour)")
    mg = MelodyGenerator("C", octave_low=4, octave_high=5)
    contour = [math.sin(math.pi * x / 15) for x in range(16)]
    melody = mg.generate(contour, 16)
    print(f"  Melody: {[str(p) for p in melody]}")

    # 4. Counterpoint
    print("\n[4] First-Species Counterpoint")
    solver = CounterpointSolver("C")
    cf = [pitch.Pitch(n) for n in ["C4", "D4", "F4", "E4", "A4", "G4",
                                    "E4", "D4", "C4"]]
    cp = solver.solve(cf)
    if cp:
        print(f"  CF: {[str(p) for p in cf]}")
        print(f"  CP: {[str(p) for p in cp]}")
        intervals = [abs(c.midi - f.midi) % 12 for c, f in zip(cp, cf)]
        print(f"  Intervals: {intervals}")

    # 5. Phrase structure
    print("\n[5] Antecedent-Consequent Period")
    ps = PhraseStructure("G")
    period = ps.generate_period(8)
    print(f"  Antecedent chords:  {period['antecedent_chords']}")
    print(f"  Consequent chords:  {period['consequent_chords']}")

    # 6. Alberti bass
    print("\n[6] Alberti Bass")
    ab = AlbertiBass("C")
    bass = ab.generate(["I", "IV", "V", "I"], beats_per_chord=4,
                       pattern_type="standard")
    midi_strs = [str(notes) for notes in bass]
    print(f"  Pattern (MIDI): {midi_strs}")

    # 7. Orchestration
    print("\n[7] Orchestration Mapper")
    om = OrchestrationMapper()
    satb = [(72, 67, 64, 48), (71, 67, 62, 47), (72, 67, 64, 48)]
    tracks = om.assign(satb, template="strings")
    print(f"  Instruments: {list(tracks.keys())}")
    for inst, notes in tracks.items():
        print(f"    {inst}: {notes}")

    # 8. Form engine
    print("\n[8] Form Template Engine")
    fe = FormEngine("D")
    keys = fe.ternary_keys()
    print(f"  Ternary form keys: {keys}")
    theme_pitches = [pitch.Pitch(n) for n in ["D5", "E5", "F#5", "A5",
                                               "G5", "F#5", "E5", "D5"]]
    theme_durs = [1.0] * 8
    variations = fe.theme_and_variations(theme_pitches, theme_durs)
    print(f"  Theme:      {[str(p) for p in variations['theme'][0]]}")
    print(f"  Var1 (orn): {[str(p) for p in variations['var1_ornamental'][0]]}")
    print(f"  Var3 (mode):{[str(p) for p in variations['var3_mode_change'][0]]}")


def main():
    """Generate a complete 32-bar piano piece."""
    random.seed(42)  # reproducible; remove for randomness

    # Show individual component demos
    demo_individual_components()

    # 9. Full pipeline
    print("\n" + "=" * 70)
    print("[9] COMPLETE 32-BAR COMPOSITION PIPELINE")
    print("=" * 70)
    pipeline = CompositionPipeline(key_str="C", bpm=108)
    output_file = pipeline.generate("composition_32bar.mid")
    print(f"\nDone. Open {output_file} in any MIDI player.")

    # Also generate an orchestral version
    print("\n[Bonus] Orchestral version...")
    g = ChordGrammar("C")
    prog = g.generate_progression(4)
    realized = g.realize(prog)
    vl = VoiceLeader()
    voicings = []
    current = (60, 64, 67, 72)
    voicings.append(current)
    for ch in realized[1:]:
        pcs = [p.pitchClass for p in ch.pitches]
        current = vl.find_optimal(current, pcs, key.Key("C"))
        voicings.append(current)

    om = OrchestrationMapper()
    tracks = om.assign(voicings, template="full")
    om.to_midi(tracks, "orchestral_version.mid", bpm=100)
    print("Written orchestral_version.mid")


if __name__ == "__main__":
    main()
