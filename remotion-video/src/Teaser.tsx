import React from "react";
import { AbsoluteFill, Audio, Series, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { GameClip } from "./components/GameClip";
import { TitleCard } from "./components/TitleCard";
import { Grain } from "./components/Grain";
import { Vignette } from "./components/Vignette";
import { FlashCut } from "./components/FlashCut";

export const TEASER_FPS = 30;

const FLASH_LEN = 3;

type Beat =
  | {
      kind: "clip";
      durationInFrames: number;
      startSeconds: number;
      playbackRate: number;
      grade: "green" | "amber" | "red" | "none";
      text?: string;
      subtext?: string;
      textDelay?: number;
    }
  | {
      kind: "card";
      durationInFrames: number;
      text: string;
      subtext?: string;
      danger?: boolean;
    };

const BEATS: Beat[] = [
  {
    kind: "clip",
    durationInFrames: 75,
    startSeconds: 0.2,
    playbackRate: 0.88,
    grade: "green",
    text: "ЗОНА НЕ ПРОЩАЄ",
    textDelay: 18,
  },
  {
    kind: "clip",
    durationInFrames: 40,
    startSeconds: 2.2,
    playbackRate: 0.6,
    grade: "green",
  },
  {
    kind: "clip",
    durationInFrames: 120,
    startSeconds: 9.0,
    playbackRate: 1.075,
    grade: "amber",
    text: "КОЖЕН ВИСТРІЛ ВАЖИТЬ",
    textDelay: 15,
  },
  {
    kind: "clip",
    durationInFrames: 115,
    startSeconds: 16.3,
    playbackRate: 1.043,
    grade: "green",
    text: "ВІДСТУПУ НЕМАЄ",
    textDelay: 15,
  },
  {
    kind: "card",
    durationInFrames: 55,
    text: "ОДНА ПОМИЛКА —",
    subtext: "І ГРІ КІНЕЦЬ",
    danger: true,
  },
  {
    kind: "clip",
    durationInFrames: 90,
    startSeconds: 22.0,
    playbackRate: 0.533,
    grade: "red",
    text: "ЦІЛЬСЯ. ДИХАЙ. ВИЖИВИ.",
    textDelay: 12,
  },
  {
    kind: "clip",
    durationInFrames: 90,
    startSeconds: 25.5,
    playbackRate: 0.667,
    grade: "none",
  },
];

const HOLD_FRAMES = 30;

export const TEASER_DURATION_IN_FRAMES =
  BEATS.reduce((sum, b) => sum + b.durationInFrames, 0) +
  (BEATS.length - 1) * FLASH_LEN +
  HOLD_FRAMES;

const DangerPulse: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = interpolate(frame % 20, [0, 10, 20], [0.15, 0.4, 0.15]);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000",
      }}
    >
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at center, rgba(120,0,0,${pulse}) 0%, rgba(0,0,0,0) 70%)`,
        }}
      />
    </AbsoluteFill>
  );
};

const BeatContent: React.FC<{ beat: Beat }> = ({ beat }) => {
  const frame = useCurrentFrame();

  const localOpacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
  });

  if (beat.kind === "card") {
    return (
      <AbsoluteFill style={{ opacity: localOpacity }}>
        <DangerPulse />
        <TitleCard text={beat.text} subtext={beat.subtext} accent="#ff5a4d" />
      </AbsoluteFill>
    );
  }

  const textDelay = beat.textDelay ?? 12;

  return (
    <AbsoluteFill style={{ opacity: localOpacity }}>
      <GameClip
        startSeconds={beat.startSeconds}
        durationInFrames={beat.durationInFrames}
        playbackRate={beat.playbackRate}
        grade={beat.grade}
      />
      <Vignette
        strength={0.5}
        bottomFade={beat.startSeconds === 25.5 ? 0.85 : 0}
      />
      {beat.text && (
        <AbsoluteFill style={{ opacity: interpolate(frame, [textDelay, textDelay + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
          <TitleCard text={beat.text} subtext={beat.subtext} />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

export const Teaser: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const endFade = interpolate(
    frame,
    [durationInFrames - HOLD_FRAMES, durationInFrames - 1],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const startFade = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Audio src={staticFile("audio-bed.aac")} volume={0.9} />

      <Series>
        {BEATS.map((beat, i) => (
          <React.Fragment key={i}>
            <Series.Sequence durationInFrames={beat.durationInFrames}>
              <BeatContent beat={beat} />
            </Series.Sequence>
            {i < BEATS.length - 1 && (
              <Series.Sequence durationInFrames={FLASH_LEN}>
                <FlashCut color="#000" />
              </Series.Sequence>
            )}
          </React.Fragment>
        ))}
        <Series.Sequence durationInFrames={HOLD_FRAMES}>
          <AbsoluteFill style={{ backgroundColor: "#000" }} />
        </Series.Sequence>
      </Series>

      <Grain opacity={0.05} />

      <AbsoluteFill
        style={{ backgroundColor: "#000", opacity: 1 - Math.min(startFade, endFade), pointerEvents: "none" }}
      />
    </AbsoluteFill>
  );
};
