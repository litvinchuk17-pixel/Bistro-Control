import platform
import subprocess
from pathlib import Path

TARGET_SIZE = (1920, 1080)
FPS = 30


def _detect_codec():
    """Use h264_videotoolbox on Apple Silicon, libx264 elsewhere."""
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


def _subtitle_clips(words: list, duration: float):
    from moviepy.editor import TextClip
    clips = []
    chunk, chunk_words = [], []
    for w in words:
        chunk_words.append(w)
        if len(chunk_words) >= 7:
            chunk.append(chunk_words)
            chunk_words = []
    if chunk_words:
        chunk.append(chunk_words)

    for group in chunk:
        text = " ".join(w["word"] for w in group)
        start = group[0]["start"]
        end = group[-1]["start"] + group[-1]["duration"]
        if end > duration:
            end = duration
        dur = end - start
        if dur <= 0:
            continue
        try:
            tc = (
                TextClip(
                    text,
                    fontsize=56,
                    color="white",
                    font="DejaVu-Sans-Bold",
                    stroke_color="black",
                    stroke_width=2,
                    method="caption",
                    size=(1600, None),
                )
                .set_start(start)
                .set_duration(dur)
                .set_position(("center", 880))
            )
            clips.append(tc)
        except Exception:
            pass
    return clips


def assemble_video(broll_clips: list, audio_path: Path, words: list, output_path: Path, bgm_path: Path = None):
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, ColorClip,
        concatenate_videoclips, CompositeVideoClip,
    )

    audio = AudioFileClip(str(audio_path))
    total = audio.duration

    def _ken_burns(clip, zoom_start=1.0, zoom_end=1.08):
        """Slow zoom-in effect."""
        return clip.fl_time(lambda t: t).resize(
            lambda t: zoom_start + (zoom_end - zoom_start) * (t / max(clip.duration, 0.1))
        ).crop(
            x_center=TARGET_SIZE[0] / 2,
            y_center=TARGET_SIZE[1] / 2,
            width=TARGET_SIZE[0],
            height=TARGET_SIZE[1],
        )

    bg_clips = []
    current = 0.0
    if broll_clips:
        idx = 0
        while current < total:
            path = broll_clips[idx % len(broll_clips)]
            try:
                c = VideoFileClip(str(path)).without_audio().resize(TARGET_SIZE)
                remaining = total - current
                if c.duration > remaining:
                    c = c.subclip(0, remaining)
                c = _ken_burns(c)
                bg_clips.append(c.set_start(current))
                current += c.duration
            except Exception as e:
                print(f"  Clip load error ({path.name}): {e}")
            idx += 1
            if idx > len(broll_clips) * 2:
                break

    if not bg_clips:
        bg_clips = [ColorClip(TARGET_SIZE, color=(10, 10, 25), duration=total)]

    background = concatenate_videoclips(bg_clips, method="compose").set_audio(audio)

    sub_clips = _subtitle_clips(words, total)
    final = CompositeVideoClip([background] + sub_clips, size=TARGET_SIZE)

    if bgm_path and bgm_path.exists():
        from moviepy.editor import AudioFileClip as AFC
        from moviepy.audio.AudioClip import CompositeAudioClip
        bgm = AFC(str(bgm_path)).subclip(0, total).volumex(0.07)
        final = final.set_audio(CompositeAudioClip([audio, bgm]))

    if CODEC == "h264_videotoolbox":
        print(f"  Using Apple Silicon hardware encoder (h264_videotoolbox)")
        final.write_videofile(
            str(output_path),
            fps=FPS,
            codec=CODEC,
            audio_codec="aac",
            threads=4,
            logger=None,
            ffmpeg_params=["-b:v", "8000k", "-pix_fmt", "yuv420p"],
        )
    else:
        final.write_videofile(
            str(output_path),
            fps=FPS,
            codec=CODEC,
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,
        )

    for c in bg_clips:
        try:
            c.close()
        except Exception:
            pass
    audio.close()
    return output_path
