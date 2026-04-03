"""Gallery — Pre-generated compositions for instant listening."""
from __future__ import annotations

import os
import streamlit as st

st.set_page_config(page_title="Gallery | Sacred Composer", layout="wide")

st.title("Gallery")
st.markdown("Pre-generated compositions showcasing different patterns and moods. "
            "Press play to listen — no generation wait required.")

# ---------------------------------------------------------------------------
# Gallery pieces — generated once and committed to the repo under gallery/
# ---------------------------------------------------------------------------
GALLERY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gallery")

PIECES = [
    {
        "title": "Fibonacci Nocturne in C minor",
        "file": "fibonacci_nocturne_c_minor.wav",
        "description": (
            "A gentle nocturne built from the Fibonacci sequence. "
            "The melody unfolds in organic spirals over a harmonic-series bass."
        ),
        "pattern": "fibonacci",
        "key": "C minor",
        "tempo": 66,
    },
    {
        "title": "Golden Spiral in A minor",
        "file": "golden_spiral_a_minor.wav",
        "description": (
            "Phi-derived pitch contours create an ever-expanding arc. "
            "Euclidean rhythms (5 in 8) give it a lilting asymmetry."
        ),
        "pattern": "golden_spiral",
        "key": "A minor",
        "tempo": 72,
    },
    {
        "title": "Logistic Dreams in G minor",
        "file": "logistic_dreams_g_minor.wav",
        "description": (
            "The logistic map at the edge of chaos. The piece begins in order "
            "and gradually fractures into complex, unpredictable motion."
        ),
        "pattern": "logistic",
        "key": "G minor",
        "tempo": 80,
    },
]


def _load_wav(filename: str) -> bytes | None:
    path = os.path.join(GALLERY_DIR, filename)
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return f.read()
    return None


# Check if gallery has been generated
if not os.path.isdir(GALLERY_DIR) or not any(f.endswith(".wav") for f in os.listdir(GALLERY_DIR)):
    st.warning("Gallery WAV files have not been generated yet. Click below to generate them.")
    if st.button("Generate gallery pieces", type="primary"):
        with st.spinner("Generating gallery compositions (this may take a minute)..."):
            from sacred_composer.builder import CompositionBuilder
            from sacred_composer.wav_renderer import render_wav

            os.makedirs(GALLERY_DIR, exist_ok=True)

            # Piece 1: Fibonacci Nocturne
            b = CompositionBuilder(key="C_minor", tempo=66, bars=8)
            b.melody(pattern="fibonacci", seed=0, rhythm_pattern="euclidean_5_8")
            b.bass(pattern="harmonic_series", rhythm_pattern="steady")
            p = b.build()
            p.render(os.path.join(GALLERY_DIR, "fibonacci_nocturne_c_minor.mid"))
            render_wav(p.score, os.path.join(GALLERY_DIR, "fibonacci_nocturne_c_minor.wav"), reverb=True)

            # Piece 2: Golden Spiral
            b = CompositionBuilder(key="A_minor", tempo=72, bars=8)
            b.melody(pattern="golden_spiral", seed=1, rhythm_pattern="euclidean_5_8")
            b.bass(pattern="harmonic_series", rhythm_pattern="steady")
            p = b.build()
            p.render(os.path.join(GALLERY_DIR, "golden_spiral_a_minor.mid"))
            render_wav(p.score, os.path.join(GALLERY_DIR, "golden_spiral_a_minor.wav"), reverb=True)

            # Piece 3: Logistic Dreams
            b = CompositionBuilder(key="G_minor", tempo=80, bars=8)
            b.melody(pattern="logistic", seed=0, rhythm_pattern="euclidean_7_12")
            b.bass(pattern="fibonacci", rhythm_pattern="euclidean_3_8")
            p = b.build()
            p.render(os.path.join(GALLERY_DIR, "logistic_dreams_g_minor.mid"))
            render_wav(p.score, os.path.join(GALLERY_DIR, "logistic_dreams_g_minor.wav"), reverb=True)

        st.success("Gallery generated! Refresh the page to listen.")
        st.rerun()
else:
    for piece in PIECES:
        wav_data = _load_wav(piece["file"])
        if wav_data:
            st.subheader(piece["title"])
            st.caption(f"Pattern: {piece['pattern']} | Key: {piece['key']} | Tempo: {piece['tempo']} BPM")
            st.markdown(piece["description"])
            st.audio(wav_data, format="audio/wav")
            st.divider()
        else:
            st.warning(f"Missing file: {piece['file']}")
