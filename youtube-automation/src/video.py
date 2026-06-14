import platform
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image as _PILImage, ImageDraw, ImageFont

# moviepy 1.0.3 uses PIL.Image.ANTIALIAS removed in Pillow 10 — patch it
if not hasattr(_PILImage, "ANTIALIAS"):
    _PILImage.ANTIALIAS = _PILImage.LANCZOS

TARGET_SIZE = (1920, 1080)
FPS = 30

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/opt/homebrew/Caskroom/miniconda/base/envs/yt/lib/python3.11/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _detect_codec():
    if platform.system() != "Darwin":
        return "libx264"
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10
        ).stdout
        if "h264_videotoolbox" in out:
            return "h264_videotoolbox"
    except Exception:
        pass
    return "libx264"


CODEC = _detect_codec()


def _get_font(size: int):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _make_subtitle_clip(text: str, duration: float, start: float, highlight_last: bool = False):
    """PIL-based subtitle — no ImageMagick required."""
    from moviepy.editor import ImageClip

    W, H = TARGET_SIZE
    FONT_SIZE = 64
    PAD = 18
    MAX_W = W - 120

    font = _get_font(FONT_SIZE)

    # Word-wrap
    dummy = ImageDraw.Draw(_PILImage.new("RGB", (W, 10)))
    word_list = text.split()
    lines, line = [], []
    for word in word_list:
        line.append(word)
        if dummy.textbbox((0, 0), " ".join(line), font=font)[2] > MAX_W and len(line) > 1:
            line.pop()
            lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))

    LINE_H = FONT_SIZE + 10
    total_h = len(lines) * LINE_H + PAD * 2

    img = _PILImage.new("RGBA", (W, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    last_word = word_list[-1] if highlight_last and word_list else None

    y = PAD
    for li, ln in enumerate(lines):
        is_last_line = (li == len(lines) - 1)
        bb = draw.textbbox((0, 0), ln, font=font)
        x = (W - (bb[2] - bb[0])) // 2

        if highlight_last and is_last_line and last_word and ln.endswith(last_word):
            ln_words = ln.split()
            if len(ln_words) > 1:
                prefix = " ".join(ln_words[:-1]) + " "
                prefix_w = draw.textbbox((0, 0), prefix, font=font)[2]
                for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2), (0, 3)]:
                    draw.text((x + dx, y + dy), prefix, fill=(0, 0, 0, 210), font=font)
                draw.text((x, y), prefix, fill=(255, 255, 255, 255), font=font)
                x_hw = x + prefix_w
                for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2), (0, 3)]:
                    draw.text((x_hw + dx, y + dy), last_word, fill=(0, 0, 0, 210), font=font)
                draw.text((x_hw, y), last_word, fill=(255, 215, 0, 255), font=font)
            else:
                for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2), (0, 3)]:
                    draw.text((x + dx, y + dy), ln, fill=(0, 0, 0, 210), font=font)
                draw.text((x, y), ln, fill=(255, 215, 0, 255), font=font)
        else:
            for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2), (0, 3)]:
                draw.text((x + dx, y + dy), ln, fill=(0, 0, 0, 210), font=font)
            draw.text((x, y), ln, fill=(255, 255, 255, 255), font=font)
        y += LINE_H

    arr = np.array(img)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3] / 255.0

    clip = ImageClip(rgb)
    mask = ImageClip(alpha, ismask=True)
    clip = (clip
            .set_mask(mask)
            .set_duration(duration)
            .set_start(start)
            .set_position(("center", H - total_h - 70)))
    return clip


def _subtitle_clips(words: list, duration: float):
    """Kinetic text: each word appears one by one, new word highlighted in gold."""
    clips = []
    CHUNK = 5
    groups = []
    group = []
    for w in words:
        group.append(w)
        if len(group) >= CHUNK:
            groups.append(group)
            group = []
    if group:
        groups.append(group)

    for g in groups:
        group_end = min(g[-1]["start"] + g[-1]["duration"] + 0.3, duration)
        for n in range(len(g)):
            word_start = g[n]["start"]
            word_end = g[n + 1]["start"] if n + 1 < len(g) else group_end
            dur = word_end - word_start
            if dur < 0.05:
                continue
            partial = " ".join(w["word"] for w in g[:n + 1])
            try:
                clips.append(_make_subtitle_clip(partial, dur, word_start, highlight_last=True))
            except Exception as e:
                print(f"  subtitle error: {e}")
    return clips


class _ProgressLogger:
    """Simple % progress output for moviepy write_videofile."""
    def __init__(self):
        self._last = -1

    def __call__(self, *args, **kwargs):
        pass

    # proglog interface
    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == "t" and attr == "index":
            total = getattr(self, "_total", None)
            if total and total > 0:
                pct = int(100 * value / total)
                if pct != self._last:
                    self._last = pct
                    print(f"\r  Encoding: {pct}%", end="", flush=True)

    def callback(self, **changes):
        for bar_name, bar in changes.get("bars", {}).items():
            if bar_name == "t":
                self._total = bar.get("total", 0)
        self.bars_callback(
            "t", "index",
            changes.get("bars", {}).get("t", {}).get("index", 0)
        )


def assemble_video(broll_clips: list, audio_path: Path, words: list,
                   output_path: Path, bgm_path: Path = None):
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, ColorClip,
        concatenate_videoclips, CompositeVideoClip,
    )
    import proglog

    audio = AudioFileClip(str(audio_path))
    total = audio.duration

    print(f"  Audio duration: {total:.1f}s")

    bg_clips = []
    current = 0.0
    if broll_clips:
        idx = 0
        while current < total:
            path = broll_clips[idx % len(broll_clips)]
            try:
                # Clips are already 1920x1080 from ffmpeg transcode — no resize needed
                c = VideoFileClip(str(path), audio=False)
                dur = c.duration
                remaining = total - current
                if dur > remaining:
                    c = c.subclip(0, remaining)
                    dur = remaining
                bg_clips.append(c.set_start(current))
                current += dur
            except Exception as e:
                print(f"  Clip error ({path.name}): {e}")
            idx += 1
            if idx > 500:
                break

    if not bg_clips:
        bg_clips = [ColorClip(TARGET_SIZE, color=(10, 10, 25), duration=total)]

    background = concatenate_videoclips(bg_clips, method="compose").set_audio(audio)

    # Dark overlay
    overlay = ColorClip(TARGET_SIZE, color=(0, 0, 0), duration=total).set_opacity(0.20)

    print(f"  Building {len(words)} subtitle clips...")
    sub_clips = _subtitle_clips(words, total)
    print(f"  {len(sub_clips)} subtitle clips ready")

    final = CompositeVideoClip([background, overlay] + sub_clips, size=TARGET_SIZE)

    if bgm_path and bgm_path.exists():
        from moviepy.editor import AudioFileClip as AFC
        from moviepy.audio.AudioClip import CompositeAudioClip
        bgm = AFC(str(bgm_path)).subclip(0, total).volumex(0.08)
        final = final.set_audio(CompositeAudioClip([audio, bgm]))

    logger = proglog.TqdmProgressBarLogger(print_messages=False)

    if CODEC == "h264_videotoolbox":
        print(f"  Using Apple Silicon encoder (h264_videotoolbox)")
        final.write_videofile(
            str(output_path),
            fps=FPS, codec=CODEC, audio_codec="aac", threads=4,
            logger=logger,
            ffmpeg_params=["-b:v", "8000k", "-pix_fmt", "yuv420p"],
        )
    else:
        final.write_videofile(
            str(output_path),
            fps=FPS, codec=CODEC, audio_codec="aac",
            preset="medium", threads=4, logger=logger,
        )

    print()
    for c in bg_clips:
        try:
            c.close()
        except Exception:
            pass
    audio.close()
    return output_path
