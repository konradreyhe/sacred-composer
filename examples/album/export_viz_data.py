"""Export visualization JSON for all 10 album tracks.

Reads seeds.json, builds each track with CompositionBuilder,
calls comp.to_visualization_json(), and saves to viz/src/data/track_NN.json.

Usage:
    python examples/album/export_viz_data.py
    python examples/album/export_viz_data.py --track 6   # just one
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
PROJECT_ROOT = ALBUM_DIR.parent.parent
VIZ_DATA_DIR = PROJECT_ROOT / "viz" / "src" / "data"
VIZ_DATA_DIR.mkdir(parents=True, exist_ok=True)

FRISSON_TRACK = 6


def build_track(track: dict, config: dict, use_frisson: bool):
    """Build a Composition from track + config dicts."""
    builder = (
        CompositionBuilder(
            key=track["key"],
            tempo=config["tempo"],
            bars=config["bars"],
            title=track["title"],
        )
        .form(pattern=config["form_pattern"], n_sections=config["n_sections"])
        .melody(
            pattern=track["pattern"],
            instrument=config["melody_instrument"],
            seed=track["seed"],
        )
        .bass(
            pattern=config["bass_pattern"],
            instrument=config["bass_instrument"],
            seed=track["seed"] + config["bass_seed_offset"],
        )
    )
    if use_frisson:
        builder = builder.frisson(intensity=1.0)
    return builder.build()


def main():
    parser = argparse.ArgumentParser(description="Export viz JSON for album tracks")
    parser.add_argument("--track", type=int, default=None,
                        help="Export only track #N (1-9). Default: all.")
    args = parser.parse_args()

    with open(ALBUM_DIR / "seeds.json", encoding="utf-8") as f:
        album = json.load(f)

    config = album["config"]
    tracks = album["tracks"]
    if args.track is not None:
        tracks = [t for t in tracks if t["number"] == args.track]
        if not tracks:
            print(f"Track {args.track} not found in seeds.json")
            return

    for track in tracks:
        use_frisson = track["number"] == FRISSON_TRACK
        tag = " [FRISSON]" if use_frisson else ""
        print(f"Track {track['number']:02d}: {track['title']}"
              f" ({track['key']} seed={track['seed']}){tag}")

        comp = build_track(track, config, use_frisson=use_frisson)
        viz_data = comp.to_visualization_json()

        # Add audio file reference for Remotion
        viz_data["meta"]["audioFile"] = f"track_{track['number']:02d}.wav"

        out_path = VIZ_DATA_DIR / f"track_{track['number']:02d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(viz_data, f, indent=2)

        n_voices = len(viz_data["voices"])
        n_notes = sum(len(v["notes"]) for v in viz_data["voices"])
        n_sections = len(viz_data["formSections"])
        dur = viz_data["meta"]["durationSec"]
        print(f"  -> {out_path.name}  "
              f"({n_voices} voices, {n_notes} notes, "
              f"{n_sections} sections, {dur:.1f}s)")

    print()
    print("Exported files:")
    for p in sorted(VIZ_DATA_DIR.glob("track_*.json")):
        sz_kb = p.stat().st_size / 1024
        print(f"  {p.name}  ({sz_kb:.1f} KB)")


if __name__ == "__main__":
    main()
