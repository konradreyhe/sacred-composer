import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig, staticFile } from "remotion";
import { PianoRoll } from "./components/PianoRoll";
import { FormTimeline } from "./components/FormTimeline";
import { FibonacciSpiral } from "./components/FibonacciSpiral";
import { CompositionData, frameToSec, getActiveNotes } from "./lib/timing";

export const SacredComposition: React.FC<{ data: CompositionData }> = ({
  data,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentSec = frameToSec(frame, fps);
  const activeNotes = getActiveNotes(data.voices, currentSec);
  const progress = currentSec / data.meta.durationSec;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A12" }}>
      {/* Audio track — place a composition.wav in public/ */}
      <Audio src={staticFile("composition.wav")} />

      {/* Form section labels along the top */}
      <FormTimeline
        sections={data.formSections}
        tempo={data.meta.tempo}
        currentSec={currentSec}
        durationSec={data.meta.durationSec}
      />

      {/* Fibonacci spiral behind the piano roll */}
      <div style={{ position: "absolute", right: 40, top: 140, opacity: 0.6 }}>
        <FibonacciSpiral
          activeNotes={activeNotes}
          progress={progress}
          size={360}
        />
      </div>

      {/* Scrolling piano roll — main visualization */}
      <div style={{ position: "absolute", left: 0, top: 120, width: "100%", height: 800 }}>
        <PianoRoll
          voices={data.voices}
          currentSec={currentSec}
          width={1920}
          height={800}
          visibleWindowSec={8}
        />
      </div>

      {/* Title overlay */}
      <div
        style={{
          position: "absolute",
          bottom: 32,
          left: 40,
          fontFamily: "Georgia, serif",
          fontSize: 28,
          color: "rgba(255,255,255,0.5)",
        }}
      >
        {data.meta.title} — {data.meta.tempo} BPM
      </div>
    </AbsoluteFill>
  );
};
