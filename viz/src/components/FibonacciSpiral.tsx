import { useRef, useEffect } from "react";
import { NoteData, getNoteColor } from "../lib/timing";

interface Props {
  activeNotes: NoteData[];
  progress: number;
  size: number;
  tension?: number;
}

const PHI = (1 + Math.sqrt(5)) / 2;
const GOLDEN_ANGLE = 2 * Math.PI * (1 - 1 / PHI);
const TAU = Math.PI * 2;

/**
 * Golden-angle spiral with connecting arcs, pulsing glow trails,
 * and a slowly rotating bloom effect.
 */
export const FibonacciSpiral: React.FC<Props> = ({
  activeNotes,
  progress,
  size,
  tension = 0.5,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const totalPoints = 233; // Fibonacci number

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cx = size / 2;
    const cy = size / 2;
    const maxRadius = size * 0.44;
    const rotation = progress * TAU * 0.15; // slow rotation

    ctx.clearRect(0, 0, size, size);

    const revealedCount = Math.floor(progress * totalPoints);

    // Compute all point positions
    const points: { x: number; y: number; angle: number; r: number }[] = [];
    for (let i = 0; i < totalPoints; i++) {
      const angle = i * GOLDEN_ANGLE + rotation;
      const r = maxRadius * Math.sqrt(i / totalPoints);
      points.push({
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
        angle,
        r,
      });
    }

    // Draw spiral arm curves (connect consecutive revealed points)
    if (revealedCount > 2) {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < revealedCount; i++) {
        // Only connect nearby points to form arms
        if (Math.abs(i % 8) < 2) {
          ctx.lineTo(points[i].x, points[i].y);
        } else {
          ctx.moveTo(points[i].x, points[i].y);
        }
      }
      ctx.strokeStyle = `rgba(232, 168, 56, ${0.04 + tension * 0.06})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw base dots with breathing
    for (let i = 0; i < revealedCount; i++) {
      const p = points[i];
      if (!p) continue;
      const breathe = 1 + Math.sin(progress * TAU * 2 + i * 0.3) * 0.3 * tension;
      const dotSize = (1.5 + (i / totalPoints) * 1.5) * breathe;

      ctx.beginPath();
      ctx.arc(p.x, p.y, dotSize, 0, TAU);
      ctx.fillStyle = `rgba(255,255,255,${0.06 + (i / totalPoints) * 0.08})`;
      ctx.fill();
    }

    // Light up active notes with dramatic multi-layer glow
    const activeIndices = new Set<number>();
    for (const note of activeNotes) {
      const idx = note.pitch % totalPoints;
      if (idx >= revealedCount) continue;
      activeIndices.add(idx);

      const p = points[idx];
      if (!p) continue;
      const color = getNoteColor(note.voiceIndex ?? 0);
      const vel = note.velocity / 127;

      // Outer bloom
      const bloomSize = 20 + vel * 25 + tension * 15;
      const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, bloomSize);
      grad.addColorStop(0, color);
      grad.addColorStop(0.3, color.replace(")", ", 0.3)").replace("rgb", "rgba"));
      grad.addColorStop(1, "transparent");
      ctx.globalAlpha = 0.4 * vel;
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, bloomSize, 0, TAU);
      ctx.fill();

      // Bright core
      ctx.globalAlpha = 0.9;
      ctx.shadowColor = color;
      ctx.shadowBlur = 20 * vel;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4 + vel * 4, 0, TAU);
      ctx.fillStyle = "#fff";
      ctx.fill();

      // Color ring
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 7 + vel * 5, 0, TAU);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.7;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Draw connecting arcs between active notes on the spiral
    const activeList = Array.from(activeIndices).sort((a, b) => a - b);
    if (activeList.length >= 2) {
      for (let i = 0; i < activeList.length - 1; i++) {
        const a = points[activeList[i]];
        const b = points[activeList[i + 1]];
        if (!a || !b) continue;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        // Curved connection through center
        const midX = cx + (a.x + b.x - 2 * cx) * 0.3;
        const midY = cy + (a.y + b.y - 2 * cy) * 0.3;
        ctx.quadraticCurveTo(midX, midY, b.x, b.y);
        ctx.strokeStyle = `rgba(232, 168, 56, ${0.15 + tension * 0.15})`;
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.4;
        ctx.stroke();
      }
    }

    ctx.globalAlpha = 1;
  }, [activeNotes, progress, size, tension, totalPoints]);

  return <canvas ref={canvasRef} width={size} height={size} />;
};
