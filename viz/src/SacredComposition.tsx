import {
  AbsoluteFill,
  Audio,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  interpolate,
  Easing,
  random,
} from "remotion";
import { useRef } from "react";
import { PianoRoll } from "./components/PianoRoll";
import { FormTimeline } from "./components/FormTimeline";
import { FibonacciSpiral } from "./components/FibonacciSpiral";
import { GoldenRatioWave } from "./components/GoldenRatioWave";
import { SacredGeometry } from "./components/SacredGeometry";
import { ParticleField } from "./components/ParticleField";
import { NoteConstellation } from "./components/NoteConstellation";
import { PulseRings } from "./components/PulseRings";
import {
  CompositionData,
  NoteData,
  frameToSec,
  getActiveNotes,
} from "./lib/timing";

const PHI_INVERSE = 0.618;

/** Get notes that ended recently (for trails/afterglow). */
function getRecentNotes(
  voices: CompositionData["voices"],
  currentSec: number,
  windowSec: number = 2
): NoteData[] {
  const recent: NoteData[] = [];
  for (let vi = 0; vi < voices.length; vi++) {
    for (const n of voices[vi].notes) {
      const end = n.startSec + n.durationSec;
      if (end < currentSec && end > currentSec - windowSec) {
        recent.push({ ...n, voiceIndex: vi });
      }
    }
  }
  return recent;
}

export const SacredComposition: React.FC<{ data: CompositionData }> = ({
  data,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const currentSec = frameToSec(frame, fps);
  const activeNotes = getActiveNotes(data.voices, currentSec);
  const recentNotes = getRecentNotes(data.voices, currentSec, 3);
  const progress = currentSec / data.meta.durationSec;

  // Tension arc: peaks at golden section
  const tension =
    progress < PHI_INVERSE
      ? Math.sin((Math.PI * progress) / (2 * PHI_INVERSE))
      : Math.sin((Math.PI * (1 - progress)) / (2 * (1 - PHI_INVERSE)));

  // Smooth fade in / out
  const fadeIn = interpolate(frame, [0, fps * 3], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 4, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", easing: Easing.in(Easing.cubic) }
  );
  const masterOpacity = fadeIn * fadeOut;

  // Background: deep space gradient that shifts with tension
  const bgHue = interpolate(tension, [0, 1], [225, 260]);
  const bgSat = interpolate(tension, [0, 1], [30, 50]);
  const bgLight = interpolate(tension, [0, 1], [3, 7]);

  // Note intensity drives ambient effects
  const noteEnergy = Math.min(1, activeNotes.length / 5);
  const avgVel =
    activeNotes.length > 0
      ? activeNotes.reduce((s, n) => s + n.velocity, 0) /
        activeNotes.length /
        127
      : 0;

  // Title intro animation
  const titleOpacity = interpolate(frame, [fps * 1, fps * 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const titleY = interpolate(frame, [fps * 1, fps * 4], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: `hsl(${bgHue}, ${bgSat}%, ${bgLight}%)`,
        opacity: masterOpacity,
        overflow: "hidden",
      }}
    >
      {/* Audio — uses track-specific file if available, falls back to default */}
      <Audio src={staticFile(data.meta.audioFile || "composition.wav")} />

      {/* === BACKGROUND LAYERS === */}

      {/* Slow radial gradient that breathes */}
      <div
        style={{
          position: "absolute",
          inset: "-20%",
          background: `radial-gradient(ellipse at ${50 + Math.sin(progress * Math.PI * 2) * 10}% ${50 + Math.cos(progress * Math.PI * 1.5) * 8}%,
            hsla(${bgHue + 20}, 60%, ${12 + tension * 8}%, ${0.3 + tension * 0.2}) 0%,
            transparent 60%)`,
          pointerEvents: "none",
        }}
      />

      {/* Pulse rings (behind everything) */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.5 }}>
        <PulseRings
          activeNotes={activeNotes}
          width={width}
          height={height}
          progress={progress}
        />
      </div>

      {/* Particle field */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.6 + tension * 0.2 }}>
        <ParticleField
          activeNotes={activeNotes}
          progress={progress}
          width={width}
          height={height}
        />
      </div>

      {/* === MIDDLE LAYERS === */}

      {/* Golden ratio wave (bottom) */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          height: height * 0.3,
          opacity: 0.4 + tension * 0.3,
          filter: `blur(${1 - tension}px)`,
        }}
      >
        <GoldenRatioWave
          activeNotes={activeNotes}
          progress={progress}
          width={width}
          height={Math.round(height * 0.3)}
        />
      </div>

      {/* Note constellation (full screen) */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.8 }}>
        <NoteConstellation
          activeNotes={activeNotes}
          recentNotes={recentNotes}
          width={width}
          height={height}
          tension={tension}
        />
      </div>

      {/* Sacred geometry (left, larger) */}
      <div
        style={{
          position: "absolute",
          left: -20,
          top: height * 0.08,
          opacity: 0.3 + tension * 0.35,
          transform: `scale(${0.95 + tension * 0.12}) rotate(${progress * 15}deg)`,
          transformOrigin: "center center",
        }}
      >
        <SacredGeometry
          activeNotes={activeNotes}
          progress={progress}
          size={Math.round(height * 0.55)}
        />
      </div>

      {/* Fibonacci spiral (right, larger) */}
      <div
        style={{
          position: "absolute",
          right: -10,
          top: height * 0.05,
          opacity: 0.4 + tension * 0.4,
          transform: `scale(${0.95 + tension * 0.1})`,
          transformOrigin: "center center",
        }}
      >
        <FibonacciSpiral
          activeNotes={activeNotes}
          progress={progress}
          size={Math.round(height * 0.6)}
          tension={tension}
        />
      </div>

      {/* === FOREGROUND === */}

      {/* Piano roll (center, prominent) */}
      <div
        style={{
          position: "absolute",
          left: width * 0.12,
          top: height * 0.22,
          width: width * 0.76,
          height: height * 0.5,
          opacity: 0.75 + tension * 0.15,
          borderRadius: 16,
          overflow: "hidden",
          boxShadow: `0 0 ${40 + tension * 40}px rgba(0,0,0,0.4)`,
        }}
      >
        {/* Piano roll backdrop */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.35)",
            backdropFilter: "blur(8px)",
            borderRadius: 16,
          }}
        />
        <PianoRoll
          voices={data.voices}
          currentSec={currentSec}
          width={Math.round(width * 0.76)}
          height={Math.round(height * 0.5)}
          visibleWindowSec={10}
          tension={tension}
        />
      </div>

      {/* Form timeline (top) */}
      <FormTimeline
        sections={data.formSections}
        tempo={data.meta.tempo}
        currentSec={currentSec}
        durationSec={data.meta.durationSec}
      />

      {/* === OVERLAYS === */}

      {/* Vignette */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,${0.5 + (1 - tension) * 0.2}) 100%)`,
          pointerEvents: "none",
        }}
      />

      {/* Center energy pulse */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "45%",
          transform: "translate(-50%, -50%)",
          width: 200 + noteEnergy * 400 + tension * 200,
          height: 200 + noteEnergy * 400 + tension * 200,
          borderRadius: "50%",
          background: `radial-gradient(circle,
            rgba(232,168,56,${noteEnergy * 0.08 + tension * 0.04}) 0%,
            rgba(171,71,188,${noteEnergy * 0.04}) 40%,
            transparent 70%)`,
          pointerEvents: "none",
          transition: "width 0.15s, height 0.15s",
        }}
      />

      {/* Film grain overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.03 + tension * 0.02,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
          backgroundSize: "128px 128px",
          mixBlendMode: "overlay",
          pointerEvents: "none",
        }}
      />

      {/* Title block */}
      <div
        style={{
          position: "absolute",
          bottom: 36,
          left: 48,
          opacity: titleOpacity * masterOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: "'Georgia', 'Palatino Linotype', 'Book Antiqua', serif",
            fontSize: 28,
            color: "rgba(255,255,255,0.55)",
            letterSpacing: 2,
            fontWeight: 400,
          }}
        >
          {data.meta.title}
        </div>
        <div
          style={{
            fontFamily: "'Georgia', serif",
            fontSize: 14,
            color: "rgba(232,168,56,0.4)",
            letterSpacing: 4,
            marginTop: 6,
            textTransform: "uppercase",
          }}
        >
          Generated by Sacred Composer
        </div>
      </div>

      {/* BPM + progress */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 48,
          fontFamily: "'SF Mono', 'Fira Code', monospace",
          fontSize: 13,
          color: "rgba(255,255,255,0.2)",
          letterSpacing: 1,
          textAlign: "right",
        }}
      >
        <div>{data.meta.tempo} BPM</div>
        <div style={{ color: "rgba(232,168,56,0.3)", marginTop: 2 }}>
          {Math.floor(progress * 100)}%
        </div>
      </div>
    </AbsoluteFill>
  );
};
