import { useRef, useEffect } from "react";
import { NoteData, getNoteColor } from "../lib/timing";

interface Props {
  activeNotes: NoteData[];
  progress: number;
  width: number;
  height: number;
}

const PHI = (1 + Math.sqrt(5)) / 2;

/**
 * Animated golden-ratio wave: overlapping sine waves whose frequencies
 * relate by phi. Active notes modulate amplitude and color.
 */
export const GoldenRatioWave: React.FC<Props> = ({
  activeNotes,
  progress,
  width,
  height,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);
    const cy = height / 2;

    // Base amplitude from active notes
    const avgVel =
      activeNotes.length > 0
        ? activeNotes.reduce((s, n) => s + n.velocity, 0) /
          activeNotes.length /
          127
        : 0.2;

    const layers = [
      { freq: 1, color: "rgba(232,168,56,0.4)", amp: 0.35 },
      { freq: PHI, color: "rgba(79,195,247,0.3)", amp: 0.25 },
      { freq: PHI * PHI, color: "rgba(171,71,188,0.2)", amp: 0.18 },
      { freq: PHI * PHI * PHI, color: "rgba(102,187,106,0.15)", amp: 0.12 },
    ];

    const phase = progress * Math.PI * 6;

    for (const layer of layers) {
      ctx.beginPath();
      ctx.moveTo(0, cy);

      for (let x = 0; x <= width; x += 2) {
        const t = x / width;
        const wave =
          Math.sin(t * Math.PI * 4 * layer.freq + phase) *
          layer.amp *
          height *
          (0.3 + avgVel * 0.7);
        // Envelope: fade edges
        const env = Math.sin(t * Math.PI);
        ctx.lineTo(x, cy + wave * env);
      }

      ctx.strokeStyle = layer.color;
      ctx.lineWidth = 2 + avgVel * 3;
      ctx.stroke();

      // Fill below curve with gradient
      ctx.lineTo(width, height);
      ctx.lineTo(0, height);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, cy, 0, height);
      grad.addColorStop(0, layer.color);
      grad.addColorStop(1, "transparent");
      ctx.fillStyle = grad;
      ctx.globalAlpha = 0.15;
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    // Draw note particles on the wave
    for (const note of activeNotes) {
      const t = (note.pitch % 24) / 24;
      const x = t * width;
      const wave =
        Math.sin(t * Math.PI * 4 + phase) *
        0.35 *
        height *
        (0.3 + avgVel * 0.7) *
        Math.sin(t * Math.PI);

      const color = getNoteColor(note.voiceIndex ?? 0);
      const radius = 4 + (note.velocity / 127) * 6;

      ctx.shadowColor = color;
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.arc(x, cy + wave, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }, [activeNotes, progress, width, height]);

  return <canvas ref={canvasRef} width={width} height={height} />;
};
