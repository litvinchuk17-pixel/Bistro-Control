from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np

SOURCE = "/root/.claude/uploads/cb6d978d-3c5c-576b-978b-eef8f7ca0fd6/bc12695b-48eafa7ef6f810a2d9fc9d07ce1fdad9505939c04155195f267b11dfac91337c.mp4"
OUTPUT = "/home/user/Bistro-Control/buffett_birth.mp4"

FONT_PATH = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"
FONT_BOLD  = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
W, H = 716, 1284
TOTAL = 75.0

# (start, end, text, bold)
SEGMENTS = [
    (0.0,  3.0,  "Америка. 1930 год.", True),
    (3.5,  7.5,  "Великая Депрессия\nвыжигает страну дотла.", False),
    (8.0,  11.5, "Банки закрываются\nодин за другим.", False),
    (12.0, 15.0, "Фермы пустеют.\nЗаводы стоят.", False),
    (15.5, 21.0, "Миллионы людей стоят\nв очередях за хлебом —", False),
    (21.5, 26.5, "и не знают,\nбудет ли хлеб завтра.", False),
    (28.0, 33.0, "В этот мир —\nв маленьком деревянном доме", False),
    (33.5, 38.0, "на улице Данлэп\nв Омахе, Небраска —", False),
    (38.5, 45.0, "тридцатого августа\nтысяча девятьсот\nтридцатого года", False),
    (45.5, 49.0, "рождается мальчик.", False),
    (50.5, 55.5, "Его зовут\nУоррен Эдвард Баффет.", True),
    (57.5, 61.0, "Он ещё не знает,", False),
    (61.5, 67.0, "что однажды станет\nбогатейшим человеком\nна Земле.", False),
    (67.5, 71.0, "Он просто плачет.", False),
    (71.5, 75.0, "Как все дети.", False),
]


def make_text_frame(text, bold=False, font_size=52):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    path = FONT_BOLD if bold else FONT_PATH
    font = ImageFont.truetype(path, font_size)

    lines = text.split("\n")
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = font_size * 0.3
    total_h = sum(line_heights) + line_spacing * (len(lines) - 1)
    y_start = H * 0.72 - total_h / 2

    shadow_offset = 3
    for i, line in enumerate(lines):
        x = (W - line_widths[i]) / 2
        y = y_start + i * (line_heights[i] + line_spacing)

        # Shadow
        draw.text((x + shadow_offset, y + shadow_offset), line, font=font,
                  fill=(0, 0, 0, 180))
        # Main text
        draw.text((x, y), line, font=font, fill=(255, 248, 220, 255))

    return np.array(img)


def make_fade_clip(text, start, end, bold=False):
    duration = end - start
    frame = make_text_frame(text, bold=bold)

    def make_frame(t):
        fade_in  = min(t / 0.6, 1.0)
        fade_out = min((duration - t) / 0.6, 1.0)
        alpha = min(fade_in, fade_out)
        out = frame.copy()
        out[:, :, 3] = (out[:, :, 3] * alpha).astype(np.uint8)
        return out

    clip = ImageClip(frame, duration=duration)
    clip = clip.with_effects([])

    def frame_with_fade(get_frame, t):
        fade_in  = min(t / 0.6, 1.0)
        fade_out = min((duration - t) / 0.6, 1.0)
        alpha = min(fade_in, fade_out)
        f = frame.copy()
        f[:, :, 3] = (f[:, :, 3] * alpha).astype(np.uint8)
        return f

    from moviepy import VideoClip
    text_clip = VideoClip(lambda t: frame_with_fade(None, t), duration=duration, is_mask=False)
    text_clip = text_clip.with_start(start)
    return text_clip


# Load and loop background
bg = VideoFileClip(SOURCE)
loops_needed = int(np.ceil(TOTAL / bg.duration))
from moviepy import concatenate_videoclips
bg_looped = concatenate_videoclips([bg] * loops_needed).subclipped(0, TOTAL)

# Create text clips
text_clips = [make_fade_clip(text, start, end, bold)
              for start, end, text, bold in SEGMENTS]

# Composite
final = CompositeVideoClip([bg_looped] + text_clips)
final = final.subclipped(0, TOTAL)

print("Rendering…")
final.write_videofile(
    OUTPUT,
    fps=24,
    codec="libx264",
    audio=False,
    preset="fast",
    ffmpeg_params=["-crf", "23"],
)
print("Done:", OUTPUT)
