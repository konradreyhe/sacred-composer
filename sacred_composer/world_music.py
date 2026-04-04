"""World music systems — non-Western scales, tunings, rhythms, and forms.

Extends Sacred Composer beyond Western classical with mathematically precise
encodings of Indian raga, Arabic maqam, Javanese gamelan, West African
polyrhythm, Japanese form, Balinese kotekan, and overtone singing.
"""

from __future__ import annotations

import math
import random as _rng_mod
from typing import Iterator

from sacred_composer.core import Composition


# ══════════════════════════════════════════════════════════════
# 1. INDIAN RAGA SYSTEM
# ══════════════════════════════════════════════════════════════

# The 16 svarasthanas (pitch positions) in Carnatic music.
# 72 melakarta ragas = systematic permutation of these into 7-note scales.
# Formula: pick 1 of {0}, 1 of {1,2}, 1 of {3,4}, 1 of {5}, 1 of {6,7},
#          1 of {8,9,10}, 1 of {10,11} — with constraints.
# We encode all 72 via the Katapayadi numbering scheme.

# Svarasthana intervals in cents from Sa (mapped to semitones for MIDI)
SVARASTHANAS = {
    "Sa": 0, "Ri1": 1, "Ri2": 2, "Ri3": 3,
    "Ga1": 2, "Ga2": 3, "Ga3": 4,
    "Ma1": 5, "Ma2": 6,
    "Pa": 7, "Da1": 8, "Da2": 9, "Da3": 10,
    "Ni1": 9, "Ni2": 10, "Ni3": 11,
}

# Melakarta lookup: lower 36 use Ma1, upper 36 use Ma2.
# Within each group of 36: 6 groups of 6, varying Ri/Ga x Da/Ni.
MELAKARTA_RI_GA = [
    (1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3),  # 6 combos
]
MELAKARTA_DA_NI = [
    (1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3),
]


def melakarta_scale(number: int) -> tuple[int, ...]:
    """Return semitone intervals for melakarta raga 1-72.

    Examples: 29 = Dheerashankarabharanam (Western major), 65 = Mechakalyani (Lydian).
    """
    if not 1 <= number <= 72:
        raise ValueError(f"Melakarta number must be 1-72, got {number}")
    idx = number - 1
    ma = 5 if idx < 36 else 6  # Ma1 or Ma2
    sub = idx % 36
    ri_ga_idx = sub // 6
    da_ni_idx = sub % 6
    ri_n, ga_n = MELAKARTA_RI_GA[ri_ga_idx]
    da_n, ni_n = MELAKARTA_DA_NI[da_ni_idx]

    ri = {1: 1, 2: 2, 3: 3}[ri_n]
    ga = {1: 2, 2: 3, 3: 4}[ga_n]
    # Ga must be >= Ri
    if ga < ri:
        ga = ri
    da = {1: 8, 2: 9, 3: 10}[da_n]
    ni = {1: 9, 2: 10, 3: 11}[ni_n]
    if ni < da:
        ni = da

    return (0, ri, ga, ma, 7, da, ni)


class Raga:
    """A raga with ascending/descending paths, vadi/samvadi, and gamaka rules.

    Parameters
    ----------
    name : Raga name for identification.
    arohana : Ascending pitch classes (semitones from root), e.g., (0, 2, 4, 5, 7, 9, 11).
    avarohana : Descending pitch classes (must descend), e.g., (11, 9, 7, 5, 4, 2, 0).
    vadi : Most important note (semitone from root).
    samvadi : Second most important note.
    gamakas : Dict of pitch_class -> gamaka type ("kampita", "jaru", "nokku").
    """

    def __init__(
        self,
        name: str,
        arohana: tuple[int, ...],
        avarohana: tuple[int, ...],
        vadi: int = 0,
        samvadi: int = 7,
        gamakas: dict[int, str] | None = None,
    ) -> None:
        self.name = name
        self.arohana = arohana
        self.avarohana = avarohana
        self.vadi = vadi
        self.samvadi = samvadi
        self.gamakas = gamakas or {}

    @classmethod
    def from_melakarta(cls, number: int, name: str | None = None) -> "Raga":
        """Create a raga from melakarta number (straight ascending/descending)."""
        scale = melakarta_scale(number)
        return cls(
            name=name or f"melakarta_{number}",
            arohana=scale,
            avarohana=tuple(reversed(scale)),
            vadi=scale[4],  # Pa by convention for parent ragas
            samvadi=scale[0],
        )

    def generate_melody(
        self,
        pattern_values: list[float],
        root: int = 60,
        octave_range: int = 2,
    ) -> list[int]:
        """Map pattern values to raga-constrained melody.

        Respects ascending/descending rules: if the pattern moves up,
        use arohana notes; if down, use avarohana notes.
        """
        pitches = []
        prev_val = pattern_values[0] if pattern_values else 0
        ascending = True

        for val in pattern_values:
            if val >= prev_val:
                ascending = True
            else:
                ascending = False
            prev_val = val

            pool = self.arohana if ascending else self.avarohana
            n_pool = len(pool)
            # Map value to index across octave range
            idx = int(abs(val)) % (n_pool * octave_range)
            octave_offset = idx // n_pool
            note_idx = idx % n_pool
            pitch = root + pool[note_idx] + 12 * octave_offset
            pitches.append(max(0, min(127, pitch)))

        return pitches

    def apply_gamakas(self, pitches: list[int]) -> list[float]:
        """Return fractional MIDI pitches with gamaka ornaments.

        kampita = oscillation (+/- 0.3 semitones)
        jaru = slide (approach from below by 0.5)
        nokku = stress/push (slight sharp, +0.15)
        """
        rng = _rng_mod.Random(pitches[0] if pitches else 0)
        result = []
        for p in pitches:
            pc = p % 12
            gamaka = self.gamakas.get(pc)
            if gamaka == "kampita":
                result.append(p + 0.3 * math.sin(rng.random() * math.pi))
            elif gamaka == "jaru":
                result.append(p - 0.5 + rng.random() * 0.5)
            elif gamaka == "nokku":
                result.append(p + 0.15)
            else:
                result.append(float(p))
        return result


# Tala system: additive meter patterns
TALAS = {
    "adi":        (4, 2, 2),        # 8 beats — most common
    "rupaka":     (2, 4),            # 6 beats (originally 3+2+2 regrouped)
    "misra_chapu": (3, 2, 2),       # 7 beats
    "khanda_chapu": (2, 1, 2),      # 5 beats
    "tisra_triputa": (3, 2, 2),     # 7 beats
    "jhaptal":    (2, 3, 2, 3),     # 10 beats (Hindustani)
    "tintal":     (4, 4, 4, 4),     # 16 beats (Hindustani)
    "rupak_tal":  (3, 2, 2),        # 7 beats (Hindustani)
}


def tala_pattern(tala_name: str, n_cycles: int = 4) -> list[float]:
    """Generate rhythmic durations from tala groupings.

    Returns beat durations with emphasis on group boundaries (sam = beat 1).
    """
    groups = TALAS.get(tala_name, TALAS["adi"])
    durations = []
    for _ in range(n_cycles):
        for g in groups:
            # First beat of group is full, subdivide rest
            durations.append(1.0)
            for _ in range(g - 1):
                durations.append(0.5)
    return durations


# ══════════════════════════════════════════════════════════════
# 2. ARABIC MAQAM — QUARTER-TONE SYSTEM
# ══════════════════════════════════════════════════════════════

# 24-TET: each step = 50 cents = quarter tone.
# Maqam intervals stored as number of quarter-tone steps.
# A whole tone = 4 quarter tones, a semitone = 2, a three-quarter tone = 3.

# Jins (pl. ajnas): tetrachord/trichord building blocks
AJNAS = {
    # name: (intervals in quarter tones, size in notes)
    "ajam":    (4, 4, 2),          # major tetrachord
    "nahawand": (4, 2, 4),         # minor tetrachord
    "kurd":    (2, 4, 4),          # phrygian tetrachord
    "hijaz":   (2, 6, 2),          # augmented second tetrachord
    "bayati":  (3, 3, 4),          # neutral second tetrachord (quarter tones!)
    "rast":    (4, 3, 3),          # neutral third tetrachord
    "sikah":   (3, 4, 3),          # neutral second tetrachord variant
    "saba":    (3, 3, 2),          # trichord (3 notes above root)
}

# Maqamat as combinations of ajnas
MAQAMAT = {
    # name: (lower_jins, upper_jins, junction_type)
    # junction_type: "disjunct" (gap of 1 whole tone) or "conjunct" (shared note)
    "rast":      ("rast", "rast", "disjunct"),
    "bayati":    ("bayati", "nahawand", "conjunct"),
    "hijaz":     ("hijaz", "rast", "disjunct"),
    "saba":      ("saba", "hijaz", "conjunct"),
    "nahawand":  ("nahawand", "hijaz", "disjunct"),
    "ajam":      ("ajam", "ajam", "disjunct"),
    "kurd":      ("kurd", "nahawand", "conjunct"),
    "sikah":     ("sikah", "rast", "conjunct"),
}


def maqam_scale(maqam_name: str, root_midi: int = 60) -> list[float]:
    """Return MIDI pitches (fractional for quarter tones) for a maqam.

    Quarter tones are represented as .5 additions to MIDI note numbers.
    Use with Composition.add_voice_microtonal() for proper MIDI rendering.
    """
    lower_name, upper_name, junction = MAQAMAT.get(
        maqam_name, MAQAMAT["rast"]
    )
    lower = AJNAS[lower_name]
    upper = AJNAS[upper_name]

    pitches = [root_midi]
    pos = 0.0

    # Lower jins
    for interval in lower:
        pos += interval * 0.5  # quarter tone steps to semitones
        pitches.append(root_midi + pos)

    # Junction
    if junction == "disjunct":
        pos += 2.0  # whole tone gap
        pitches.append(root_midi + pos)

    # Upper jins
    for interval in upper:
        pos += interval * 0.5
        pitches.append(root_midi + pos)

    return pitches


def maqam_sayr(
    maqam_name: str,
    pattern_values: list[float],
    root: int = 60,
) -> list[float]:
    """Generate a melodic path (sayr) through a maqam.

    The sayr follows traditional rules: start in lower jins, ascend
    to ghammaz (junction point), explore upper jins, descend.
    Returns fractional MIDI pitches.
    """
    scale = maqam_scale(maqam_name, root)
    n = len(scale)
    ghammaz_idx = n // 2  # junction point

    result = []
    phase_len = len(pattern_values) // 3

    for i, val in enumerate(pattern_values):
        if i < phase_len:
            # Phase 1: lower jins exploration
            idx = int(abs(val)) % (ghammaz_idx + 1)
        elif i < 2 * phase_len:
            # Phase 2: ascend to upper jins
            idx = ghammaz_idx + int(abs(val)) % (n - ghammaz_idx)
        else:
            # Phase 3: descend back
            idx = int(abs(val)) % n
        result.append(scale[idx])

    return result


# ══════════════════════════════════════════════════════════════
# 3. GAMELAN TUNING AND COLOTOMIC STRUCTURE
# ══════════════════════════════════════════════════════════════

# Slendro and pelog are NOT equal temperament. Each gamelan is unique.
# These are representative cent values from Surjodiningrat (1972).
GAMELAN_TUNINGS = {
    "slendro_solo": (0, 231, 474, 717, 955),          # 5-note, roughly equal
    "slendro_yogya": (0, 245, 485, 726, 960),
    "pelog_solo": (0, 124, 284, 539, 677, 784, 1018),  # 7-note, very unequal
    "pelog_yogya": (0, 117, 291, 546, 670, 793, 1025),
    # Abstract "ideal" slendro: 5-TET (240 cents each)
    "slendro_equal": tuple(i * 240 for i in range(5)),
    # Abstract "ideal" pelog: specific cent pattern
    "pelog_bem": (0, 120, 270, 540, 675, 780, 1020),
}


def gamelan_to_midi(tuning_name: str, root_midi: int = 60, octaves: int = 2) -> list[float]:
    """Convert gamelan cent tuning to fractional MIDI pitches.

    Returns pitches spanning given number of octaves.
    """
    cents = GAMELAN_TUNINGS.get(tuning_name, GAMELAN_TUNINGS["slendro_solo"])
    pitches = []
    for octave in range(octaves):
        for c in cents:
            midi = root_midi + octave * 12 + c / 100.0
            pitches.append(midi)
    return pitches


# Colotomic structure: nested gong cycles
# In a 16-beat gongan: gong ageng (16), kenong (8), ketuk (4), kempyang (2)
COLOTOMIC_STRUCTURES = {
    "lancaran":  {"gongan": 16, "kenong": 4,  "ketuk": 2, "kempul": 4},
    "ketawang":  {"gongan": 16, "kenong": 8,  "ketuk": 2, "kempul": 8},
    "ladrang":   {"gongan": 32, "kenong": 8,  "ketuk": 4, "kempul": 8},
    "gending":   {"gongan": 64, "kenong": 16, "ketuk": 4, "kempul": 16},
}


def colotomic_pattern(structure_name: str, n_gongans: int = 2) -> dict[str, list[int]]:
    """Generate colotomic marker positions.

    Returns dict mapping instrument names to lists of beat positions
    where they sound (0-indexed).
    """
    struct = COLOTOMIC_STRUCTURES.get(structure_name, COLOTOMIC_STRUCTURES["lancaran"])
    gongan_len = struct["gongan"]
    total_beats = gongan_len * n_gongans

    result = {}
    for inst, period in struct.items():
        if inst == "gongan":
            continue
        beats = []
        for b in range(total_beats):
            if (b + 1) % period == 0:
                beats.append(b)
        result[inst] = beats

    # Gong ageng sounds at end of each gongan
    result["gong"] = [gongan_len * (i + 1) - 1 for i in range(n_gongans)]

    return result


def balungan_elaborate(
    core_melody: list[int],
    style: str = "peking",
) -> list[int]:
    """Elaborate a balungan (core melody) in the style of a specific instrument.

    peking: double speed, neighbor tones above
    saron: same speed, slight ornamentation
    gender: half speed, intervals of a kempyung (roughly a fifth)
    """
    if style == "peking":
        elaborated = []
        for note in core_melody:
            elaborated.append(note + 1)  # upper neighbor
            elaborated.append(note)
        return elaborated
    elif style == "gender":
        # Half speed with kempyung (interval of ~2 in slendro = rough fifth)
        return [note for note in core_melody[::2]]
    else:  # saron
        return list(core_melody)


# ══════════════════════════════════════════════════════════════
# 4. WEST AFRICAN POLYRHYTHM
# ══════════════════════════════════════════════════════════════

# Timeline patterns (bell patterns) — the rhythmic DNA of West African music.
# Stored as onset positions within a cycle of N pulses.
TIMELINE_PATTERNS = {
    # Standard pattern (aka "standard bell"): 12/8 time
    "standard_12":    [0, 2, 4, 5, 7, 9, 10],    # 7 in 12
    # Agbadza bell (Ewe): 12 pulses
    "agbadza":        [0, 2, 4, 5, 7, 9, 10],
    # Gahu bell (Ewe): 16 pulses
    "gahu":           [0, 3, 6, 8, 10, 12, 14],
    # Bembé: 12 pulses
    "bembe":          [0, 2, 3, 5, 7, 8, 10],
    # Soukous: 16 pulses
    "soukous":        [0, 3, 5, 7, 9, 11, 13],
    # Shiko (Yoruba): 12 pulses
    "shiko":          [0, 2, 5, 7, 10],
    # Son clave: 16 pulses (Afro-Cuban, African origin)
    "son_clave":      [0, 3, 6, 10, 12],
    # Rumba clave: 16 pulses
    "rumba_clave":    [0, 3, 7, 10, 12],
    # Fume-fume (Ghana): 12 pulses
    "fume_fume":      [0, 2, 5, 7, 10],
    # Bata (Yoruba): 12 pulses, Iya drum
    "bata_iya":       [0, 1, 4, 5, 7, 8, 10],
}

# Cycle lengths for each pattern
TIMELINE_CYCLES = {
    "standard_12": 12, "agbadza": 12, "gahu": 16, "bembe": 12,
    "soukous": 16, "shiko": 12, "son_clave": 16, "rumba_clave": 16,
    "fume_fume": 12, "bata_iya": 12,
}


def cross_rhythm(a: int, b: int, total_pulses: int) -> tuple[list[int], list[int]]:
    """Generate two cross-rhythmic streams: a-against-b.

    Returns (stream_a, stream_b) where each is a binary onset list.

    Example: cross_rhythm(3, 4, 12) gives the 3-against-4 pattern.
    """
    stream_a = [0] * total_pulses
    stream_b = [0] * total_pulses

    step_a = total_pulses / a
    step_b = total_pulses / b

    for i in range(a):
        pos = int(round(i * step_a)) % total_pulses
        stream_a[pos] = 1
    for i in range(b):
        pos = int(round(i * step_b)) % total_pulses
        stream_b[pos] = 1

    return stream_a, stream_b


def polyrhythmic_texture(
    bell_pattern: str,
    n_layers: int = 3,
    n_cycles: int = 4,
    seed: int | None = None,
) -> list[list[int]]:
    """Generate a multi-layer polyrhythmic texture from a timeline pattern.

    Layer 0: the bell pattern (timeline).
    Layer 1+: complementary patterns derived by rotation and thinning.
    Returns list of binary onset patterns (one per layer).
    """
    rng = random.Random(seed)
    onsets = TIMELINE_PATTERNS.get(bell_pattern, TIMELINE_PATTERNS["standard_12"])
    cycle_len = TIMELINE_CYCLES.get(bell_pattern, 12)
    total = cycle_len * n_cycles

    # Layer 0: bell pattern, cycled
    bell = [0] * total
    for c in range(n_cycles):
        for o in onsets:
            bell[c * cycle_len + o] = 1

    layers = [bell]

    for layer_idx in range(1, n_layers):
        # Rotate the pattern and selectively thin
        rotation = rng.randint(1, cycle_len - 1)
        density = 1.0 - (layer_idx * 0.2)  # each layer slightly sparser
        pattern = [0] * total
        for c in range(n_cycles):
            for o in onsets:
                pos = (c * cycle_len + (o + rotation) % cycle_len)
                if rng.random() < density:
                    pattern[pos] = 1
        layers.append(pattern)

    return layers


# ══════════════════════════════════════════════════════════════
# 5. JAPANESE SCALES AND JO-HA-KYU
# ══════════════════════════════════════════════════════════════

# Japanese pentatonic modes
JAPANESE_SCALES = {
    "in_sen":     (0, 1, 5, 7, 10),    # In scale (dark, minor quality)
    "yo":         (0, 2, 5, 7, 9),     # Yo scale (bright, major quality)
    "miyako_bushi": (0, 1, 5, 7, 8),   # Miyako-bushi (urban)
    "kumoi":      (0, 2, 3, 7, 9),     # Kumoi
    "iwato":      (0, 1, 5, 6, 10),    # Iwato (same notes as In, different root)
    "hirajoshi":  (0, 2, 3, 7, 8),     # Hirajoshi
    "ritsu":      (0, 2, 5, 7, 9),     # Ritsu (gagaku mode)
    "ryo":        (0, 2, 4, 7, 9),     # Ryo (gagaku mode)
}


def jo_ha_kyu_curve(total_events: int) -> list[float]:
    """Generate a tempo/density multiplier following jo-ha-kyu.

    Jo (introduction): slow, sparse — ~25% of duration.
    Ha (development): accelerating, building — ~50%.
    Kyu (climax/conclusion): fast, dense, then abrupt stop — ~25%.

    Returns multipliers (0.5 to 2.0) for tempo or event density.
    """
    jo_end = int(total_events * 0.25)
    ha_end = int(total_events * 0.75)
    result = []

    for i in range(total_events):
        if i < jo_end:
            # Jo: slow start, gentle rise
            t = i / max(1, jo_end)
            result.append(0.5 + 0.3 * t)
        elif i < ha_end:
            # Ha: steady acceleration
            t = (i - jo_end) / max(1, ha_end - jo_end)
            result.append(0.8 + 0.7 * t)
        else:
            # Kyu: rapid climax
            t = (i - ha_end) / max(1, total_events - ha_end)
            result.append(1.5 + 0.5 * t)

    return result


def apply_ma(
    durations: list[float],
    silence_ratio: float = 0.3,
    seed: int | None = None,
) -> list[float]:
    """Insert 'ma' (meaningful silence) into a duration sequence.

    Replaces a proportion of notes with rests (negative durations),
    preferring longer rests at phrase boundaries (every 4-8 notes).
    """
    rng = random.Random(seed)
    result = []
    phrase_len = rng.randint(4, 8)

    for i, dur in enumerate(durations):
        at_boundary = (i > 0 and i % phrase_len == 0)
        if at_boundary:
            # Insert rest at phrase boundary
            result.append(-dur * (1.0 + rng.random()))
            phrase_len = rng.randint(4, 8)
        elif rng.random() < silence_ratio * 0.5:
            # Occasional internal rest
            result.append(-dur)
        else:
            result.append(dur)

    return result


# ══════════════════════════════════════════════════════════════
# 6. BALINESE KOTEKAN (INTERLOCKING PARTS)
# ══════════════════════════════════════════════════════════════

def kotekan_split(
    melody: list[int],
    durations: list[float],
    style: str = "norot",
) -> tuple[list[int], list[float], list[int], list[float]]:
    """Split a melody into two interlocking kotekan parts: polos and sangsih.

    polos = on-beat notes (even indices)
    sangsih = off-beat notes (odd indices), offset by a scale step

    style:
        "norot": sangsih mirrors polos a step above
        "ubit-ubitan": strict alternation (polos on even, sangsih on odd)
        "ocak-ocakan": complementary — when one plays, other rests

    Returns (polos_pitches, polos_durations, sangsih_pitches, sangsih_durations).
    """
    polos_p, polos_d = [], []
    sangsih_p, sangsih_d = [], []

    for i, (pitch, dur) in enumerate(zip(melody, durations)):
        half_dur = dur / 2 if dur > 0 else dur

        if style == "ubit-ubitan":
            if i % 2 == 0:
                polos_p.append(pitch)
                polos_d.append(half_dur)
                sangsih_p.append(-1)  # rest
                sangsih_d.append(-abs(half_dur))
            else:
                polos_p.append(-1)
                polos_d.append(-abs(half_dur))
                sangsih_p.append(pitch + 1)  # step above
                sangsih_d.append(half_dur)

        elif style == "ocak-ocakan":
            polos_p.append(pitch)
            polos_d.append(half_dur)
            sangsih_p.append(pitch + 2)  # offset
            sangsih_d.append(half_dur)

        else:  # norot
            polos_p.append(pitch)
            polos_d.append(half_dur)
            # Sangsih: neighbor tone, offset by half a beat
            sangsih_p.append(pitch + 1)
            sangsih_d.append(half_dur)

    return polos_p, polos_d, sangsih_p, sangsih_d


# ══════════════════════════════════════════════════════════════
# 7. TUVAN/MONGOLIAN OVERTONE SINGING
# ══════════════════════════════════════════════════════════════

def overtone_melody(
    fundamental_midi: int,
    partials: list[int],
    durations: list[float],
) -> tuple[list[float], list[float]]:
    """Create a melody from overtone selection over a drone.

    Given a fundamental (e.g., MIDI 36 = C2), select specific partials
    to create a melody — mimicking throat singing where the singer
    holds a drone and articulates overtones.

    Parameters
    ----------
    fundamental_midi : MIDI note of the drone fundamental.
    partials : List of partial numbers to play (e.g., [6, 8, 9, 10, 12]).
        Typical khoomei range: partials 6-13 (roughly pentatonic).
    durations : Duration for each note.

    Returns
    -------
    (melody_pitches, drone_pitch) — melody as fractional MIDI (overtones
    are not equal-tempered), drone as constant.
    """
    fundamental_freq = 440.0 * (2 ** ((fundamental_midi - 69) / 12.0))

    melody_pitches = []
    for p in partials:
        freq = fundamental_freq * p
        # Convert back to MIDI (fractional — overtones are not 12-TET)
        midi = 69 + 12 * math.log2(freq / 440.0)
        melody_pitches.append(midi)

    return melody_pitches, durations


# Common overtone singing partial sequences
KHOOMEI_PATTERNS = {
    # Sygyt style: bright, whistling overtones (partials 8-13)
    "sygyt":   [8, 9, 10, 9, 12, 10, 9, 8],
    # Khoomei style: mid-range overtones (partials 6-10)
    "khoomei":  [6, 8, 9, 10, 9, 8, 6, 8],
    # Kargyraa style: deep, sub-harmonic (partials 3-8)
    "kargyraa": [3, 4, 5, 6, 5, 4, 6, 8],
    # Pentatonic-like: partials 8,9,10,12 form a near-pentatonic
    "pentatonic_overtone": [8, 9, 10, 12, 10, 9, 8, 12],
}


# ══════════════════════════════════════════════════════════════
# CONVENIENCE: Pre-built raga definitions
# ══════════════════════════════════════════════════════════════

RAGA_PRESETS = {
    "yaman": Raga(
        "Yaman", arohana=(0, 2, 4, 6, 7, 9, 11),
        avarohana=(11, 9, 7, 6, 4, 2, 0),
        vadi=7, samvadi=4,
        gamakas={4: "kampita", 11: "kampita"},
    ),
    "bhairav": Raga(
        "Bhairav", arohana=(0, 1, 4, 5, 7, 8, 11),
        avarohana=(11, 8, 7, 5, 4, 1, 0),
        vadi=8, samvadi=1,
        gamakas={1: "jaru", 8: "jaru"},
    ),
    "todi": Raga(
        "Todi", arohana=(0, 1, 3, 6, 7, 8, 11),
        avarohana=(11, 8, 7, 6, 3, 1, 0),
        vadi=8, samvadi=3,
        gamakas={1: "kampita", 3: "kampita", 8: "jaru"},
    ),
    "malkauns": Raga(
        "Malkauns", arohana=(0, 3, 5, 8, 10),
        avarohana=(10, 8, 5, 3, 0),
        vadi=5, samvadi=0,
    ),
    "shankarabharanam": Raga.from_melakarta(29, "Shankarabharanam"),
    "kalyani": Raga.from_melakarta(65, "Kalyani"),
}
