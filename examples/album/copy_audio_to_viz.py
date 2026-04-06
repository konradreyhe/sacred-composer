"""Copy normalized album WAVs into viz/public/ for Remotion rendering.

Maps: normalized/01_threshold.wav -> viz/public/track_01.wav

Usage:
    python examples/album/copy_audio_to_viz.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

ALBUM_DIR = Path(__file__).parent
NORMALIZED_DIR = ALBUM_DIR / "normalized"
VIZ_PUBLIC = ALBUM_DIR.parent.parent / "viz" / "public"
VIZ_PUBLIC.mkdir(parents=True, exist_ok=True)

# Map track number from filename prefix (01_, 02_, etc.)
def main():
    wavs = sorted(NORMALIZED_DIR.glob("*.wav"))
    if not wavs:
        print(f"No WAVs found in {NORMALIZED_DIR}")
        print("Run render_masters.py + ffmpeg normalization first.")
        return

    for wav in wavs:
        # Extract track number from filename like "01_threshold.wav"
        num = wav.name.split("_")[0]
        dest = VIZ_PUBLIC / f"track_{num}.wav"
        print(f"  {wav.name} -> {dest.name}")
        shutil.copy2(wav, dest)

    print(f"\nCopied {len(wavs)} WAVs to {VIZ_PUBLIC}")


if __name__ == "__main__":
    main()
