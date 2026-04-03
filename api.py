"""Sacred Composer — Composition-as-a-Service REST API.

Generate sacred-geometry-based music via HTTP. Targets: meditation apps,
game studios, film composers, hold music systems.

Run with:
    python api.py
    uvicorn api:app --reload
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from sacred_composer.builder import CompositionBuilder
from sacred_composer.adaptive import (
    GameState, AdaptiveComposer, ENVIRONMENT_SCALES, generate_soundtrack,
)
from sacred_composer.constants import SCALES, NOTE_NAMES
from sacred_composer.core import Composition

# ---------------------------------------------------------------------------
# Storage for generated compositions
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(tempfile.gettempdir()) / "sacred_composer_api"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory registry: composition_id -> Composition object
_compositions: dict[str, Composition] = {}


def _store(piece: Composition) -> str:
    """Persist a Composition to disk (MIDI + WAV) and return its UUID."""
    cid = uuid.uuid4().hex[:12]
    _compositions[cid] = piece
    piece.render(str(OUTPUT_DIR / f"{cid}.mid"))
    try:
        piece.render(str(OUTPUT_DIR / f"{cid}.wav"))
    except Exception:
        pass  # WAV renderer may not be available
    return cid


def _get_composition(cid: str) -> Composition:
    if cid not in _compositions:
        raise HTTPException(status_code=404, detail=f"Composition '{cid}' not found")
    return _compositions[cid]


def _get_file(cid: str, ext: str) -> Path:
    path = OUTPUT_DIR / f"{cid}.{ext}"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{ext.upper()} file not found for '{cid}'")
    return path


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ComposeRequest(BaseModel):
    key: str = "C_minor"
    tempo: int = Field(72, ge=20, le=300)
    bars: int = Field(48, ge=4, le=1024)
    melody_pattern: str = "infinity_series"
    bass_pattern: str = "harmonic_series"
    rhythm: str = "euclidean_5_8"
    seed: int = 0
    title: str = "Sacred Composition"
    use_harmony: bool = False
    consciousness_state: Optional[str] = None


class AdaptiveStatePoint(BaseModel):
    timestamp: float = Field(..., ge=0, description="Beat timestamp")
    danger: float = Field(0.0, ge=0, le=1)
    energy: float = Field(0.5, ge=0, le=1)
    environment: str = "forest"
    time_of_day: float = Field(12.0, ge=0, le=24)
    health: float = Field(1.0, ge=0, le=1)
    speed: float = Field(0.5, ge=0, le=1)


class AdaptiveRequest(BaseModel):
    states: list[AdaptiveStatePoint]
    chunk_beats: int = Field(8, ge=4, le=64)
    seed: int = 42


class ComposeResponse(BaseModel):
    id: str
    title: str
    notes: int
    duration_sec: float
    midi_url: str
    wav_url: str


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sacred Composer API",
    description="Composition-as-a-service powered by sacred geometry patterns.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _response(cid: str, piece: Composition) -> ComposeResponse:
    info = piece.info()
    return ComposeResponse(
        id=cid,
        title=info["title"],
        notes=info["total_notes"],
        duration_sec=round(info["duration_seconds"], 2),
        midi_url=f"/compose/{cid}/midi",
        wav_url=f"/compose/{cid}/wav",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/compose", response_model=ComposeResponse)
async def compose(request: ComposeRequest):
    """Generate a composition from parameters."""
    # If a consciousness state is provided, use that preset directly
    if request.consciousness_state:
        builder = CompositionBuilder(title=request.title)
        builder.consciousness(request.consciousness_state)
    else:
        builder = CompositionBuilder(
            key=request.key,
            tempo=request.tempo,
            bars=request.bars,
            title=request.title,
        )
        builder.melody(
            pattern=request.melody_pattern,
            rhythm_pattern=request.rhythm,
            seed=request.seed,
        )
        builder.bass(
            pattern=request.bass_pattern,
            seed=request.seed + 10,
        )

    if request.use_harmony:
        builder.harmony(seed=request.seed)

    piece = builder.build()
    cid = _store(piece)
    return _response(cid, piece)


@app.post("/compose/consciousness/{state}", response_model=ComposeResponse)
async def compose_consciousness(state: str, seed: int = 42):
    """Quick preset generation from a consciousness state."""
    available = CompositionBuilder.available_states()
    if state not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown state '{state}'. Available: {available}",
        )
    builder = CompositionBuilder(title=f"{state.replace('_', ' ').title()} Music")
    builder.consciousness(state)
    builder.harmony(seed=seed)
    piece = builder.build()
    cid = _store(piece)
    return _response(cid, piece)


@app.post("/compose/adaptive", response_model=ComposeResponse)
async def compose_adaptive(request: AdaptiveRequest):
    """Generate an adaptive soundtrack from a sequence of game states."""
    if not request.states:
        raise HTTPException(status_code=400, detail="At least one state is required")

    state_pairs: list[tuple[float, GameState]] = [
        (
            s.timestamp,
            GameState(
                danger=s.danger,
                energy=s.energy,
                environment=s.environment,
                time_of_day=s.time_of_day,
                health=s.health,
                speed=s.speed,
            ),
        )
        for s in request.states
    ]
    state_pairs.sort(key=lambda x: x[0])

    piece = generate_soundtrack(
        states=state_pairs,
        chunk_beats=request.chunk_beats,
        seed=request.seed,
    )
    cid = _store(piece)
    return _response(cid, piece)


@app.get("/compose/{cid}/midi")
async def download_midi(cid: str):
    """Download the MIDI file for a composition."""
    _get_composition(cid)
    path = _get_file(cid, "mid")
    return FileResponse(path, media_type="audio/midi", filename=f"{cid}.mid")


@app.get("/compose/{cid}/wav")
async def download_wav(cid: str):
    """Download the WAV file for a composition."""
    _get_composition(cid)
    path = _get_file(cid, "wav")
    return FileResponse(path, media_type="audio/wav", filename=f"{cid}.wav")


@app.get("/compose/{cid}/json")
async def get_visualization_json(cid: str):
    """Get visualization JSON for a composition."""
    piece = _get_composition(cid)
    return piece.to_visualization_json()


@app.get("/patterns")
async def list_patterns():
    """List available pattern generators."""
    return {
        "patterns": list(CompositionBuilder.PATTERN_GENERATORS.keys()),
    }


@app.get("/scales")
async def list_scales():
    """List available scales and root notes."""
    return {
        "scale_types": list(SCALES.keys()),
        "root_notes": list(NOTE_NAMES.keys()),
        "usage": "Combine as '{root}_{scale_type}', e.g. 'C_minor', 'F#_dorian'",
    }


@app.get("/consciousness")
async def list_consciousness():
    """List available consciousness presets with their parameters."""
    return {
        "states": {
            name: {k: v for k, v in preset.items()}
            for name, preset in CompositionBuilder.CONSCIOUSNESS_PRESETS.items()
        },
    }


@app.get("/environments")
async def list_environments():
    """List available environment-to-scale mappings for adaptive composition."""
    return {
        "environments": ENVIRONMENT_SCALES,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
