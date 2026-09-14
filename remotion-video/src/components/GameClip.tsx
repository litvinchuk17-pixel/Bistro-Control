import React from "react";
import { AbsoluteFill, OffthreadVideo, interpolate, staticFile, useCurrentFrame } from "remotion";

const SOURCE = "gameplay-source.mp4";
const SOURCE_FPS = 30;

export const GameClip: React.FC<{
  /** Start time in the source footage, in seconds. */
  startSeconds: number;
  /** How long this clip plays for on the timeline, in frames (at comp fps). */
  durationInFrames: number;
  /** Playback speed relative to source (1 = normal, <1 = slow motion). */
  playbackRate?: number;
  /** Subtle continuous zoom for a "Ken Burns" push-in feel. */
  zoom?: boolean;
  grade?: "green" | "amber" | "red" | "none";
}> = ({ startSeconds, durationInFrames, playbackRate = 1, zoom = true, grade = "green" }) => {
  const frame = useCurrentFrame();

  const scale = zoom
    ? interpolate(frame, [0, durationInFrames], [1.04, 1.14], {
        extrapolateRight: "clamp",
      })
    : 1.04;

  const filter =
    grade === "green"
      ? "contrast(1.15) saturate(0.55) brightness(0.85) sepia(0.12) hue-rotate(45deg)"
      : grade === "amber"
        ? "contrast(1.15) saturate(0.6) brightness(0.95) sepia(0.25) hue-rotate(-10deg)"
        : grade === "red"
          ? "contrast(1.25) saturate(0.5) brightness(0.8) sepia(0.3) hue-rotate(-40deg)"
          : "none";

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${scale})`, filter }}>
        <OffthreadVideo
          src={staticFile(SOURCE)}
          trimBefore={Math.round(startSeconds * SOURCE_FPS)}
          playbackRate={playbackRate}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
