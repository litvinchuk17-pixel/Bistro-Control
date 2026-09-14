import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

/** A quick white/black flash frame used between hard cuts for a kinetic-trailer feel. */
export const FlashCut: React.FC<{ color?: string }> = ({ color = "#fff" }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 1, 3], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{ backgroundColor: color, opacity, pointerEvents: "none" }}
    />
  );
};
