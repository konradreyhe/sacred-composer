import { useRef, useEffect, useMemo } from "react";
import { NoteData, getNoteColor } from "../lib/timing";

interface Props {
  activeNotes: NoteData[];
  progress: number;
  width: number;
  height: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  color: string;
  size: number;
}

/**
 * Particle field that emits particles on each note attack.
 * Particles drift upward like fireflies, fading with golden-ratio timing.
 */
export const ParticleField: React.FC<Props> = ({
  activeNotes,
  progress,
  width,
  height,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const prevNotesRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Spawn particles for new notes
    const noteCount = activeNotes.length;
    if (noteCount > prevNotesRef.current) {
      const newNotes = activeNotes.slice(prevNotesRef.current);
      for (const note of newNotes) {
        const x = ((note.pitch - 40) / 50) * width;
        const y = height * 0.6 + (Math.random() - 0.5) * height * 0.3;
        const color = getNoteColor(note.voiceIndex ?? 0);
        const vel = note.velocity / 127;

        for (let j = 0; j < 3 + Math.floor(vel * 5); j++) {
          particlesRef.current.push({
            x: x + (Math.random() - 0.5) * 30,
            y,
            vx: (Math.random() - 0.5) * 2,
            vy: -0.5 - Math.random() * 2 * vel,
            life: 1.0,
            color,
            size: 2 + Math.random() * 4 * vel,
          });
        }
      }
    }
    prevNotesRef.current = noteCount;

    // Update and draw particles
    ctx.clearRect(0, 0, width, height);

    const alive: Particle[] = [];
    for (const p of particlesRef.current) {
      p.x += p.vx;
      p.y += p.vy;
      p.vy -= 0.01; // gentle gravity upward
      p.life -= 0.015;

      if (p.life <= 0) continue;
      alive.push(p);

      ctx.globalAlpha = p.life * p.life; // quadratic fade
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 8 * p.life;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();
    }

    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
    particlesRef.current = alive;

    // Limit particle count
    if (particlesRef.current.length > 500) {
      particlesRef.current = particlesRef.current.slice(-500);
    }
  }, [activeNotes, progress, width, height]);

  return <canvas ref={canvasRef} width={width} height={height} />;
};
