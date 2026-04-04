"""Sacred Composer — Pattern-based deterministic music composition.

Code as composition. Sacred patterns as source material.
"""

from sacred_composer.constants import (
    phi, golden_angle, fibonacci_intervals, sacred_numbers,
    PHI_INVERSE, FEIGENBAUM_DELTA,
    MIDI_MAX_VELOCITY, MIDI_PITCH_BEND_CENTER, MIDI_MIN_NOTE_DURATION,
    DEFAULT_TEMPO,
)
from sacred_composer.patterns import (
    FibonacciSequence,
    HarmonicSeries,
    InfinitySeries,
    EuclideanRhythm,
    CellularAutomata,
    PinkNoise,
    GoldenSpiral,
    LorenzAttractor,
    DigitsOf,
    SternBrocot,
    LogisticMap,
    Lindenmayer,
    MandelbrotBoundary,
    RosslerAttractor,
    CantorSet,
    ZipfDistribution,
    TextToMelody,
    DataPattern,
    CombinationTones,
    IChing,
    ThueMorse,
    PlanetaryRhythm,
    SieveScale,
)
from sacred_composer.mappers import to_pitch, to_pitch_microtonal, to_rhythm, to_dynamics, to_form
from sacred_composer.core import Note, Voice, Score, Composition, FormSection
from sacred_composer.combiners import layer, canon, phase, fractal_form
from sacred_composer.lilypond import render_lilypond
from sacred_composer.musicxml import render_musicxml
from sacred_composer.wav_renderer import render_wav
from sacred_composer.orchestration import (
    ORCHESTRA_DB, InstrumentProfile, Technique, TextureType,
    find_best_instruments, assign_instrument, suggest_doubling,
    render_orchestral_wav, TIMBRE_TARGETS,
)
from sacred_composer.bridge import score_to_performance_ir, voice_to_performance_notes
from sacred_composer.evaluate import evaluate_composition
from sacred_composer.constraints import (
    constrained_melody, enforce_range, smooth_leaps,
    add_tension_arc, improve_interval_distribution,
    add_phrase_endings, add_pitch_tension_arc, add_motivic_variation,
    smooth_direction, add_cadences, fix_seventh_resolution,
)
from sacred_composer.variation import (
    Motif, augment, diminish, invert, retrograde,
    expand_intervals, contract_intervals, fragment, liquidate,
    variation_distance, develop_phrase, apply_developing_variation,
)
from sacred_composer.builder import CompositionBuilder
from sacred_composer.optimizer import (
    SEARCH_SPACE, build_from_params, evaluate_fast,
    optimize, optimize_and_build,
)
from sacred_composer.harmony import (
    CHORD_GRAMMAR, Chord, roman_to_chord,
    generate_progression, voice_lead, melody_from_chords, bass_from_chords,
    HarmonicEngine,
)
from sacred_composer.world_music import (
    melakarta_scale, Raga, RAGA_PRESETS, tala_pattern, TALAS,
    maqam_scale, maqam_sayr, AJNAS, MAQAMAT,
    gamelan_to_midi, colotomic_pattern, balungan_elaborate,
    GAMELAN_TUNINGS, COLOTOMIC_STRUCTURES, TIMELINE_PATTERNS,
    cross_rhythm, polyrhythmic_texture,
    JAPANESE_SCALES, jo_ha_kyu_curve, apply_ma,
    kotekan_split, overtone_melody, KHOOMEI_PATTERNS,
)
from sacred_composer.adaptive import (
    GameState, ENVIRONMENT_SCALES, AdaptiveComposer,
    state_to_params, generate_soundtrack,
)
from sacred_composer.osc_bridge import (
    OSCServer, OSCSender, MIDIOutput, LivePerformer,
)
from sacred_composer.tension import (
    fifth_distance, surface_dissonance, tonal_distance, register_tension,
    compute_tension, tension_curve,
    target_curve_sonata, target_curve_arch, target_curve_ramp,
    shape_to_tension,
)
from sacred_composer.psychoacoustics import (
    information_content, surprise_ratio, expectation_score,
    FrissonEvent, plan_frisson_events, appoggiatura_pitches,
    voice_separation_score, parallel_motion_ratio,
    GrooveTemplate, GROOVE_TEMPLATES, phrase_ritardando,
    critical_bandwidth, plomp_levelt_roughness, sethares_dissonance,
    consonance_ranking, midi_to_freq,
    peak_end_score, earworm_score,
    PerceptualReport, analyze_perceptual,
)

__all__ = [
    # Constants
    "phi", "golden_angle", "fibonacci_intervals", "sacred_numbers",
    "PHI_INVERSE", "FEIGENBAUM_DELTA",
    "MIDI_MAX_VELOCITY", "MIDI_PITCH_BEND_CENTER", "MIDI_MIN_NOTE_DURATION",
    "DEFAULT_TEMPO",
    # Phase 1 patterns
    "FibonacciSequence", "HarmonicSeries", "InfinitySeries",
    "EuclideanRhythm", "CellularAutomata", "PinkNoise",
    # Phase 2 patterns
    "GoldenSpiral", "LorenzAttractor", "DigitsOf",
    "SternBrocot", "LogisticMap", "Lindenmayer",
    # Phase 3 patterns
    "MandelbrotBoundary", "RosslerAttractor", "CantorSet",
    "ZipfDistribution", "TextToMelody", "DataPattern",
    # Spectral patterns
    "CombinationTones",
    # Historical algorithm patterns
    "IChing", "ThueMorse", "PlanetaryRhythm", "SieveScale",
    # Mappers
    "to_pitch", "to_pitch_microtonal", "to_rhythm", "to_dynamics", "to_form",
    # Core
    "Note", "Voice", "Score", "Composition", "FormSection",
    # Combiners
    "layer", "canon", "phase", "fractal_form",
    # Renderers
    "render_lilypond", "render_musicxml", "render_wav", "render_orchestral_wav",
    # Orchestration
    "ORCHESTRA_DB", "InstrumentProfile", "Technique", "TextureType",
    "find_best_instruments", "assign_instrument", "suggest_doubling",
    "TIMBRE_TARGETS",
    # Bridge
    "score_to_performance_ir", "voice_to_performance_notes",
    # Evaluation
    "evaluate_composition",
    # Constraints
    "constrained_melody", "enforce_range", "smooth_leaps",
    "add_tension_arc", "improve_interval_distribution",
    # Variation (developing variation)
    "Motif", "augment", "diminish", "invert", "retrograde",
    "expand_intervals", "contract_intervals", "fragment", "liquidate",
    "variation_distance", "develop_phrase", "apply_developing_variation",
    # Builder
    "CompositionBuilder",
    # Optimizer
    "SEARCH_SPACE", "build_from_params", "evaluate_fast",
    "optimize", "optimize_and_build",
    # Harmony
    "CHORD_GRAMMAR", "Chord", "roman_to_chord",
    "generate_progression", "voice_lead", "melody_from_chords", "bass_from_chords",
    "HarmonicEngine",
    # World Music
    "melakarta_scale", "Raga", "RAGA_PRESETS", "tala_pattern", "TALAS",
    "maqam_scale", "maqam_sayr", "AJNAS", "MAQAMAT",
    "gamelan_to_midi", "colotomic_pattern", "balungan_elaborate",
    "GAMELAN_TUNINGS", "COLOTOMIC_STRUCTURES", "TIMELINE_PATTERNS",
    "cross_rhythm", "polyrhythmic_texture",
    "JAPANESE_SCALES", "jo_ha_kyu_curve", "apply_ma",
    "kotekan_split", "overtone_melody", "KHOOMEI_PATTERNS",
    # Tension
    "fifth_distance", "surface_dissonance", "tonal_distance", "register_tension",
    "compute_tension", "tension_curve",
    "target_curve_sonata", "target_curve_arch", "target_curve_ramp",
    "shape_to_tension",
    # Psychoacoustics
    "information_content", "surprise_ratio", "expectation_score",
    "FrissonEvent", "plan_frisson_events", "appoggiatura_pitches",
    "voice_separation_score", "parallel_motion_ratio",
    "GrooveTemplate", "GROOVE_TEMPLATES", "phrase_ritardando",
    "critical_bandwidth", "plomp_levelt_roughness", "sethares_dissonance",
    "consonance_ranking", "midi_to_freq",
    "peak_end_score", "earworm_score",
    "PerceptualReport", "analyze_perceptual",
    # Adaptive
    "GameState", "ENVIRONMENT_SCALES", "AdaptiveComposer",
    "state_to_params", "generate_soundtrack",
    # OSC Bridge
    "OSCServer", "OSCSender", "MIDIOutput", "LivePerformer",
]
