"""Sacred Composer — Interactive Streamlit Playground.

Launch with:  streamlit run playground.py
"""
from __future__ import annotations

import json
import os
import tempfile

import streamlit as st

# ---------------------------------------------------------------------------
# Imports from sacred_composer
# ---------------------------------------------------------------------------
from sacred_composer.constants import SCALES, NOTE_NAMES
from sacred_composer.builder import CompositionBuilder
from sacred_composer.optimizer import evaluate_fast
from sacred_composer.wav_renderer import render_wav
from sacred_composer.adaptive import (
    GameState, ENVIRONMENT_SCALES, AdaptiveComposer,
)
from sacred_composer.patterns import DataPattern
from sacred_composer.mappers import to_pitch, to_rhythm, to_dynamics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
ROOTS = list(NOTE_NAMES.keys())
SCALE_TYPES = list(SCALES.keys())
PATTERN_NAMES = list(CompositionBuilder.PATTERN_GENERATORS.keys())
RHYTHM_PATTERNS = ["euclidean_3_8", "euclidean_5_8", "euclidean_7_12", "steady"]
CONSCIOUSNESS_STATES = CompositionBuilder.available_states()

_TMP_DIR = tempfile.mkdtemp(prefix="sacred_pg_")


def _key_name(root: str, scale_type: str) -> str:
    return f"{root}_{scale_type}"


@st.cache_data(show_spinner="Composing...")
def _compose(
    key: str, tempo: int, bars: int,
    melody_pat: str, melody_seed: int,
    bass_pat: str, rhythm_pat: str,
    harmony: bool,
) -> tuple[dict, bytes, bytes, dict, float]:
    """Build a composition and return (info, midi_bytes, wav_bytes, viz_json, score)."""
    builder = CompositionBuilder(key=key, tempo=tempo, bars=bars)
    builder.melody(pattern=melody_pat, seed=melody_seed, rhythm_pattern=rhythm_pat)
    builder.bass(pattern=bass_pat, rhythm_pattern=rhythm_pat)
    if harmony:
        builder.harmony()
    piece = builder.build()

    midi_path = os.path.join(_TMP_DIR, "out.mid")
    wav_path = os.path.join(_TMP_DIR, "out.wav")
    piece.render(midi_path)
    render_wav(piece.score, wav_path, reverb=True)

    with open(midi_path, "rb") as f:
        midi_bytes = f.read()
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    info = piece.info()
    viz = piece.to_visualization_json()
    score = evaluate_fast(piece)
    return info, midi_bytes, wav_bytes, viz, score


@st.cache_data(show_spinner="Composing consciousness preset...")
def _compose_consciousness(state: str) -> tuple[dict, bytes, bytes, dict, float]:
    builder = CompositionBuilder(title=f"Consciousness: {state}")
    builder.consciousness(state)
    piece = builder.build()

    midi_path = os.path.join(_TMP_DIR, "cons.mid")
    wav_path = os.path.join(_TMP_DIR, "cons.wav")
    piece.render(midi_path)
    render_wav(piece.score, wav_path, reverb=True)

    with open(midi_path, "rb") as f:
        midi_bytes = f.read()
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    return piece.info(), midi_bytes, wav_bytes, piece.to_visualization_json(), evaluate_fast(piece)


@st.cache_data(show_spinner="Sonifying data...")
def _sonify(data_str: str, key: str, tempo: int) -> tuple[dict, bytes, bytes]:
    values = [float(x.strip()) for x in data_str.replace("\n", ",").split(",") if x.strip()]
    dp = DataPattern(values, name="user_data")
    n = max(len(values), 32)
    raw = dp.generate(n)
    pitches = to_pitch(raw, scale=key, octave_range=(4, 5), strategy="normalize")
    durations = to_rhythm(raw[:n], base_duration=0.5, strategy="proportional")
    velocities = to_dynamics(raw[:n], velocity_range=(50, 100))

    from sacred_composer.core import Composition
    piece = Composition(tempo=tempo, title="Data Sonification")
    piece.add_voice("data", pitches, durations, velocities)

    midi_path = os.path.join(_TMP_DIR, "sonify.mid")
    wav_path = os.path.join(_TMP_DIR, "sonify.wav")
    piece.render(midi_path)
    render_wav(piece.score, wav_path, reverb=True)

    with open(midi_path, "rb") as f:
        midi_bytes = f.read()
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()
    return piece.info(), midi_bytes, wav_bytes


@st.cache_data(show_spinner="Generating adaptive soundtrack...")
def _adaptive(danger: float, energy: float, environment: str, bars: int) -> tuple[dict, bytes, bytes]:
    state = GameState(danger=danger, energy=energy, environment=environment)
    ac = AdaptiveComposer(seed=42)
    ac.update(state)
    piece = ac.render_chunk(beats=bars * 4)

    midi_path = os.path.join(_TMP_DIR, "adaptive.mid")
    wav_path = os.path.join(_TMP_DIR, "adaptive.wav")
    piece.render(midi_path)
    render_wav(piece.score, wav_path, reverb=True)

    with open(midi_path, "rb") as f:
        midi_bytes = f.read()
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()
    return piece.info(), midi_bytes, wav_bytes


def _show_results(info: dict, midi_bytes: bytes, wav_bytes: bytes,
                  viz: dict | None = None, score: float | None = None):
    """Render the results panel."""
    col1, col2, col3 = st.columns(3)
    col1.metric("Notes", info.get("total_notes", "?"))
    col2.metric("Duration", f"{info.get('duration_seconds', 0):.1f}s")
    col3.metric("Voices", info.get("voices", "?"))

    if score is not None:
        st.progress(min(score / 100.0, 1.0), text=f"Evaluation score: {score:.1f} / 100")

    st.subheader("Listen")
    st.audio(wav_bytes, format="audio/wav")

    st.download_button("Download MIDI", data=midi_bytes, file_name="sacred_composer.mid",
                       mime="audio/midi")

    if viz:
        with st.expander("Visualization JSON"):
            st.json(viz)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Sacred Composer Playground", layout="wide")
st.title("Sacred Composer Playground")

tab_compose, tab_conscious, tab_sonify, tab_adaptive = st.tabs(
    ["Compose", "Consciousness", "Sonification", "Adaptive"]
)

# ===========================================================================
# Tab 1 — Compose
# ===========================================================================
with tab_compose:
    with st.sidebar:
        st.header("Parameters")
        root = st.selectbox("Root note", ROOTS, index=ROOTS.index("C"))
        scale_type = st.selectbox("Scale", SCALE_TYPES, index=0)
        tempo = st.slider("Tempo (BPM)", 40, 180, 72)
        bars = st.slider("Bars", 8, 128, 48)
        melody_pat = st.selectbox("Melody pattern", PATTERN_NAMES, index=0)
        melody_seed = st.slider("Melody seed", 0, 100, 0)
        bass_pat = st.selectbox("Bass pattern", PATTERN_NAMES,
                                index=PATTERN_NAMES.index("harmonic_series"))
        rhythm_pat = st.selectbox("Rhythm pattern", RHYTHM_PATTERNS, index=1)
        harmony = st.checkbox("Harmony mode", value=False)
        generate = st.button("Generate", type="primary", use_container_width=True)

    if generate:
        key = _key_name(root, scale_type)
        info, midi_bytes, wav_bytes, viz, score = _compose(
            key, tempo, bars, melody_pat, melody_seed, bass_pat, rhythm_pat, harmony
        )
        st.subheader(f"{info.get('title', 'Composition')}")
        _show_results(info, midi_bytes, wav_bytes, viz, score)
    else:
        st.info("Configure parameters in the sidebar and press **Generate**.")

# ===========================================================================
# Tab 2 — Consciousness
# ===========================================================================
with tab_conscious:
    st.markdown("Select a consciousness preset to generate music tuned for a specific mental state.")
    descriptions = {
        "deep_sleep": "Very slow, narrow range, quiet — designed for deep sleep induction.",
        "meditation": "Phrygian mode, gentle motion — aids meditative focus.",
        "relaxation": "Major key, moderate pace — calming background music.",
        "flow": "Pentatonic, steady movement — supports creative flow state.",
        "focus": "Dorian mode, rhythmic drive — concentration music.",
        "energy": "Fast, wide range, loud — energising and uplifting.",
    }
    chosen = st.selectbox("Consciousness state", CONSCIOUSNESS_STATES)
    st.caption(descriptions.get(chosen, ""))
    if st.button("Generate preset", key="gen_conscious", type="primary"):
        info, midi_bytes, wav_bytes, viz, score = _compose_consciousness(chosen)
        _show_results(info, midi_bytes, wav_bytes, viz, score)

# ===========================================================================
# Tab 3 — Sonification
# ===========================================================================
with tab_sonify:
    st.markdown("Paste numeric data (comma or newline separated) and hear it as music.")
    data_str = st.text_area("Data values", value="14.0, 14.1, 14.3, 14.8, 15.2, 15.9, 16.4, 15.8, 15.1",
                            height=120)
    col_a, col_b = st.columns(2)
    son_key = col_a.selectbox("Key", [f"C_{s}" for s in SCALE_TYPES], index=0, key="son_key")
    son_tempo = col_b.slider("Tempo", 40, 180, 80, key="son_tempo")
    if st.button("Sonify", key="gen_sonify", type="primary"):
        try:
            info, midi_bytes, wav_bytes = _sonify(data_str, son_key, son_tempo)
            _show_results(info, midi_bytes, wav_bytes)
        except Exception as exc:
            st.error(f"Could not parse data: {exc}")

# ===========================================================================
# Tab 4 — Adaptive
# ===========================================================================
with tab_adaptive:
    st.markdown("Simulate game-state changes and hear the music adapt in real time.")
    col1, col2 = st.columns(2)
    danger = col1.slider("Danger", 0.0, 1.0, 0.0, 0.05)
    energy = col2.slider("Energy", 0.0, 1.0, 0.5, 0.05)
    environment = st.selectbox("Environment", list(ENVIRONMENT_SCALES.keys()))
    ad_bars = st.slider("Bars to generate", 4, 32, 8, key="ad_bars")
    if st.button("Generate adaptive chunk", key="gen_adaptive", type="primary"):
        info, midi_bytes, wav_bytes = _adaptive(danger, energy, environment, ad_bars)
        _show_results(info, midi_bytes, wav_bytes)
