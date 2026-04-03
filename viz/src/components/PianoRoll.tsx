import { useRef, useEffect } from "react";
import { VoiceData, getNoteColor } from "../lib/timing";

interface Props {
  voices: VoiceData[];
  currentSec: number;
  width: number;
  height: number;
  visibleWindowSec: number;
}

export const PianoRoll: React.FC<Props> = ({
  voices,
  currentSec,
  width,
  height,
  visibleWindowSec,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Compute global pitch range once
  let minPitch = 127;
  let maxPitch = 0;
  for (const v of voices) {
    for (const n of v.notes) {
      if (n.pitch < minPitch) minPitch = n.pitch;
      if (n.pitch > maxPitch) maxPitch = n.pitch;
    }
  }
  minPitch = Math.max(0, minPitch - 2);
  maxPitch = Math.min(127, maxPitch + 2);
  const pitchRange = maxPitch - minPitch || 1;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    const windowStart = currentSec - visibleWindowSec * 0.3;
    const windowEnd = windowStart + visibleWindowSec;
    const pxPerSec = width / visibleWindowSec;
    const noteHeight = height / pitchRange;

    // Draw subtle grid lines for octave boundaries
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 1;
    for (let p = minPitch; p <= maxPitch; p++) {
      if (p % 12 === 0) {
        const y = height - ((p - minPitch) / pitchRange) * height;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
    }

    // Draw playhead
    const playheadX = (currentSec - windowStart) * pxPerSec;
    ctx.strokeStyle = "rgba(255,255,255,0.25)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, height);
    ctx.stroke();

    // Draw notes per voice
    voices.forEach((voice, vi) => {
      const color = getNoteColor(vi);
      for (const n of voice.notes) {
        const noteEnd = n.startSec + n.durationSec;
        if (noteEnd < windowStart || n.startSec > windowEnd) continue;

        const x = (n.startSec - windowStart) * pxPerSec;
        const w = n.durationSec * pxPerSec;
        const y =
          height - ((n.pitch - minPitch) / pitchRange) * height - noteHeight;

        const isActive =
          currentSec >= n.startSec && currentSec < noteEnd;
        const alpha = isActive
          ? 0.6 + 0.4 * (n.velocity / 127)
          : 0.25 + 0.25 * (n.velocity / 127);

        // Note rectangle
        ctx.fillStyle = color;
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.roundRect(x, y, Math.max(w, 2), noteHeight * 0.85, 3);
        ctx.fill();

        // Glow for active notes
        if (isActive) {
          ctx.shadowColor = color;
          ctx.shadowBlur = 16;
          ctx.fillStyle = color;
          ctx.globalAlpha = 0.3;
          ctx.beginPath();
          ctx.roundRect(x, y, Math.max(w, 2), noteHeight * 0.85, 3);
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      }
    });

    ctx.globalAlpha = 1;
  }, [voices, currentSec, width, height, visibleWindowSec, minPitch, pitchRange, noteHeight]);

  return <canvas ref={canvasRef} width={width} height={height} />;
};
