import { useRef, useEffect } from "react";
import { NoteData, getNoteColor } from "../lib/timing";

interface Props {
  activeNotes: NoteData[];
  recentNotes: NoteData[];
  width: number;
  height: number;
  tension: number;
}

/**
 * Constellation lines connecting active notes with glowing threads.
 * Recent notes leave afterglow trails. Creates a living star-map.
 */
export const NoteConstellation: React.FC<Props> = ({
  activeNotes,
  recentNotes,
  width,
  height,
  tension,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);

    // Map note to screen position: pitch → Y, time-spread → X
    const mapNote = (n: NoteData, spread: number) => ({
      x: ((n.pitch * 7 + (n.voiceIndex ?? 0) * 200 + spread * 80) % width),
      y: height * 0.15 + ((127 - n.pitch) / 80) * height * 0.7,
      vel: n.velocity / 127,
      color: getNoteColor(n.voiceIndex ?? 0),
    });

    // Fading trails from recent notes
    for (let i = 0; i < recentNotes.length; i++) {
      const age = i / recentNotes.length;
      const n = mapNote(recentNotes[i], i * 0.3);
      const alpha = (1 - age) * 0.15;
      ctx.beginPath();
      ctx.arc(n.x, n.y, 2 + n.vel * 3, 0, Math.PI * 2);
      ctx.fillStyle = n.color;
      ctx.globalAlpha = alpha;
      ctx.fill();
    }

    // Active note stars
    const points = activeNotes.map((n, i) => mapNote(n, i));

    // Connection lines between active notes
    if (points.length >= 2) {
      for (let i = 0; i < points.length; i++) {
        for (let j = i + 1; j < points.length; j++) {
          const a = points[i];
          const b = points[j];
          if (!a || !b) continue;
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist > width * 0.5) continue;

          const lineAlpha = Math.max(0, 0.3 - dist / (width * 0.5)) * (0.5 + tension * 0.5);
          const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
          grad.addColorStop(0, a.color);
          grad.addColorStop(1, b.color);

          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1 + tension;
          ctx.globalAlpha = lineAlpha;
          ctx.stroke();
        }
      }
    }

    // Draw active stars with multi-ring glow
    for (const p of points) {
      // Outer glow
      ctx.globalAlpha = 0.15 * p.vel;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 30 * p.vel * (1 + tension);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 12 + p.vel * 8 + tension * 6, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();

      // Inner bright core
      ctx.shadowBlur = 15;
      ctx.globalAlpha = 0.7 + p.vel * 0.3;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3 + p.vel * 3, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();

      // Color ring
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 0.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6 + p.vel * 5, 0, Math.PI * 2);
      ctx.strokeStyle = p.color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
  }, [activeNotes, recentNotes, width, height, tension]);

  return <canvas ref={canvasRef} width={width} height={height} />;
};
