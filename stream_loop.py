#!/usr/bin/env python3
"""24/7 Sacred Geometry music stream generator.

Continuously generates compositions and renders WAV + metadata.
Designed to feed into OBS/ffmpeg for YouTube livestreaming.

Usage:
    python stream_loop.py                    # Generate to output/stream/
    python stream_loop.py --output ./live    # Custom output dir
    python stream_loop.py --once             # Generate one and exit
"""

import argparse
import json
import random
import time
from pathlib import Path

from sacred_composer.builder import CompositionBuilder

# Musical presets that create variety
PRESETS = [
    {"key": "D_minor", "pattern": "infinity_series", "mood": "contemplative"},
    {"key": "A_minor", "pattern": "fibonacci", "mood": "introspective"},
    {"key": "C_minor", "pattern": "golden_spiral", "mood": "mysterious"},
    {"key": "E_minor", "pattern": "logistic", "mood": "restless"},
    {"key": "G_minor", "pattern": "mandelbrot", "mood": "otherworldly"},
    {"key": "F_minor", "pattern": "rossler", "mood": "flowing"},
    {"key": "C_major", "pattern": "fibonacci", "mood": "luminous"},
    {"key": "D_major", "pattern": "infinity_series", "mood": "radiant"},
    {"key": "A_minor", "pattern": "golden_spiral", "mood": "ancient"},
    {"key": "E_minor", "pattern": "cantor", "mood": "sparse"},
]

PATTERN_DISPLAY = {
    "infinity_series": "Infinity Series",
    "fibonacci": "Fibonacci Sequence",
    "golden_spiral": "Golden Spiral",
    "logistic": "Logistic Map",
    "mandelbrot": "Mandelbrot Boundary",
    "rossler": "Rossler Attractor",
    "cantor": "Cantor Set",
}


def generate_one(seed: int, output_dir: Path) -> dict:
    """Generate one composition. Returns metadata dict."""
    preset = PRESETS[seed % len(PRESETS)]
    key = preset["key"]
    pattern = preset["pattern"]
    mood = preset["mood"]
    tempo = 60 + (seed % 30)  # 60-89 BPM (calm range)
    bars = 40 + (seed % 20)   # 40-59 bars (2-4 minutes)
    n_sections = 4 + (seed % 3)

    title = f"Seed #{seed} — {PATTERN_DISPLAY.get(pattern, pattern)} in {key.replace('_', ' ')}"

    print(f"\n{'='*60}")
    print(f"  Generating: {title}")
    print(f"  Mood: {mood} | Tempo: {tempo} BPM | Bars: {bars}")
    print(f"{'='*60}")

    # Richer composition: 3 voices + drone for orchestral depth
    inner_instruments = ["oboe", "viola", "clarinet", "flute", "horn"]
    inner_patterns = ["golden_spiral", "fibonacci", "infinity_series"]

    builder = CompositionBuilder(key=key, tempo=tempo, bars=bars, title=title)
    builder.form(pattern="fibonacci", n_sections=n_sections)
    builder.melody(pattern=pattern, instrument="violin", seed=seed)
    builder.inner_voice(
        pattern=inner_patterns[seed % len(inner_patterns)],
        instrument=inner_instruments[seed % len(inner_instruments)],
        seed=seed + 5,
    )
    builder.bass(pattern="harmonic_series", instrument="cello", seed=seed + 10)
    builder.drone(instrument="contrabass", velocity=35)
    piece = builder.build()

    # Render files
    wav_path = output_dir / f"seed_{seed:06d}.wav"
    mid_path = output_dir / f"seed_{seed:06d}.mid"
    json_path = output_dir / f"seed_{seed:06d}.json"

    piece.render(str(mid_path))
    piece.render(str(wav_path))
    print(f"  WAV: {wav_path} ({wav_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Build viz JSON
    voices_data = []
    beats_per_sec = tempo / 60.0
    for v in piece.score.voices:
        notes = []
        for n in v.notes:
            if n.is_rest or n.pitch < 0:
                continue
            notes.append({
                "pitch": n.pitch,
                "velocity": n.velocity,
                "startSec": n.time,
                "durationSec": n.duration,
                "startBeat": n.time * beats_per_sec,
                "durationBeat": n.duration * beats_per_sec,
                "pitchBend": None,
            })
        voices_data.append({
            "name": v.name,
            "instrument": "violin" if "violin" in v.name else "cello",
            "channel": v.channel,
            "notes": notes,
        })

    all_ends = [n["startSec"] + n["durationSec"] for voice in voices_data for n in voice["notes"]]
    dur_sec = max(all_ends) if all_ends else 60

    sections = []
    if piece.form:
        for s in piece.form:
            sections.append({
                "label": getattr(s, "label", f"Section {s.start_bar}-{s.end_bar}"),
                "startBar": s.start_bar,
                "endBar": s.end_bar,
                "bars": s.end_bar - s.start_bar,
            })

    meta = {
        "title": title,
        "seed": seed,
        "key": key,
        "pattern": pattern,
        "mood": mood,
        "tempo": tempo,
        "bars": bars,
        "durationSec": dur_sec,
        "durationBeats": dur_sec * beats_per_sec,
        "fps": 30,
        "wavFile": str(wav_path.name),
        "midFile": str(mid_path.name),
    }

    viz_data = {
        "meta": meta,
        "voices": voices_data,
        "formSections": sections,
    }

    with open(json_path, "w") as f:
        json.dump(viz_data, f, indent=2)

    print(f"  Duration: {dur_sec:.0f}s | Notes: {sum(len(v['notes']) for v in voices_data)}")
    return meta


def stream_loop(output_dir: Path, start_seed: int = 0):
    """Infinite generation loop."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Playlist file for ffmpeg concat
    playlist_path = output_dir / "playlist.txt"

    seed = start_seed
    print(f"\n  Sacred Composer — 24/7 Stream Generator")
    print(f"  Output: {output_dir}")
    print(f"  Starting from seed {seed}")
    print(f"  Press Ctrl+C to stop\n")

    while True:
        try:
            meta = generate_one(seed, output_dir)

            # Append to playlist
            with open(playlist_path, "a") as f:
                f.write(f"file '{meta['wavFile']}'\n")

            print(f"  Added to playlist. Total: {seed - start_seed + 1} compositions.")
            seed += 1
            time.sleep(1)  # Brief pause between generations

        except KeyboardInterrupt:
            print(f"\n\nStopped. Generated {seed - start_seed} compositions.")
            print(f"Playlist: {playlist_path}")
            print(f"\nTo stream with ffmpeg:")
            print(f"  ffmpeg -f concat -safe 0 -i {playlist_path} -f wav - | "
                  f"ffmpeg -re -i - -c:a aac -b:a 192k -f flv rtmp://YOUR_YOUTUBE_KEY")
            break

        except Exception as e:
            print(f"  Error on seed {seed}: {e}")
            seed += 1


def main():
    parser = argparse.ArgumentParser(description="Sacred Composer stream generator")
    parser.add_argument("--output", default="output/stream", help="Output directory")
    parser.add_argument("--seed", type=int, default=0, help="Starting seed")
    parser.add_argument("--once", action="store_true", help="Generate one and exit")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.once:
        generate_one(args.seed, output_dir)
    else:
        stream_loop(output_dir, args.seed)


if __name__ == "__main__":
    main()
