import React from "react";
import { AbsoluteFill } from "remotion";

export const Vignette: React.FC<{
  strength?: number;
  bottomFade?: number;
}> = ({ strength = 0.55, bottomFade = 0 }) => {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,${strength}) 100%)`,
        }}
      />
      {bottomFade > 0 && (
        <AbsoluteFill
          style={{
            background: `linear-gradient(to bottom, rgba(0,0,0,0) 65%, rgba(0,0,0,${bottomFade}) 100%)`,
          }}
        />
      )}
    </AbsoluteFill>
  );
};
