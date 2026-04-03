import { useRef, useEffect } from "react";
import { NoteData, getNoteColor } from "../lib/timing";

interface Props {
  activeNotes: NoteData[];
  progress: number;
  size: number;
}

const PHI = (1 + Math.sqrt(5)) / 2;
const TAU = Math.PI * 2;

/**
 * Flower of Life / sacred geometry that breathes with the music.
 * Circles pulse with note velocity, colors shift with voice.
 */
export const SacredGeometry: React.FC<Props> = ({
  activeNotes,
  progress,
  size,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cx = size / 2;
    const cy = size / 2;
    const baseR = size * 0.15;

    ctx.clearRect(0, 0, size, size);

    const avgVel =
      activeNotes.length > 0
        ? activeNotes.reduce((s, n) => s + n.velocity, 0) /
          activeNotes.length /
          127
        : 0.15;

    const breathe = 1 + Math.sin(progress * TAU * 3) * 0.08 * avgVel;
    const rotation = progress * TAU * 0.3;

    // Flower of Life: center + 6 surrounding circles + 12 outer
    const circles: { x: number; y: number; ring: number }[] = [
      { x: cx, y: cy, ring: 0 },
    ];

    // First ring: 6 circles
    for (let i = 0; i < 6; i++) {
      const angle = (i / 6) * TAU + rotation;
      circles.push({
        x: cx + baseR * breathe * Math.cos(angle),
        y: cy + baseR * breathe * Math.sin(angle),
        ring: 1,
      });
    }

    // Second ring: 12 circles (only reveal as progress increases)
    const revealOuter = Math.min(12, Math.floor(progress * 20));
    for (let i = 0; i < revealOuter; i++) {
      const angle = (i / 12) * TAU + rotation * 0.5;
      const r = baseR * 2 * breathe;
      circles.push({
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
        ring: 2,
      });
    }

    // Draw circles
    for (const c of circles) {
      const ringAlpha = c.ring === 0 ? 0.4 : c.ring === 1 ? 0.25 : 0.12;
      const alpha = ringAlpha + avgVel * 0.3;

      ctx.beginPath();
      ctx.arc(c.x, c.y, baseR * breathe, 0, TAU);
      ctx.strokeStyle = `rgba(232, 168, 56, ${alpha})`;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }

    // Light up circles based on active notes
    for (const note of activeNotes) {
      const idx = note.pitch % circles.length;
      const c = circles[idx];
      const color = getNoteColor(note.voiceIndex ?? 0);
      const intensity = note.velocity / 127;

      ctx.shadowColor = color;
      ctx.shadowBlur = 15 * intensity;
      ctx.beginPath();
      ctx.arc(c.x, c.y, baseR * breathe * (0.3 + intensity * 0.7), 0, TAU);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5 + intensity * 2;
      ctx.globalAlpha = 0.5 + intensity * 0.5;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
    }

    // Center dot
    ctx.beginPath();
    ctx.arc(cx, cy, 3 + avgVel * 4, 0, TAU);
    ctx.fillStyle = `rgba(232, 168, 56, ${0.6 + avgVel * 0.4})`;
    ctx.shadowColor = "#E8A838";
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;
  }, [activeNotes, progress, size]);

  return <canvas ref={canvasRef} width={size} height={size} />;
};
