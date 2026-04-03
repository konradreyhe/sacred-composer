"""Orchestration engine — intelligent instrument assignment and timbre control.

Inspired by Rimsky-Korsakov's orchestration principles and IRCAM's Orchidee
system for automated orchestration. Provides:

- Instrument database with register profiles, timbral descriptors, techniques
- Dynamic instrument assignment based on register, dynamics, texture, character
- Timbre vector matching (simplified Orchidee approach)
- Spatial panning following orchestral seating
- FluidSynth multi-SoundFont rendering support
- Extended technique representation via MIDI CC/keyswitches
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sacred_composer.core import Score, Voice, Note, GM_INSTRUMENTS


# ---------------------------------------------------------------------------
# Instrument Database (Rimsky-Korsakov codified)
# ---------------------------------------------------------------------------

class Technique(Enum):
    NORMAL = "normal"
    LEGATO = "legato"
    STACCATO = "staccato"
    PIZZICATO = "pizzicato"
    TREMOLO = "tremolo"
    TRILL = "trill"
    HARMONICS = "harmonics"
    COL_LEGNO = "col_legno"
    SUL_PONTICELLO = "sul_ponticello"
    SUL_TASTO = "sul_tasto"
    MUTED = "muted"
    STOPPED = "stopped"
    FLUTTER_TONGUE = "flutter_tongue"
    DOUBLE_TONGUE = "double_tongue"
    CON_SORDINO = "con_sordino"


@dataclass
class InstrumentProfile:
    """Complete profile for an orchestral instrument.

    Registers use MIDI note numbers. Timbre descriptors are 0.0-1.0.
    """
    name: str
    gm_program: int
    family: str  # "strings", "woodwinds", "brass", "percussion", "keyboard"

    # Ranges (MIDI note numbers)
    lowest_possible: int
    highest_possible: int
    lowest_effective: int
    highest_effective: int
    sweet_spot_low: int
    sweet_spot_high: int

    # Dynamic characteristics per register (low, mid, high)
    loudest_register: str = "high"    # "low", "mid", "high"
    softest_register: str = "low"     # where ppp is most natural

    # Timbre descriptor vector (Orchidee-inspired, MPEG-7 aligned)
    brightness: float = 0.5     # spectral centroid proxy
    warmth: float = 0.5         # low-mid energy
    roughness: float = 0.2      # inharmonicity / beating
    attack_sharpness: float = 0.5  # transient steepness
    richness: float = 0.5       # number of strong harmonics

    # Character tags for semantic matching
    character: tuple[str, ...] = ()  # e.g. ("noble", "warm", "singing")

    # Available extended techniques
    techniques: tuple[Technique, ...] = (Technique.NORMAL,)

    # Harmonic partials for additive synthesis: (harmonic_number, amplitude)
    partials: tuple[tuple[float, float], ...] = ((1, 1.0),)

    # Stereo pan position (-1.0 left to 1.0 right) — orchestral seating
    pan: float = 0.0

    # MIDI CC mappings for techniques
    technique_cc: dict[Technique, tuple[int, int]] = field(default_factory=dict)
    # Keyswitch mappings (note number that triggers articulation)
    technique_keyswitch: dict[Technique, int] = field(default_factory=dict)

    @property
    def timbre_vector(self) -> tuple[float, ...]:
        """5D timbre vector for Orchidee-style matching."""
        return (self.brightness, self.warmth, self.roughness,
                self.attack_sharpness, self.richness)

    def effectiveness(self, midi_pitch: int) -> float:
        """How effective is this instrument at a given pitch? 0.0-1.0."""
        if midi_pitch < self.lowest_possible or midi_pitch > self.highest_possible:
            return 0.0
        if midi_pitch < self.lowest_effective or midi_pitch > self.highest_effective:
            return 0.2  # playable but not ideal
        if self.sweet_spot_low <= midi_pitch <= self.sweet_spot_high:
            return 1.0
        # Linear interpolation between effective and sweet spot
        if midi_pitch < self.sweet_spot_low:
            dist = self.sweet_spot_low - midi_pitch
            range_ = self.sweet_spot_low - self.lowest_effective
            return 0.5 + 0.5 * (1 - dist / max(range_, 1))
        else:
            dist = midi_pitch - self.sweet_spot_high
            range_ = self.highest_effective - self.sweet_spot_high
            return 0.5 + 0.5 * (1 - dist / max(range_, 1))


# Complete orchestral instrument database
ORCHESTRA_DB: dict[str, InstrumentProfile] = {
    # ---- STRINGS ----
    "violin": InstrumentProfile(
        name="violin", gm_program=40, family="strings",
        lowest_possible=55, highest_possible=103,  # G3-G7
        lowest_effective=55, highest_effective=96,  # G3-C7
        sweet_spot_low=62, sweet_spot_high=86,      # D4-D6
        loudest_register="high", softest_register="mid",
        brightness=0.7, warmth=0.6, roughness=0.15,
        attack_sharpness=0.5, richness=0.7,
        character=("singing", "brilliant", "expressive"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.PIZZICATO, Technique.TREMOLO, Technique.TRILL,
                    Technique.HARMONICS, Technique.COL_LEGNO,
                    Technique.SUL_PONTICELLO, Technique.SUL_TASTO,
                    Technique.CON_SORDINO),
        partials=((1, 1.0), (2, 0.75), (3, 0.55), (4, 0.35),
                  (5, 0.25), (6, 0.15), (7, 0.1), (8, 0.06)),
        pan=-0.5,  # audience left
        technique_cc={Technique.TREMOLO: (1, 127)},  # modulation wheel
        technique_keyswitch={
            Technique.NORMAL: 24, Technique.LEGATO: 25,
            Technique.STACCATO: 26, Technique.PIZZICATO: 27,
            Technique.TREMOLO: 28, Technique.HARMONICS: 29,
        },
    ),
    "viola": InstrumentProfile(
        name="viola", gm_program=41, family="strings",
        lowest_possible=48, highest_possible=93,  # C3-A6
        lowest_effective=48, highest_effective=86,
        sweet_spot_low=55, sweet_spot_high=79,     # G3-G5
        loudest_register="high", softest_register="low",
        brightness=0.5, warmth=0.7, roughness=0.2,
        attack_sharpness=0.45, richness=0.65,
        character=("warm", "dark", "singing"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.PIZZICATO, Technique.TREMOLO, Technique.TRILL,
                    Technique.HARMONICS, Technique.COL_LEGNO,
                    Technique.SUL_PONTICELLO, Technique.CON_SORDINO),
        partials=((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.4),
                  (5, 0.3), (6, 0.2), (7, 0.12)),
        pan=-0.2,
    ),
    "cello": InstrumentProfile(
        name="cello", gm_program=42, family="strings",
        lowest_possible=36, highest_possible=84,  # C2-C6
        lowest_effective=36, highest_effective=79,
        sweet_spot_low=43, sweet_spot_high=72,     # G2-C5
        loudest_register="high", softest_register="low",
        brightness=0.45, warmth=0.85, roughness=0.15,
        attack_sharpness=0.45, richness=0.75,
        character=("noble", "warm", "singing", "passionate"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.PIZZICATO, Technique.TREMOLO, Technique.TRILL,
                    Technique.HARMONICS, Technique.SUL_PONTICELLO,
                    Technique.CON_SORDINO),
        partials=((1, 1.0), (2, 0.85), (3, 0.65), (4, 0.45),
                  (5, 0.3), (6, 0.2), (7, 0.12), (8, 0.08)),
        pan=0.2,
    ),
    "contrabass": InstrumentProfile(
        name="contrabass", gm_program=43, family="strings",
        lowest_possible=28, highest_possible=67,  # E1-G4
        lowest_effective=28, highest_effective=60,
        sweet_spot_low=33, sweet_spot_high=55,     # A1-G3
        loudest_register="mid", softest_register="low",
        brightness=0.25, warmth=0.9, roughness=0.25,
        attack_sharpness=0.35, richness=0.6,
        character=("deep", "foundational", "dark"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.PIZZICATO, Technique.TREMOLO),
        partials=((1, 1.0), (2, 0.9), (3, 0.7), (4, 0.5),
                  (5, 0.35), (6, 0.2)),
        pan=0.5,  # audience right
    ),

    # ---- WOODWINDS ----
    "flute": InstrumentProfile(
        name="flute", gm_program=73, family="woodwinds",
        lowest_possible=60, highest_possible=96,  # C4-C7
        lowest_effective=60, highest_effective=93,
        sweet_spot_low=67, sweet_spot_high=86,     # G4-D6
        loudest_register="high", softest_register="low",
        brightness=0.8, warmth=0.3, roughness=0.05,
        attack_sharpness=0.6, richness=0.3,
        character=("bright", "airy", "pastoral", "ethereal"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.TRILL, Technique.FLUTTER_TONGUE,
                    Technique.HARMONICS),
        partials=((1, 1.0), (2, 0.25), (3, 0.08)),
        pan=-0.6,
    ),
    "oboe": InstrumentProfile(
        name="oboe", gm_program=68, family="woodwinds",
        lowest_possible=58, highest_possible=91,  # Bb3-G6
        lowest_effective=58, highest_effective=86,
        sweet_spot_low=62, sweet_spot_high=81,     # D4-A5
        loudest_register="high", softest_register="mid",
        brightness=0.65, warmth=0.5, roughness=0.3,
        attack_sharpness=0.7, richness=0.7,
        character=("plaintive", "piercing", "pastoral", "expressive"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.TRILL),
        partials=((1, 1.0), (2, 0.7), (3, 0.6), (4, 0.5),
                  (5, 0.35), (6, 0.25), (7, 0.15)),
        pan=-0.4,
    ),
    "clarinet": InstrumentProfile(
        name="clarinet", gm_program=71, family="woodwinds",
        lowest_possible=50, highest_possible=94,  # D3-Bb6
        lowest_effective=52, highest_effective=91,
        sweet_spot_low=58, sweet_spot_high=82,     # Bb3-Bb5
        # Chalumeau register (low): warm, dark, rich
        # Clarion register (mid-high): bright, singing
        # Altissimo (high): thin, piercing
        loudest_register="high", softest_register="low",
        brightness=0.55, warmth=0.65, roughness=0.1,
        attack_sharpness=0.55, richness=0.6,
        character=("warm", "playful", "singing", "versatile"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.TRILL),
        partials=((1, 1.0), (3, 0.75), (5, 0.5), (7, 0.25), (9, 0.12)),
        # Note: odd harmonics dominate (cylindrical bore)
        pan=-0.3,
    ),
    "bassoon": InstrumentProfile(
        name="bassoon", gm_program=70, family="woodwinds",
        lowest_possible=34, highest_possible=77,  # Bb1-F5
        lowest_effective=34, highest_effective=74,
        sweet_spot_low=41, sweet_spot_high=67,     # F2-G4
        loudest_register="high", softest_register="low",
        brightness=0.35, warmth=0.75, roughness=0.25,
        attack_sharpness=0.55, richness=0.65,
        character=("warm", "dark", "humorous", "stately"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.TRILL),
        partials=((1, 1.0), (2, 0.8), (3, 0.65), (4, 0.5),
                  (5, 0.35), (6, 0.2)),
        pan=0.3,
    ),

    # ---- BRASS ----
    "horn": InstrumentProfile(
        name="horn", gm_program=60, family="brass",
        lowest_possible=34, highest_possible=77,  # Bb1-F5
        lowest_effective=36, highest_effective=74,
        sweet_spot_low=43, sweet_spot_high=67,     # G2-G4
        loudest_register="high", softest_register="low",
        brightness=0.4, warmth=0.85, roughness=0.15,
        attack_sharpness=0.4, richness=0.7,
        character=("noble", "warm", "heroic", "romantic"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.MUTED, Technique.STOPPED),
        partials=((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.35),
                  (5, 0.2), (6, 0.12)),
        pan=0.4,
        technique_cc={Technique.MUTED: (1, 80), Technique.STOPPED: (1, 127)},
    ),
    "trumpet": InstrumentProfile(
        name="trumpet", gm_program=56, family="brass",
        lowest_possible=55, highest_possible=84,  # G3-C6
        lowest_effective=55, highest_effective=82,
        sweet_spot_low=60, sweet_spot_high=77,     # C4-F5
        loudest_register="high", softest_register="low",
        brightness=0.8, warmth=0.4, roughness=0.2,
        attack_sharpness=0.8, richness=0.65,
        character=("brilliant", "heroic", "commanding", "festive"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.MUTED, Technique.FLUTTER_TONGUE),
        partials=((1, 1.0), (2, 0.8), (3, 0.65), (4, 0.5),
                  (5, 0.4), (6, 0.3), (7, 0.2)),
        pan=-0.5,
    ),
    "trombone": InstrumentProfile(
        name="trombone", gm_program=57, family="brass",
        lowest_possible=40, highest_possible=77,  # E2-F5
        lowest_effective=40, highest_effective=74,
        sweet_spot_low=46, sweet_spot_high=67,     # Bb2-G4
        loudest_register="high", softest_register="low",
        brightness=0.55, warmth=0.6, roughness=0.25,
        attack_sharpness=0.7, richness=0.7,
        character=("powerful", "majestic", "solemn"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO,
                    Technique.MUTED),
        partials=((1, 1.0), (2, 0.85), (3, 0.7), (4, 0.5),
                  (5, 0.35), (6, 0.25)),
        pan=0.4,
    ),
    "tuba": InstrumentProfile(
        name="tuba", gm_program=58, family="brass",
        lowest_possible=28, highest_possible=65,  # E1-F4
        lowest_effective=29, highest_effective=60,
        sweet_spot_low=33, sweet_spot_high=55,     # A1-G3
        loudest_register="mid", softest_register="low",
        brightness=0.2, warmth=0.85, roughness=0.2,
        attack_sharpness=0.4, richness=0.6,
        character=("deep", "foundational", "powerful"),
        techniques=(Technique.NORMAL, Technique.LEGATO, Technique.STACCATO),
        partials=((1, 1.0), (2, 0.9), (3, 0.7), (4, 0.5),
                  (5, 0.3)),
        pan=0.5,
    ),

    # ---- KEYBOARDS / PLUCKED ----
    "harp": InstrumentProfile(
        name="harp", gm_program=46, family="strings",
        lowest_possible=24, highest_possible=103,  # C1-G7
        lowest_effective=24, highest_effective=96,
        sweet_spot_low=48, sweet_spot_high=84,
        loudest_register="mid", softest_register="high",
        brightness=0.6, warmth=0.5, roughness=0.05,
        attack_sharpness=0.9, richness=0.4,
        character=("ethereal", "shimmering", "delicate"),
        techniques=(Technique.NORMAL, Technique.HARMONICS),
        partials=((1, 1.0), (2, 0.4), (3, 0.15), (4, 0.06)),
        pan=0.6,
    ),
    "timpani": InstrumentProfile(
        name="timpani", gm_program=47, family="percussion",
        lowest_possible=41, highest_possible=57,  # F2-A3
        lowest_effective=41, highest_effective=57,
        sweet_spot_low=43, sweet_spot_high=55,
        loudest_register="mid", softest_register="mid",
        brightness=0.3, warmth=0.7, roughness=0.4,
        attack_sharpness=0.95, richness=0.5,
        character=("dramatic", "thunderous", "ceremonial"),
        techniques=(Technique.NORMAL, Technique.TREMOLO, Technique.MUTED),
        partials=((1, 1.0), (1.5, 0.6), (2.0, 0.4), (2.44, 0.25)),
        pan=0.0,
    ),
}


# ---------------------------------------------------------------------------
# Timbre Matching (Orchidee-inspired)
# ---------------------------------------------------------------------------

def timbre_distance(v1: tuple[float, ...], v2: tuple[float, ...]) -> float:
    """Euclidean distance between two timbre vectors.

    Orchidee uses spectral envelope matching; this is a simplified
    perceptual-feature approximation. The 5 dimensions are:
    (brightness, warmth, roughness, attack_sharpness, richness)
    weighted by perceptual importance.
    """
    weights = (1.5, 1.2, 0.8, 1.0, 1.0)  # brightness matters most
    return math.sqrt(sum(
        w * (a - b) ** 2 for w, a, b in zip(weights, v1, v2)
    ))


# Semantic timbre targets — "this passage needs warmth" etc.
TIMBRE_TARGETS: dict[str, tuple[float, ...]] = {
    #                (bright, warm, rough, attack, rich)
    "warm":          (0.3, 0.9, 0.1, 0.3, 0.6),
    "bright":        (0.9, 0.3, 0.2, 0.6, 0.5),
    "dark":          (0.2, 0.8, 0.2, 0.3, 0.7),
    "ethereal":      (0.7, 0.3, 0.0, 0.4, 0.2),
    "powerful":      (0.6, 0.5, 0.4, 0.7, 0.8),
    "delicate":      (0.5, 0.4, 0.0, 0.3, 0.3),
    "noble":         (0.4, 0.7, 0.1, 0.4, 0.7),
    "pastoral":      (0.6, 0.5, 0.1, 0.5, 0.4),
    "dramatic":      (0.7, 0.5, 0.5, 0.8, 0.9),
    "mysterious":    (0.3, 0.6, 0.3, 0.2, 0.5),
}


def find_best_instruments(
    target: str | tuple[float, ...],
    pitch: int = 60,
    max_results: int = 3,
) -> list[tuple[str, float]]:
    """Find instruments closest to a target timbre at a given pitch.

    Parameters
    ----------
    target : Either a semantic name ("warm", "bright") or a 5D timbre vector.
    pitch : MIDI pitch to check register effectiveness.
    max_results : How many to return.

    Returns
    -------
    List of (instrument_name, score) sorted best first. Score is 0.0-1.0.
    """
    if isinstance(target, str):
        target_vec = TIMBRE_TARGETS.get(target, (0.5, 0.5, 0.5, 0.5, 0.5))
    else:
        target_vec = target

    candidates = []
    for name, profile in ORCHESTRA_DB.items():
        eff = profile.effectiveness(pitch)
        if eff <= 0:
            continue
        dist = timbre_distance(target_vec, profile.timbre_vector)
        # Combined score: low distance + high effectiveness
        score = eff / (1 + dist)
        candidates.append((name, score))

    candidates.sort(key=lambda x: -x[1])
    # Normalize scores to 0-1
    if candidates:
        best = candidates[0][1]
        candidates = [(n, s / best) for n, s in candidates]
    return candidates[:max_results]


# ---------------------------------------------------------------------------
# Dynamic Instrument Assignment
# ---------------------------------------------------------------------------

class TextureType(Enum):
    LEGATO_MELODY = "legato_melody"
    STACCATO_PASSAGE = "staccato_passage"
    SUSTAINED_HARMONY = "sustained_harmony"
    RHYTHMIC = "rhythmic"
    ARPEGGIATED = "arpeggiated"
    TREMOLO = "tremolo"
    CHORALE = "chorale"


# Texture -> preferred instrument families/characters
TEXTURE_PREFERENCES: dict[TextureType, dict[str, Any]] = {
    TextureType.LEGATO_MELODY: {
        "families": ["strings", "woodwinds"],
        "characters": ["singing", "expressive"],
        "technique": Technique.LEGATO,
    },
    TextureType.STACCATO_PASSAGE: {
        "families": ["woodwinds", "strings"],
        "characters": ["playful", "versatile"],
        "technique": Technique.STACCATO,
    },
    TextureType.SUSTAINED_HARMONY: {
        "families": ["brass", "strings"],
        "characters": ["noble", "warm"],
        "technique": Technique.NORMAL,
    },
    TextureType.RHYTHMIC: {
        "families": ["percussion", "brass", "woodwinds"],
        "characters": ["commanding", "festive"],
        "technique": Technique.STACCATO,
    },
    TextureType.ARPEGGIATED: {
        "families": ["strings", "woodwinds"],
        "characters": ["delicate", "shimmering"],
        "technique": Technique.NORMAL,
    },
    TextureType.CHORALE: {
        "families": ["brass", "strings"],
        "characters": ["noble", "solemn", "majestic"],
        "technique": Technique.LEGATO,
    },
}


def assign_instrument(
    pitch_range: tuple[int, int],
    dynamic_level: int,
    texture: TextureType = TextureType.LEGATO_MELODY,
    character: str | None = None,
) -> str:
    """Algorithmically choose the best instrument for a passage.

    Parameters
    ----------
    pitch_range : (lowest_midi, highest_midi) of the passage.
    dynamic_level : Average MIDI velocity (1-127).
    texture : The musical texture type.
    character : Optional semantic hint ("noble", "playful", etc.).

    Returns
    -------
    Instrument name from ORCHESTRA_DB.
    """
    mid_pitch = (pitch_range[0] + pitch_range[1]) // 2
    prefs = TEXTURE_PREFERENCES.get(texture, TEXTURE_PREFERENCES[TextureType.LEGATO_MELODY])

    best_name = "violin"
    best_score = -1.0

    for name, profile in ORCHESTRA_DB.items():
        score = 0.0

        # Register effectiveness
        eff_low = profile.effectiveness(pitch_range[0])
        eff_high = profile.effectiveness(pitch_range[1])
        eff_mid = profile.effectiveness(mid_pitch)
        score += (eff_low + eff_high + eff_mid * 2) / 4 * 3.0

        # Family preference
        if profile.family in prefs["families"]:
            rank = prefs["families"].index(profile.family)
            score += (len(prefs["families"]) - rank) * 0.5

        # Character match
        if character:
            if character in profile.character:
                score += 2.0
        for c in prefs.get("characters", []):
            if c in profile.character:
                score += 0.5

        # Technique availability
        technique = prefs.get("technique", Technique.NORMAL)
        if technique in profile.techniques:
            score += 1.0

        # Dynamic suitability
        if dynamic_level < 40:  # soft passage
            if profile.softest_register == "low" and mid_pitch < 60:
                score += 0.5
            if profile.family == "woodwinds":
                score += 0.3  # woodwinds excel at soft passages
        elif dynamic_level > 100:  # loud passage
            if profile.loudest_register == "high" and mid_pitch > 60:
                score += 0.5
            if profile.family == "brass":
                score += 0.3

        if score > best_score:
            best_score = score
            best_name = name

    return best_name


def suggest_doubling(
    instrument: str,
    pitch: int,
    dynamic_level: int,
) -> list[str]:
    """Suggest Rimsky-Korsakov-style doubling instruments.

    Rules:
    - Melody in octaves: violin + flute (upper), cello + bassoon (lower)
    - Warmth: horn doubles cello
    - Brilliance: trumpet doubles violin in forte
    - Blend: clarinet + horn = "golden" combination
    """
    profile = ORCHESTRA_DB.get(instrument)
    if not profile:
        return []

    doublings = []
    if instrument == "violin" and dynamic_level > 90:
        doublings.append("flute")  # octave above for brilliance
    if instrument == "violin" and dynamic_level > 100:
        doublings.append("trumpet")  # heroic doubling
    if instrument == "cello":
        if dynamic_level > 80:
            doublings.append("bassoon")  # classic cello+bassoon
        if dynamic_level > 60:
            doublings.append("horn")  # warmth
    if instrument == "oboe" and dynamic_level < 70:
        doublings.append("clarinet")  # blend
    if instrument == "flute" and pitch < 70:
        doublings.append("clarinet")  # low flute + clarinet warmth
    if instrument == "horn":
        doublings.append("clarinet")  # "golden combination"

    return doublings


# ---------------------------------------------------------------------------
# Spatial Audio — Orchestral Seating & Reverb
# ---------------------------------------------------------------------------

# Standard orchestral seating positions (pan: -1 left, +1 right)
# American seating arrangement
ORCHESTRAL_SEATING: dict[str, float] = {
    name: profile.pan for name, profile in ORCHESTRA_DB.items()
}


def apply_stereo_panning(
    samples_left: list[float],
    samples_right: list[float],
    pan: float,
    signal: list[float],
    start_idx: int,
) -> None:
    """Mix a mono signal into stereo buffers with constant-power panning."""
    # Constant-power pan law: preserves perceived loudness
    angle = (pan + 1.0) / 2.0 * (math.pi / 2.0)
    gain_left = math.cos(angle)
    gain_right = math.sin(angle)

    for i, s in enumerate(signal):
        idx = start_idx + i
        if idx < len(samples_left):
            samples_left[idx] += s * gain_left
            samples_right[idx] += s * gain_right


def generate_hall_impulse(
    sample_rate: int = 44100,
    rt60: float = 1.8,
    early_reflection_count: int = 12,
) -> list[float]:
    """Generate a simplified concert hall impulse response.

    Models:
    - Direct sound (delta)
    - Early reflections (discrete delays from walls/ceiling)
    - Late reverb (exponential decay noise)

    Parameters
    ----------
    rt60 : Reverberation time in seconds (1.5-2.5 for concert halls).
    early_reflection_count : Number of early reflection taps.
    """
    import random
    random.seed(42)  # reproducible

    total_samples = int(rt60 * 2 * sample_rate)
    ir = [0.0] * total_samples

    # Direct sound
    ir[0] = 1.0

    # Early reflections: spaced 5-50ms, decreasing amplitude
    for i in range(early_reflection_count):
        delay_ms = 5 + i * 4 + random.uniform(0, 3)
        delay_samples = int(delay_ms * sample_rate / 1000)
        amp = 0.5 * (0.8 ** i)
        if delay_samples < total_samples:
            ir[delay_samples] += amp * (1 if random.random() > 0.5 else -1)

    # Late reverb: gaussian noise with exponential decay
    decay_rate = -6.91 / (rt60 * sample_rate)  # -60dB at rt60
    late_start = int(0.08 * sample_rate)  # starts after 80ms
    for i in range(late_start, total_samples):
        noise = random.gauss(0, 0.15)
        envelope = math.exp(decay_rate * i)
        ir[i] += noise * envelope

    # Normalize
    peak = max(abs(s) for s in ir)
    if peak > 0:
        ir = [s / peak for s in ir]

    return ir


def convolve_reverb(
    dry_signal: list[float],
    impulse_response: list[float],
    wet_ratio: float = 0.25,
) -> list[float]:
    """Apply convolution reverb. Uses scipy if available, else brute-force.

    Parameters
    ----------
    wet_ratio : Mix ratio of reverb (0.0 = dry, 1.0 = full reverb).
    """
    try:
        import numpy as np
        from scipy.signal import fftconvolve
        dry = np.array(dry_signal)
        ir = np.array(impulse_response)
        wet = fftconvolve(dry, ir, mode="full")[:len(dry)]
        # Normalize wet to match dry peak
        dry_peak = np.max(np.abs(dry)) or 1.0
        wet_peak = np.max(np.abs(wet)) or 1.0
        wet = wet * (dry_peak / wet_peak)
        result = (1 - wet_ratio) * dry + wet_ratio * wet
        return result.tolist()
    except ImportError:
        # Brute-force convolution (slow but works)
        n = len(dry_signal)
        m = min(len(impulse_response), 4000)  # limit IR length for speed
        wet = [0.0] * n
        for i in range(n):
            for j in range(min(m, n - i)):
                wet[i + j] += dry_signal[i] * impulse_response[j]
        # Normalize
        dry_peak = max(abs(s) for s in dry_signal) or 1.0
        wet_peak = max(abs(s) for s in wet) or 1.0
        scale = dry_peak / wet_peak
        return [
            (1 - wet_ratio) * d + wet_ratio * w * scale
            for d, w in zip(dry_signal, wet)
        ]


# ---------------------------------------------------------------------------
# FluidSynth Multi-SoundFont Setup
# ---------------------------------------------------------------------------

@dataclass
class SoundFontAssignment:
    """Map an instrument to a specific SoundFont and bank/preset."""
    instrument: str
    soundfont_path: str
    bank: int = 0
    preset: int = 0  # GM program number


def generate_fluidsynth_config(
    assignments: list[SoundFontAssignment],
    midi_path: str,
    wav_path: str,
) -> str:
    """Generate a FluidSynth command script for multi-SoundFont rendering.

    FluidSynth supports loading multiple SoundFonts and assigning them
    per channel. This generates the shell command to do so.

    Free SoundFonts with extended techniques:
    - VSCO2 Community Orchestra (vsco2-ce): strings, winds, brass
    - Sonatina Symphonic Orchestra: full orchestra
    - BBC SO Discover / Spitfire LABS: not .sf2 but Kontakt/own format
      (use via DAW, not FluidSynth)

    For programmatic SoundFont access, use python-soundfont or sf2utils.
    """
    # Build fluidsynth command with multiple -F flags
    sf_loads = []
    seen = set()
    for a in assignments:
        if a.soundfont_path not in seen:
            sf_loads.append(f'load "{a.soundfont_path}"')
            seen.add(a.soundfont_path)

    # Channel assignments
    channel_cmds = []
    for i, a in enumerate(assignments):
        channel = i % 16
        sf_idx = list(seen).index(a.soundfont_path)
        channel_cmds.append(
            f"select {channel} {sf_idx + 1} {a.bank} {a.preset}"
        )

    script = "\n".join(sf_loads + channel_cmds)
    return script


# ---------------------------------------------------------------------------
# Extended Technique MIDI Representation
# ---------------------------------------------------------------------------

# MIDI CC numbers for extended techniques (common conventions)
TECHNIQUE_TO_CC: dict[Technique, tuple[int, int]] = {
    Technique.NORMAL:          (64, 0),    # sustain pedal off
    Technique.LEGATO:          (68, 127),  # legato footswitch
    Technique.STACCATO:        (64, 0),    # (short notes, no pedal)
    Technique.PIZZICATO:       (0, 45),    # bank select to pizz patch
    Technique.TREMOLO:         (1, 127),   # modulation wheel
    Technique.MUTED:           (1, 80),    # partial modulation
    Technique.CON_SORDINO:     (1, 60),    # light modulation
    Technique.FLUTTER_TONGUE:  (1, 110),   # heavy modulation
    Technique.HARMONICS:       (1, 40),    # light modulation
}

# For SoundFonts that support keyswitches (VSCO2, SSO)
# Keyswitches are typically in the C0-B0 range (MIDI 24-35)
DEFAULT_KEYSWITCHES: dict[Technique, int] = {
    Technique.NORMAL: 24,       # C1
    Technique.LEGATO: 25,       # C#1
    Technique.STACCATO: 26,     # D1
    Technique.PIZZICATO: 27,    # D#1
    Technique.TREMOLO: 28,      # E1
    Technique.TRILL: 29,        # F1
    Technique.HARMONICS: 30,    # F#1
    Technique.COL_LEGNO: 31,    # G1
    Technique.SUL_PONTICELLO: 32,  # G#1
    Technique.MUTED: 33,        # A1
    Technique.CON_SORDINO: 34,  # A#1
    Technique.FLUTTER_TONGUE: 35,  # B1
}


# ---------------------------------------------------------------------------
# Orchestral WAV Renderer (enhanced)
# ---------------------------------------------------------------------------

def render_orchestral_wav(
    score: Score,
    filename: str,
    sample_rate: int = 44100,
    reverb: bool = True,
    stereo: bool = True,
) -> str:
    """Render a Score to stereo WAV with orchestral timbres and spatial audio.

    Enhanced version of wav_renderer.render_wav that uses:
    - Instrument-specific harmonic partials from ORCHESTRA_DB
    - Stereo panning following orchestral seating
    - Optional convolution reverb (concert hall impulse response)
    """
    import struct as _struct

    beats_per_sec = score.tempo / 60.0
    total_dur_sec = score.duration / beats_per_sec + 2.0
    total_samples = int(total_dur_sec * sample_rate)

    buf_l = [0.0] * total_samples
    buf_r = [0.0] * total_samples

    for voice in score.voices:
        # Look up orchestral profile by GM program
        profile = None
        for name, p in ORCHESTRA_DB.items():
            if p.gm_program == voice.instrument:
                profile = p
                break
        if profile is None:
            # Fallback: use default piano-like partials
            partials = ((1, 1.0), (2, 0.5), (3, 0.25))
            pan = 0.0
        else:
            partials = profile.partials
            pan = profile.pan

        for note in voice.notes:
            if note.is_rest:
                continue

            freq = 440.0 * (2 ** ((note.pitch + note.pitch_bend - 69) / 12))
            start_sec = note.time / beats_per_sec
            dur_sec = note.duration / beats_per_sec
            amp = (note.velocity / 127.0) * 0.2

            attack = min(0.04, dur_sec * 0.1)
            decay = min(0.08, dur_sec * 0.2)
            release = min(0.2, dur_sec * 0.3)

            total_note_dur = dur_sec + release
            n_samples = int(total_note_dur * sample_rate)
            start_idx = int(start_sec * sample_rate)

            # Constant-power panning
            angle = (pan + 1.0) / 2.0 * (math.pi / 2.0)
            gain_l = math.cos(angle)
            gain_r = math.sin(angle)

            two_pi = 2.0 * math.pi
            for harmonic, rel_amp in partials:
                h_freq = freq * harmonic
                if h_freq > sample_rate / 2:
                    continue
                phase_inc = two_pi * h_freq / sample_rate
                phase = 0.0
                for i in range(n_samples):
                    idx = start_idx + i
                    if idx >= total_samples:
                        break
                    t = i / sample_rate
                    # ADSR
                    if t < attack:
                        env = t / attack if attack > 0 else 1.0
                    elif t < attack + decay:
                        env = 1.0 - 0.3 * ((t - attack) / decay) if decay > 0 else 0.7
                    elif t < dur_sec:
                        env = 0.7
                    else:
                        rt = t - dur_sec
                        env = 0.7 * (1 - rt / release) if release > 0 else 0.0
                        env = max(0.0, env)

                    sample = math.sin(phase) * rel_amp * amp * env
                    buf_l[idx] += sample * gain_l
                    buf_r[idx] += sample * gain_r
                    phase += phase_inc

    # Apply reverb
    if reverb:
        ir = generate_hall_impulse(sample_rate, rt60=1.8)
        buf_l = convolve_reverb(buf_l, ir, wet_ratio=0.2)
        buf_r = convolve_reverb(buf_r, ir, wet_ratio=0.2)

    # Normalize stereo
    peak = max(
        max((abs(s) for s in buf_l), default=1.0),
        max((abs(s) for s in buf_r), default=1.0),
    )
    if peak > 0:
        scale = 0.85 / peak
        buf_l = [s * scale for s in buf_l]
        buf_r = [s * scale for s in buf_r]

    # Interleave L/R for stereo WAV
    pcm = b"".join(
        _struct.pack("<hh",
                     max(-32767, min(32767, int(l * 32767))),
                     max(-32767, min(32767, int(r * 32767))))
        for l, r in zip(buf_l, buf_r)
    )

    # Write stereo WAV
    channels = 2
    bits = 16
    bps = bits // 8
    data_size = len(pcm)
    with open(filename, "wb") as f:
        f.write(b"RIFF")
        f.write(_struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(_struct.pack("<I", 16))
        f.write(_struct.pack("<H", 1))
        f.write(_struct.pack("<H", channels))
        f.write(_struct.pack("<I", sample_rate))
        f.write(_struct.pack("<I", sample_rate * channels * bps))
        f.write(_struct.pack("<H", channels * bps))
        f.write(_struct.pack("<H", bits))
        f.write(b"data")
        f.write(_struct.pack("<I", data_size))
        f.write(pcm)

    return filename
