import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Kinetic caption: words fade/slide in one by one, matching the
 * "КОЖЕН КРОК — РИЗИК" style title cards from the reference teaser.
 */
export const TitleCard: React.FC<{
  text: string;
  subtext?: string;
  accent?: string;
}> = ({ text, subtext, accent = "#e8e2d0" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: "0.5em",
          fontFamily: "Oswald, Arial Narrow, sans-serif",
          fontWeight: 600,
          fontSize: 64,
          letterSpacing: 2,
          textTransform: "uppercase",
          color: accent,
          textShadow: "0 0 30px rgba(0,0,0,0.9), 0 4px 12px rgba(0,0,0,0.8)",
        }}
      >
        {words.map((word, i) => {
          const delay = i * 4;
          const enter = spring({
            frame: frame - delay,
            fps,
            config: { damping: 200, stiffness: 200, mass: 0.5 },
          });
          const opacity = interpolate(enter, [0, 1], [0, 1]);
          const translateY = interpolate(enter, [0, 1], [18, 0]);

          return (
            <span
              key={i}
              style={{
                opacity,
                transform: `translateY(${translateY}px)`,
                display: "inline-block",
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
      {subtext && (
        <div
          style={{
            marginTop: 18,
            opacity: interpolate(
              spring({ frame: frame - words.length * 4, fps, config: { damping: 200 } }),
              [0, 1],
              [0, 0.85],
            ),
            fontFamily: "Oswald, Arial Narrow, sans-serif",
            fontWeight: 400,
            fontSize: 26,
            letterSpacing: 6,
            textTransform: "uppercase",
            color: accent,
          }}
        >
          {subtext}
        </div>
      )}
    </AbsoluteFill>
  );
};
