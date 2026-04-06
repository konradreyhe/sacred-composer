import { interpolate } from "remotion";
import { FormSection } from "../lib/timing";

interface Props {
  sections: FormSection[];
  tempo: number;
  currentSec: number;
  durationSec: number;
}

/** Convert bar number to seconds (assuming 4/4 time). */
function barToSec(bar: number, tempo: number): number {
  return (bar * 4 * 60) / tempo;
}

export const FormTimeline: React.FC<Props> = ({
  sections,
  tempo,
  currentSec,
  durationSec,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: 100,
        display: "flex",
        alignItems: "center",
        padding: "0 40px",
        gap: 4,
      }}
    >
      {sections.map((s, i) => {
        const startSec = s.startBar != null
          ? barToSec(s.startBar, tempo)
          : (s.startBeat ?? 0) * 60 / tempo;
        const endSec = s.endBar != null
          ? barToSec(s.endBar, tempo)
          : (s.endBeat ?? 0) * 60 / tempo;
        const sectionDur = endSec - startSec;
        const widthPct = (sectionDur / durationSec) * 100;

        const isActive = currentSec >= startSec && currentSec < endSec;
        const progress = isActive
          ? (currentSec - startSec) / sectionDur
          : currentSec >= endSec
          ? 1
          : 0;

        const opacity = interpolate(
          isActive ? 1 : 0,
          [0, 1],
          [0.3, 1]
        );

        return (
          <div
            key={i}
            style={{
              width: `${widthPct}%`,
              height: 48,
              position: "relative",
              borderRadius: 6,
              overflow: "hidden",
              background: "rgba(255,255,255,0.05)",
              opacity,
              transition: "opacity 0.3s",
            }}
          >
            {/* Progress fill */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                height: "100%",
                width: `${progress * 100}%`,
                background: isActive
                  ? "rgba(232,168,56,0.3)"
                  : "rgba(255,255,255,0.08)",
                borderRadius: 6,
              }}
            />
            {/* Label */}
            <span
              style={{
                position: "relative",
                zIndex: 1,
                display: "block",
                padding: "12px 14px",
                fontFamily: "Georgia, serif",
                fontSize: 16,
                color: isActive ? "#E8A838" : "rgba(255,255,255,0.5)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {s.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};
