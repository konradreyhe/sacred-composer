import { useRef, useEffect } from "react";
import { VoiceData, getNoteColor } from "../lib/timing";

interface Props {
  voices: VoiceData[];
  currentSec: number;
  width: number;
  height: number;
  visibleWindowSec: number;
  tension?: number;
}

/**
 * Cinematic scrolling piano roll with glow trails, velocity-driven
 * brightness, and a playhead light sweep.
 */
export const PianoRoll: React.FC<Props> = ({
  voices,
  currentSec,
  width,
  height,
  visibleWindowSec,
  tension = 0.5,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  let minPitch = 127;
  let maxPitch = 0;
  for (const v of voices) {
    for (const n of v.notes) {
      if (n.pitch < minPitch) minPitch = n.pitch;
      if (n.pitch > maxPitch) maxPitch = n.pitch;
    }
  }
  minPitch = Math.max(0, minPitch - 3);
  maxPitch = Math.min(127, maxPitch + 3);
  const pitchRange = maxPitch - minPitch || 1;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    const windowStart = currentSec - visibleWindowSec * 0.35;
    const windowEnd = windowStart + visibleWindowSec;
    const pxPerSec = width / visibleWindowSec;
    const noteH = Math.max(4, height / pitchRange);

    // Subtle horizontal grid (every octave)
    for (let p = minPitch; p <= maxPitch; p++) {
      if (p % 12 === 0) {
        const y = height - ((p - minPitch) / pitchRange) * height;
        ctx.strokeStyle = "rgba(255,255,255,0.04)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
    }

    // Playhead sweep glow
    const playheadX = (currentSec - windowStart) * pxPerSec;
    const sweepGrad = ctx.createLinearGradient(
      playheadX - 60, 0, playheadX + 20, 0
    );
    sweepGrad.addColorStop(0, "transparent");
    sweepGrad.addColorStop(0.7, `rgba(232,168,56,${0.06 + tension * 0.06})`);
    sweepGrad.addColorStop(1, "transparent");
    ctx.fillStyle = sweepGrad;
    ctx.fillRect(playheadX - 60, 0, 80, height);

    // Playhead line
    ctx.strokeStyle = `rgba(232,168,56,${0.4 + tension * 0.3})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playheadX, 0);
    ctx.lineTo(playheadX, height);
    ctx.stroke();

    // Draw notes
    voices.forEach((voice, vi) => {
      const color = getNoteColor(vi);
      for (const n of voice.notes) {
        const noteEnd = n.startSec + n.durationSec;
        if (noteEnd < windowStart || n.startSec > windowEnd) continue;

        const x = (n.startSec - windowStart) * pxPerSec;
        const w = Math.max(n.durationSec * pxPerSec, 3);
        const y = height - ((n.pitch - minPitch) / pitchRange) * height - noteH;
        const vel = n.velocity / 127;

        const isActive = currentSec >= n.startSec && currentSec < noteEnd;
        const isPast = currentSec >= noteEnd;

        // Past notes: dim afterglow trail
        if (isPast) {
          const fadeTime = currentSec - noteEnd;
          const trailAlpha = Math.max(0, 0.2 - fadeTime * 0.05) * vel;
          ctx.globalAlpha = trailAlpha;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.roundRect(x, y, w, noteH * 0.8, 3);
          ctx.fill();
          continue;
        }

        // Future notes: subtle preview
        if (!isActive) {
          ctx.globalAlpha = 0.12 + vel * 0.12;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.roundRect(x, y, w, noteH * 0.8, 3);
          ctx.fill();
          continue;
        }

        // ACTIVE notes: full glow treatment
        // Outer bloom
        ctx.shadowColor = color;
        ctx.shadowBlur = 25 * vel * (1 + tension * 0.5);
        ctx.globalAlpha = 0.25 * vel;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(x - 4, y - 4, w + 8, noteH * 0.8 + 8, 6);
        ctx.fill();

        // Main bar
        ctx.shadowBlur = 12;
        ctx.globalAlpha = 0.5 + vel * 0.5;
        ctx.beginPath();
        ctx.roundRect(x, y, w, noteH * 0.8, 3);
        ctx.fill();

        // Bright leading edge
        ctx.shadowBlur = 0;
        ctx.globalAlpha = 0.8;
        const edgeX = (currentSec - windowStart) * pxPerSec;
        const edgeW = Math.min(6, w);
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.roundRect(
          Math.min(edgeX, x + w - edgeW),
          y,
          edgeW,
          noteH * 0.8,
          2
        );
        ctx.fill();
      }
    });

    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
  }, [voices, currentSec, width, height, visibleWindowSec, minPitch, pitchRange, tension]);

  return <canvas ref={canvasRef} width={width} height={height} />;
};
