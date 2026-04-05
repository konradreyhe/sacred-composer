"""VoiceLeader — optimal voice leading between chords.

Finds the smoothest four-part voice leading from one chord voicing to the
next, penalising parallel 5ths/octaves, rewarding held common tones, and
enforcing leading-tone and 7th resolution.

Extracted from the former ``classical_music_gen.py`` toolkit so that the
``composer/`` package is self-contained and does not reach into a root-
level legacy module.
"""

from __future__ import annotations

import random
from itertools import product
from typing import List, Optional, Tuple

from music21 import key


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
                     key_obj: Optional[key.Key] = None) -> Tuple[int, ...]:
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
