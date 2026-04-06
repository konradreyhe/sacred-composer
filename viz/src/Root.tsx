import { Composition } from "remotion";
import { SacredComposition } from "./SacredComposition";
import compositionData from "./data/sample.json";
import track01 from "./data/track_01.json";
import track02 from "./data/track_02.json";
import track03 from "./data/track_03.json";
import track04 from "./data/track_04.json";
import track05 from "./data/track_05.json";
import track06 from "./data/track_06.json";
import track07 from "./data/track_07.json";
import track08 from "./data/track_08.json";
import track09 from "./data/track_09.json";

const albumTracks = [
  { id: "Track01_Threshold", data: track01 },
  { id: "Track02_InfiniteSeries", data: track02 },
  { id: "Track03_GoldenSpiral", data: track03 },
  { id: "Track04_HarmonicSeries", data: track04 },
  { id: "Track05_LogisticMap", data: track05 },
  { id: "Track06_MandelbrotBoundary", data: track06 },
  { id: "Track07_RosslerAttractor", data: track07 },
  { id: "Track08_CantorsDust", data: track08 },
  { id: "Track09_ZipfsLaw", data: track09 },
];

export const RemotionRoot: React.FC = () => {
  const fps = compositionData.meta.fps || 60;
  const durationInFrames = Math.ceil(compositionData.meta.durationSec * fps);

  return (
    <>
      {/* Original demo composition */}
      <Composition
        id="SacredComposition"
        component={SacredComposition}
        durationInFrames={durationInFrames}
        fps={fps}
        width={1920}
        height={1080}
        defaultProps={{ data: compositionData }}
      />

      {/* Album tracks */}
      {albumTracks.map(({ id, data }) => {
        const trackFps = data.meta.fps || 60;
        const trackFrames = Math.ceil(data.meta.durationSec * trackFps);
        return (
          <Composition
            key={id}
            id={id}
            component={SacredComposition}
            durationInFrames={trackFrames}
            fps={trackFps}
            width={1920}
            height={1080}
            defaultProps={{ data }}
          />
        );
      })}
    </>
  );
};
