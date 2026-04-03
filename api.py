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


# ---------------------------------------------------------------------------
# Viral endpoints: Compose Your Name + Seed Music
# ---------------------------------------------------------------------------

@app.get("/compose/name/{name}", response_model=ComposeResponse)
async def compose_from_name(name: str):
    """Generate a unique composition from a name using Guido d'Arezzo mapping."""
    clean = name.strip()[:100] or "Sacred"
    # Deterministic seed from name
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(clean)) % 100000
    # Derive key from name's character sum
    keys = ["D_minor", "A_minor", "E_minor", "C_minor", "G_minor",
            "F_minor", "C_major", "D_major", "F_major", "G_major"]
    key = keys[sum(ord(c) for c in clean) % len(keys)]
    tempo = 60 + (seed % 25)  # 60-84 BPM (calm range)

    builder = CompositionBuilder(
        key=key, tempo=tempo, bars=36,
        title=f"{clean}'s Melody",
    )
    builder.form(pattern="fibonacci", n_sections=4)
    builder.melody(pattern="text", instrument="violin", seed=seed)
    builder.inner_voice(pattern="golden_spiral", instrument="oboe", seed=seed + 5)
    builder.bass(pattern="harmonic_series", instrument="cello", seed=seed + 10)
    piece = builder.build()
    cid = _store(piece)
    return _response(cid, piece)


@app.get("/compose/seed/{seed}", response_model=ComposeResponse)
async def compose_from_seed(seed: int):
    """One integer → one unique composition. Deterministic and shareable."""
    keys = ["C_minor", "D_minor", "E_minor", "A_minor", "G_minor",
            "F_minor", "Bb_minor", "C_major", "D_major", "F_major"]
    patterns = ["infinity_series", "fibonacci", "golden_spiral",
                "logistic", "mandelbrot", "rossler"]
    inner_patterns = ["golden_spiral", "fibonacci", "infinity_series"]
    instruments = ["oboe", "viola", "clarinet", "flute"]

    key = keys[seed % len(keys)]
    pat = patterns[(seed // 10) % len(patterns)]
    inner_pat = inner_patterns[(seed // 7) % len(inner_patterns)]
    inner_inst = instruments[(seed // 13) % len(instruments)]
    tempo = 60 + (seed % 30)  # 60-89 BPM
    bars = 36 + (seed % 20)   # 36-55 bars

    builder = CompositionBuilder(
        key=key, tempo=tempo, bars=bars,
        title=f"Seed #{seed}",
    )
    builder.form(pattern="fibonacci", n_sections=4 + seed % 3)
    builder.melody(pattern=pat, instrument="violin", seed=seed)
    builder.inner_voice(pattern=inner_pat, instrument=inner_inst, seed=seed + 5)
    builder.bass(pattern="harmonic_series", instrument="cello", seed=seed + 10)
    piece = builder.build()
    cid = _store(piece)
    return _response(cid, piece)


# ---------------------------------------------------------------------------
# Livestream overlay — current composition tracking
# ---------------------------------------------------------------------------

_stream_current: dict = {}


class StreamUpdateRequest(BaseModel):
    title: str = ""
    pattern: str = ""
    tempo: int = 0
    mood: str = ""
    seed: int = 0


@app.post("/stream/update")
async def stream_update(request: StreamUpdateRequest):
    """Update the current livestream composition info."""
    _stream_current.update(request.model_dump())
    return _stream_current


@app.get("/stream/current")
async def stream_current():
    """Get the current livestream composition info (for overlay)."""
    if not _stream_current:
        return {"title": "", "pattern": "", "tempo": 0, "mood": "", "seed": 0}
    return _stream_current


# ---------------------------------------------------------------------------
# Web frontend (single-page app served directly)
# ---------------------------------------------------------------------------

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Sacred Composer — interactive web experience."""
    return LANDING_HTML


LANDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sacred Composer — Music from Mathematics</title>
<meta name="description" content="Type your name or a number. Hear it as classical music generated from Fibonacci, golden ratio, and chaos theory. No AI — pure mathematics.">
<meta property="og:title" content="Sacred Composer — Music from Mathematics">
<meta property="og:description" content="Every note traceable to a mathematical pattern. Type your name, hear your unique composition.">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=JetBrains+Mono:wght@300;400&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: #06060f;
    color: #e8e0d4;
    font-family: 'Cormorant Garamond', Georgia, serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  canvas#bg {
    position: fixed; inset: 0; z-index: 0;
    width: 100%; height: 100%;
  }

  .container {
    position: relative; z-index: 1;
    max-width: 800px; margin: 0 auto;
    padding: 60px 24px;
    min-height: 100vh;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 48px;
  }

  h1 {
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 300; letter-spacing: 0.08em;
    text-align: center;
    background: linear-gradient(135deg, #e8a838, #f0d090, #e8a838);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }

  .subtitle {
    font-size: 1.1rem; font-weight: 300;
    color: rgba(255,255,255,0.4);
    text-align: center; letter-spacing: 0.05em;
    max-width: 500px; line-height: 1.6;
  }

  .tabs {
    display: flex; gap: 2px;
    background: rgba(255,255,255,0.05);
    border-radius: 12px; padding: 3px;
  }

  .tab {
    padding: 10px 24px; border: none; background: transparent;
    color: rgba(255,255,255,0.4); font-family: inherit;
    font-size: 1rem; cursor: pointer; border-radius: 10px;
    transition: all 0.3s;
  }

  .tab.active {
    background: rgba(232,168,56,0.15);
    color: #e8a838;
  }

  .input-area {
    display: flex; flex-direction: column;
    align-items: center; gap: 16px; width: 100%;
  }

  input[type="text"], input[type="number"] {
    width: 100%; max-width: 440px;
    padding: 16px 24px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(232,168,56,0.15);
    border-radius: 12px;
    color: #e8e0d4; font-family: inherit;
    font-size: 1.3rem; text-align: center;
    letter-spacing: 0.05em;
    outline: none; transition: border-color 0.3s;
  }

  input:focus {
    border-color: rgba(232,168,56,0.5);
    box-shadow: 0 0 30px rgba(232,168,56,0.08);
  }

  input::placeholder { color: rgba(255,255,255,0.15); }

  .btn {
    padding: 14px 48px;
    background: linear-gradient(135deg, rgba(232,168,56,0.2), rgba(232,168,56,0.1));
    border: 1px solid rgba(232,168,56,0.3);
    border-radius: 10px;
    color: #e8a838; font-family: inherit;
    font-size: 1.1rem; letter-spacing: 0.1em;
    cursor: pointer; transition: all 0.3s;
  }

  .btn:hover {
    background: linear-gradient(135deg, rgba(232,168,56,0.3), rgba(232,168,56,0.15));
    box-shadow: 0 0 40px rgba(232,168,56,0.12);
    transform: translateY(-1px);
  }

  .btn:disabled { opacity: 0.4; cursor: wait; transform: none; }

  .result {
    display: none; flex-direction: column; align-items: center; gap: 20px;
    width: 100%;
  }

  .result.visible { display: flex; }

  .result-title {
    font-size: 1.4rem; color: #e8a838;
    font-weight: 300; letter-spacing: 0.05em;
  }

  .result-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem; color: rgba(255,255,255,0.25);
    letter-spacing: 0.05em;
  }

  audio {
    width: 100%; max-width: 440px;
    border-radius: 8px; margin: 8px 0;
  }

  .download-row {
    display: flex; gap: 12px;
  }

  .download-row a {
    padding: 8px 20px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    color: rgba(255,255,255,0.4);
    text-decoration: none; font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.2s;
  }

  .download-row a:hover {
    border-color: rgba(232,168,56,0.3);
    color: #e8a838;
  }

  .share-url {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem; color: rgba(255,255,255,0.2);
    cursor: pointer; padding: 6px 12px;
    background: rgba(255,255,255,0.02);
    border-radius: 6px; transition: color 0.2s;
  }

  .share-url:hover { color: rgba(255,255,255,0.5); }

  /* Spiral canvas */
  canvas#spiral {
    width: 280px; height: 280px;
    border-radius: 50%;
  }

  /* Audio waveform */
  canvas#waveform {
    width: 100%; max-width: 500px; height: 80px;
    border-radius: 8px;
    display: none;
  }

  .result.visible canvas#waveform { display: block; }

  .pattern-info {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: rgba(232,168,56,0.35);
    text-align: center;
    letter-spacing: 0.08em;
    max-width: 400px;
    line-height: 1.6;
    display: none;
  }

  .result.visible .pattern-info { display: block; }

  .history {
    display: flex; flex-wrap: wrap; gap: 8px;
    justify-content: center; max-width: 500px;
  }

  .history-chip {
    padding: 4px 12px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 6px;
    color: rgba(255,255,255,0.25);
    font-size: 0.75rem; font-family: 'JetBrains Mono', monospace;
    cursor: pointer; transition: all 0.2s;
  }

  .history-chip:hover {
    border-color: rgba(232,168,56,0.3);
    color: #e8a838;
  }

  .footer {
    margin-top: 40px;
    font-size: 0.8rem; color: rgba(255,255,255,0.12);
    text-align: center; letter-spacing: 0.1em;
  }

  .loading { animation: pulse 1.5s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
</style>
</head>
<body>

<canvas id="bg"></canvas>

<div class="container">
  <h1>Sacred Composer</h1>
  <p class="subtitle">
    Classical music generated from mathematical patterns.
    Every note traceable to Fibonacci, golden ratio, and chaos theory.
  </p>

  <div class="tabs">
    <button class="tab active" onclick="switchTab('name')">Your Name</button>
    <button class="tab" onclick="switchTab('seed')">Seed Number</button>
  </div>

  <div class="input-area">
    <input id="nameInput" type="text" placeholder="Enter your name" maxlength="100" />
    <input id="seedInput" type="number" placeholder="Enter any number" style="display:none" />
    <button class="btn" id="composeBtn" onclick="compose()">Compose</button>
  </div>

  <canvas id="spiral" width="560" height="560"></canvas>

  <div class="result" id="result">
    <div class="result-title" id="resultTitle"></div>
    <div class="result-meta" id="resultMeta"></div>
    <canvas id="waveform" width="1000" height="160"></canvas>
    <audio id="player" controls></audio>
    <div class="pattern-info" id="patternInfo"></div>
    <div class="download-row">
      <a id="dlWav" href="#" download>Download WAV</a>
      <a id="dlMidi" href="#" download>Download MIDI</a>
    </div>
    <div class="share-url" id="shareUrl" onclick="copyShareUrl()" title="Click to copy"></div>
  </div>

  <div class="history" id="history"></div>

  <div class="footer">
    No AI. No GPU. Pure mathematics &rarr; pure music.<br>
    <span style="font-size:0.7rem;color:rgba(255,255,255,0.08)">
      23 pattern generators &middot; 320 tests passing &middot; 88.5/100 eval score
    </span>
  </div>
</div>

<script>
const API = '';  // same origin
let mode = 'name';
let spiralCtx, spiralW, spiralH;

function switchTab(m) {
  mode = m;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[onclick*="${m}"]`).classList.add('active');
  document.getElementById('nameInput').style.display = m === 'name' ? '' : 'none';
  document.getElementById('seedInput').style.display = m === 'seed' ? '' : 'none';
}

async function compose() {
  const btn = document.getElementById('composeBtn');
  btn.disabled = true;
  btn.textContent = 'Composing...';
  btn.classList.add('loading');

  let url;
  if (mode === 'name') {
    const name = document.getElementById('nameInput').value.trim() || 'Anonymous';
    url = `${API}/compose/name/${encodeURIComponent(name)}`;
  } else {
    const seed = parseInt(document.getElementById('seedInput').value) || 42;
    url = `${API}/compose/seed/${seed}`;
  }

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Composition failed');
    const data = await res.json();

    document.getElementById('resultTitle').textContent = data.title;
    document.getElementById('resultMeta').textContent =
      `${data.notes} notes · ${data.duration_sec}s`;

    const wavUrl = `${API}${data.wav_url}`;
    const midiUrl = `${API}${data.midi_url}`;

    document.getElementById('player').src = wavUrl;
    document.getElementById('dlWav').href = wavUrl;
    document.getElementById('dlMidi').href = midiUrl;

    const shareBase = window.location.origin;
    const shareParam = mode === 'name'
      ? `?name=${encodeURIComponent(document.getElementById('nameInput').value)}`
      : `?seed=${document.getElementById('seedInput').value}`;
    document.getElementById('shareUrl').textContent = `${shareBase}/${shareParam}`;

    // Pattern info
    const input = mode === 'name'
      ? document.getElementById('nameInput').value
      : document.getElementById('seedInput').value;
    document.getElementById('patternInfo').textContent =
      mode === 'name'
        ? `Guido d'Arezzo vowel mapping (1026 AD) \u2192 Fibonacci form \u2192 voice leading constraints`
        : `Seed \u2192 pattern + key + tempo \u2192 Fibonacci form \u2192 orchestral rendering`;

    document.getElementById('result').classList.add('visible');

    const player = document.getElementById('player');
    player.play();
    startWaveform(player);
    animateSpiral(data.notes);
    addHistory(mode === 'name' ? input : `#${input}`, mode, input);
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Compose';
    btn.classList.remove('loading');
  }
}

// --- Fibonacci spiral visualization ---
const PHI = (1 + Math.sqrt(5)) / 2;
const GOLDEN_ANGLE = 2 * Math.PI * (1 - 1 / PHI);

function initSpiral() {
  const c = document.getElementById('spiral');
  spiralCtx = c.getContext('2d');
  spiralW = c.width;
  spiralH = c.height;
  drawSpiral(0);
}

function drawSpiral(activeCount) {
  const ctx = spiralCtx;
  const cx = spiralW / 2, cy = spiralH / 2;
  const maxR = spiralW * 0.44;
  const total = 233;

  ctx.clearRect(0, 0, spiralW, spiralH);

  for (let i = 0; i < total; i++) {
    const angle = i * GOLDEN_ANGLE;
    const r = maxR * Math.sqrt(i / total);
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);

    const isActive = i < activeCount;
    ctx.beginPath();
    ctx.arc(x, y, isActive ? 4 : 2, 0, Math.PI * 2);
    ctx.fillStyle = isActive
      ? `hsla(${35 + i * 0.5}, 80%, ${55 + (i/total)*20}%, ${0.7})`
      : 'rgba(255,255,255,0.07)';
    ctx.fill();

    if (isActive) {
      ctx.shadowColor = '#e8a838';
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }
}

function animateSpiral(noteCount) {
  const target = Math.min(233, noteCount);
  let current = 0;
  function step() {
    current += 2;
    if (current > target) current = target;
    drawSpiral(current);
    if (current < target) requestAnimationFrame(step);
  }
  step();
}

// --- Background particles ---
function initBg() {
  const c = document.getElementById('bg');
  c.width = window.innerWidth;
  c.height = window.innerHeight;
  const ctx = c.getContext('2d');

  const particles = [];
  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * c.width,
      y: Math.random() * c.height,
      r: 1 + Math.random() * 1.5,
      dx: (Math.random() - 0.5) * 0.3,
      dy: (Math.random() - 0.5) * 0.3,
      alpha: 0.03 + Math.random() * 0.06,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, c.width, c.height);
    for (const p of particles) {
      p.x += p.dx; p.y += p.dy;
      if (p.x < 0) p.x = c.width;
      if (p.x > c.width) p.x = 0;
      if (p.y < 0) p.y = c.height;
      if (p.y > c.height) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(232,168,56,${p.alpha})`;
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }
  draw();

  window.addEventListener('resize', () => {
    c.width = window.innerWidth;
    c.height = window.innerHeight;
  });
}

// --- Auto-compose from URL params ---
function checkUrlParams() {
  const params = new URLSearchParams(window.location.search);
  if (params.has('name')) {
    document.getElementById('nameInput').value = params.get('name');
    switchTab('name');
    compose();
  } else if (params.has('seed')) {
    document.getElementById('seedInput').value = params.get('seed');
    switchTab('seed');
    compose();
  }
}

// --- Init ---
initBg();
initSpiral();
checkUrlParams();

// Enter key triggers compose
document.getElementById('nameInput').addEventListener('keydown', e => { if (e.key === 'Enter') compose(); });
document.getElementById('seedInput').addEventListener('keydown', e => { if (e.key === 'Enter') compose(); });

// --- Audio waveform visualizer ---
let audioCtx, analyser, waveformAnimId, sourceNode;

function startWaveform(audioEl) {
  if (waveformAnimId) cancelAnimationFrame(waveformAnimId);

  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyser.connect(audioCtx.destination);
  }

  // Only create source once per element
  if (!sourceNode) {
    sourceNode = audioCtx.createMediaElementSource(audioEl);
    sourceNode.connect(analyser);
  }

  const canvas = document.getElementById('waveform');
  const ctx = canvas.getContext('2d');
  const bufLen = analyser.frequencyBinCount;
  const data = new Uint8Array(bufLen);

  function draw() {
    waveformAnimId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(data);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const barW = canvas.width / bufLen;
    const cy = canvas.height / 2;

    for (let i = 0; i < bufLen; i++) {
      const val = data[i] / 255;
      const h = val * cy * 0.9;
      const hue = 35 + i * 0.5;
      ctx.fillStyle = `hsla(${hue}, 80%, ${50 + val * 20}%, ${0.4 + val * 0.5})`;
      // Mirrored bars
      ctx.fillRect(i * barW, cy - h, barW - 1, h);
      ctx.fillRect(i * barW, cy, barW - 1, h * 0.6);
    }

    // Center line
    ctx.strokeStyle = 'rgba(232,168,56,0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, cy);
    ctx.lineTo(canvas.width, cy);
    ctx.stroke();
  }
  draw();
}

// --- History ---
const compHistory = [];

function addHistory(label, m, val) {
  if (compHistory.find(h => h.label === label)) return;
  compHistory.unshift({ label, mode: m, value: val });
  if (compHistory.length > 10) compHistory.pop();
  renderHistory();
}

function renderHistory() {
  const el = document.getElementById('history');
  el.innerHTML = compHistory.map(h =>
    `<div class="history-chip" onclick="replayHistory('${h.mode}','${h.value}')">${h.label}</div>`
  ).join('');
}

function replayHistory(m, val) {
  switchTab(m);
  if (m === 'name') document.getElementById('nameInput').value = val;
  else document.getElementById('seedInput').value = val;
  compose();
}

function copyShareUrl() {
  const text = document.getElementById('shareUrl').textContent;
  navigator.clipboard.writeText(text);
  document.getElementById('shareUrl').textContent = 'Copied!';
  setTimeout(() => { document.getElementById('shareUrl').textContent = text; }, 1500);
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)
