import { useRef, useEffect } from "react";
import { NoteData, getNoteColor } from "../lib/timing";

interface Props {
  activeNotes: NoteData[];
  progress: number; // 0..1
  size: number;
}

const PHI = (1 + Math.sqrt(5)) / 2;
const GOLDEN_ANGLE = 2 * Math.PI * (1 - 1 / PHI); // ~137.5 degrees

export const FibonacciSpiral: React.FC<Props> = ({
  activeNotes,
  progress,
  size,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const totalPoints = 200;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cx = size / 2;
    const cy = size / 2;
    const maxRadius = size * 0.45;

    ctx.clearRect(0, 0, size, size);

    // Number of spiral points revealed so far
    const revealedCount = Math.floor(progress * totalPoints);

    // Draw spiral dots
    for (let i = 0; i < revealedCount; i++) {
      const angle = i * GOLDEN_ANGLE;
      const r = maxRadius * Math.sqrt(i / totalPoints);
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);

      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255,255,255,0.15)";
      ctx.fill();
    }

    // Light up points for each active note (mapped by pitch to spiral index)
    for (const note of activeNotes) {
      const idx = note.pitch % totalPoints;
      if (idx >= revealedCount) continue;

      const angle = idx * GOLDEN_ANGLE;
      const r = maxRadius * Math.sqrt(idx / totalPoints);
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);

      const color = getNoteColor(note.voiceIndex ?? 0);
      const glow = 6 + (note.velocity / 127) * 10;

      ctx.shadowColor = color;
      ctx.shadowBlur = glow;
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.8;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
    }
  }, [activeNotes, progress, size, totalPoints]);

  return <canvas ref={canvasRef} width={size} height={size} />;
};
