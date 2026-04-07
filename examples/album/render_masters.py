"""Render the 10 album tracks to master WAVs.

Reads examples/album/seeds.json, renders each track via FluidSynth,
applies the Goosebump Engine to the designated signature track
(track 6, Mandelbrot Boundary). Output lands in masters/.

Next step after this: FFmpeg loudnorm pass to normalize to -14 LUFS
(Spotify target).

Usage:
    python examples/album/render_masters.py
    python examples/album/render_masters.py --track 6   # just one
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sacred_composer.builder import CompositionBuilder


ALBUM_DIR = Path(__file__).parent
MASTERS_DIR = ALBUM_DIR / "masters"
MASTERS_DIR.mkdir(exist_ok=True)

# Which track number gets the Goosebump Engine (frisson appoggiatura).
FRISSON_TRACK = 6


def slugify(title: str) -> str:
    return title.lower().replace(" ", "_").replace("(", "").replace(")", "") \
        .replace("'", "").replace(",", "").replace("=", "").replace(".", "_")


def render_track(track: dict, config: dict, use_frisson: bool) -> Path:
    slug = f"{track['number']:02d}_{slugify(track['title'])}"
    out = MASTERS_DIR / f"{slug}.wav"

    # Per-track overrides (optional keys in track dict)
    n_sections = track.get("n_sections", config["n_sections"])
    base_duration = track.get("base_duration", None)

    melody_kwargs = dict(
        pattern=track["pattern"],
        instrument=config["melody_instrument"],
        seed=track["seed"],
    )
    if base_duration is not None:
        melody_kwargs["base_duration"] = base_duration

    builder = (
        CompositionBuilder(
            key=track["key"],
            tempo=config["tempo"],
            bars=config["bars"],
            title=track["title"],
        )
        .form(pattern=config["form_pattern"], n_sections=n_sections)
        .melody(**melody_kwargs)
        .bass(
            pattern=config["bass_pattern"],
            instrument=config["bass_instrument"],
            seed=track["seed"] + config["bass_seed_offset"],
        )
    )
    if use_frisson:
        builder = builder.frisson(intensity=1.0)
    comp = builder.build()
    comp.render(str(out))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", type=int, default=None,
                        help="Render only track #N (1-9). Default: all.")
    parser.add_argument("--no-frisson", action="store_true",
                        help="Skip frisson engine even on signature track")
    args = parser.parse_args()

    with open(ALBUM_DIR / "seeds.json", encoding="utf-8") as f:
        album = json.load(f)

    config = album["config"]
    tracks = album["tracks"]
    if args.track is not None:
        tracks = [t for t in tracks if t["number"] == args.track]
        if not tracks:
            print(f"Track {args.track} not found")
            return

    for track in tracks:
        is_signature = (track["number"] == FRISSON_TRACK) and not args.no_frisson
        tag = " [FRISSON]" if is_signature else ""
        print(f"Track {track['number']}: {track['title']}"
              f" ({track['key']} seed={track['seed']}){tag}")
        out = render_track(track, config, use_frisson=is_signature)
        print(f"  -> {out}")

    print()
    print("Rendered tracks:")
    for w in sorted(MASTERS_DIR.glob("*.wav")):
        sz_mb = w.stat().st_size / (1024 * 1024)
        print(f"  {w.name}  ({sz_mb:.1f} MB)")


if __name__ == "__main__":
    main()
