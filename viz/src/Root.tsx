import { Composition } from "remotion";
import { SacredComposition } from "./SacredComposition";
import compositionData from "./data/sample.json";

export const RemotionRoot: React.FC = () => {
  const fps = compositionData.meta.fps || 60;
  const durationInFrames = Math.ceil(compositionData.meta.durationSec * fps);

  return (
    <>
      <Composition
        id="SacredComposition"
        component={SacredComposition}
        durationInFrames={durationInFrames}
        fps={fps}
        width={1920}
        height={1080}
        defaultProps={{ data: compositionData }}
      />
    </>
  );
};
