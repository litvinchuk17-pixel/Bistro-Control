import React from "react";
import { Composition } from "remotion";
import { Teaser, TEASER_FPS, TEASER_DURATION_IN_FRAMES } from "./Teaser";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Stalker2Teaser"
        component={Teaser}
        durationInFrames={TEASER_DURATION_IN_FRAMES}
        fps={TEASER_FPS}
        width={1920}
        height={1080}
      />
    </>
  );
};
