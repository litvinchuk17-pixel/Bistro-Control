from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pathlib import Path
import requests
from io import BytesIO

SIZE = (1280, 720)
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def _load_font(size: int):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def create_thumbnail(title: str, bg_url: str = None, output_path: Path = None) -> Path:
    img = Image.new("RGB", SIZE, (15, 15, 35))

    if bg_url:
        try:
            resp = requests.get(bg_url, timeout=10)
            bg = Image.open(BytesIO(resp.content)).convert("RGB").resize(SIZE)
            bg = ImageEnhance.Brightness(bg).enhance(0.35)
            img.paste(bg)
        except Exception:
            pass

    draw = ImageDraw.Draw(img)

    # gradient overlay bottom half
    for y in range(SIZE[1] // 2, SIZE[1]):
        alpha = int(200 * (y - SIZE[1] // 2) / (SIZE[1] // 2))
        draw.line([(0, y), (SIZE[0], y)], fill=(0, 0, 0))

    font = _load_font(72)
    words = title.upper().split()
    lines, line = [], []
    for word in words:
        line.append(word)
        bbox = draw.textbbox((0, 0), " ".join(line), font=font)
        if bbox[2] > SIZE[0] - 100 and len(line) > 1:
            line.pop()
            lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))

    total_h = len(lines) * 82
    y = (SIZE[1] - total_h) // 2 + 80
    for text in lines:
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (SIZE[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, y + 3), text, fill=(0, 0, 0), font=font)
        draw.text((x, y), text, fill=(255, 220, 50), font=font)
        y += 82

    if output_path is None:
        output_path = Path("thumbnail.jpg")
    img.save(output_path, "JPEG", quality=95)
    return output_path
