# S.T.A.L.K.E.R. 2 Teaser (Remotion)

A short kinetic-typography teaser built with [Remotion](https://www.remotion.dev),
in the style of the attached reference clip (Ukrainian title cards, cinematic
color grade, hard cuts, logo reveal).

Network access to fetch new footage from the internet (stalker2.com,
YouTube, Wikipedia, press kits, etc.) is blocked by this environment's
egress policy, so the source footage used here (`public/gameplay-source.mp4`)
is the gameplay clip that was supplied directly. Swap in your own clips by
replacing that file and adjusting the `startSeconds` ranges in
`src/Teaser.tsx` to match clean (caption-free) sections of your new footage.

## Structure

- `src/Teaser.tsx` — the beat-by-beat timeline (footage clips + title cards)
- `src/components/GameClip.tsx` — trims/grades/zooms a segment of the source video
- `src/components/TitleCard.tsx` — word-by-word kinetic caption
- `src/components/Grain.tsx`, `Vignette.tsx`, `FlashCut.tsx` — cinematic finishing touches
- `public/gameplay-source.mp4` — source footage
- `public/audio-bed.aac` — extracted ambient/music bed from the source footage

## Commands

```bash
npm install
npm start      # opens Remotion Studio for live preview/editing
npm run build  # renders out/stalker2-teaser.mp4
```

This project pins the headless Chrome executable used for rendering to the
Playwright-provided Chromium in this sandbox
(`/opt/pw-browsers/chromium_headless_shell-1194/...`) via
`remotion.config.ts`, since Remotion's own browser download is blocked by
the same egress policy. On a normal machine with unrestricted internet
access, delete that `Config.setBrowserExecutable(...)` line and Remotion
will download its own browser automatically.
