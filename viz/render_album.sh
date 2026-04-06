#!/usr/bin/env bash
# Render all 9 album track videos via Remotion.
#
# Prerequisites:
#   1. Copy each track's WAV into viz/public/ as composition_NN.wav
#      (or run: python examples/album/copy_audio_to_viz.py)
#   2. npm install in viz/
#
# Usage:
#   cd viz && bash render_album.sh
#   bash render_album.sh --track 6   # render just one

set -euo pipefail

TRACKS=(
  "Track01-Threshold"
  "Track02-InfiniteSeries"
  "Track03-GoldenSpiral"
  "Track04-HarmonicSeries"
  "Track05-LogisticMap"
  "Track06-MandelbrotBoundary"
  "Track07-RosslerAttractor"
  "Track08-CantorsDust"
  "Track09-ZipfsLaw"
  "Track10-ThueMorseResolution"
)

OUTDIR="out/album"
mkdir -p "$OUTDIR"

if [[ "${1:-}" == "--track" && -n "${2:-}" ]]; then
  idx=$(( $2 - 1 ))
  TRACKS=("${TRACKS[$idx]}")
fi

for track in "${TRACKS[@]}"; do
  echo "=== Rendering $track ==="
  npx remotion render "$track" \
    --codec h264 \
    --output "$OUTDIR/${track}.mp4" \
    --log warn
  echo "  -> $OUTDIR/${track}.mp4"
done

echo ""
echo "Done. Videos in $OUTDIR/"
ls -lh "$OUTDIR"/*.mp4
