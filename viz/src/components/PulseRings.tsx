import { useRef, useEffect } from "react";
import { NoteData, getNoteColor } from "../lib/timing";

interface Props {
  activeNotes: NoteData[];
  width: number;
  height: number;
  progress: number;
}

interface Ring {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  color: string;
  life: number;
}

/**
 * Expanding rings that emanate from each note attack,
 * like ripples on water. Creates a sense of space and impact.
 */
export const PulseRings: React.FC<Props> = ({
  activeNotes,
  width,
  height,
  progress,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ringsRef = useRef<Ring[]>([]);
  const prevCountRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Spawn rings for new notes
    if (activeNotes.length > prevCountRef.current) {
      const newNotes = activeNotes.slice(prevCountRef.current);
      for (const note of newNotes) {
        const vel = note.velocity / 127;
        ringsRef.current.push({
          x: width * 0.1 + ((note.pitch * 13) % (width * 0.8)),
          y: height * 0.2 + ((127 - note.pitch) / 80) * height * 0.6,
          radius: 5,
          maxRadius: 60 + vel * 120,
          color: getNoteColor(note.voiceIndex ?? 0),
          life: 1.0,
        });
      }
    }
    prevCountRef.current = activeNotes.length;

    ctx.clearRect(0, 0, width, height);

    const alive: Ring[] = [];
    for (const ring of ringsRef.current) {
      ring.radius += (ring.maxRadius - ring.radius) * 0.06;
      ring.life -= 0.02;
      if (ring.life <= 0) continue;
      alive.push(ring);

      const alpha = ring.life * ring.life * 0.6;
      ctx.beginPath();
      ctx.arc(ring.x, ring.y, ring.radius, 0, Math.PI * 2);
      ctx.strokeStyle = ring.color;
      ctx.lineWidth = Math.max(0.5, 3 * ring.life);
      ctx.globalAlpha = alpha;
      ctx.stroke();

      // Inner faint ring
      if (ring.life > 0.5) {
        ctx.beginPath();
        ctx.arc(ring.x, ring.y, ring.radius * 0.5, 0, Math.PI * 2);
        ctx.globalAlpha = alpha * 0.3;
        ctx.stroke();
      }
    }

    ctx.globalAlpha = 1;
    ringsRef.current = alive.slice(-80);
  }, [activeNotes, width, height, progress]);

  return <canvas ref={canvasRef} width={width} height={height} />;
};
