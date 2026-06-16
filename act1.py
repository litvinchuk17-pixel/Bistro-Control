#!/usr/bin/env python3
"""
ACT 1 — HOOK: "The man who called every crash"
0:00 – 1:30  (90 seconds)
Netflix doc style, 1280×536, 24fps
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from cinematic import (
    Timeline, render,
    make_ken_burns, make_quote_card, make_title_card,
    grade_netflix, add_vignette, add_grain,
    ease_in_out, ease_out, ease_in,
    FONT_SANS, FONT_SANS_BOLD, FONT_SERIF_IT,
)

W, H   = 1280, 536
FPS    = 24
OUTPUT = "/home/user/Bistro-Control/act1_hook.mp4"

PHOTO_CRASH   = "/home/user/Bistro-Control/photo_1.webp"   # NYSE crash scene
PHOTO_DALIO   = "/home/user/Bistro-Control/photo_2.webp"   # Ray Dalio portrait

rng   = np.random.default_rng(17)
GRAIN = rng.normal(0, 1.0, (H, W, 3)).astype(np.float32)

_y, _x = np.mgrid[0:H, 0:W]
VIG = np.clip(1.0 - (np.sqrt(((_x-W/2)/(W/2))**2 +
                              ((_y-H/2)/(H/2)*1.15)**2) - 0.42)*1.9,
              0.16, 1.0).astype(np.float32)

def lp(a, b, f):
    f = max(0., min(1., f))
    return tuple(int(x+(y-x)*f) for x, y in zip(a, b))

def ease(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)


# ════════════════════════════════════════════════════════════════
# TEXT OVERLAY SYSTEM — draws subtitle-style captions on frames
# ════════════════════════════════════════════════════════════════

def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

# Pre-render caption strips (text drawn on transparent RGBA)
_caption_cache = {}

def _make_caption_strip(text, font_size=32):
    key = (text, font_size)
    if key in _caption_cache:
        return _caption_cache[key]
    font  = _load_font(FONT_SANS, font_size)
    dummy = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    # Wrap text to 80% width
    max_w = int(W * 0.82)
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bb = dummy.textbbox((0,0), test, font=font)
        if bb[2]-bb[0] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)

    lh = font_size + int(font_size * 0.38)
    total_h = len(lines) * lh + 20
    strip = Image.new("RGBA", (W, total_h), (0,0,0,0))
    d     = ImageDraw.Draw(strip)
    for i, line in enumerate(lines):
        bb = d.textbbox((0,0), line, font=font)
        x  = (W - (bb[2]-bb[0])) // 2
        y  = i * lh + 10
        # shadow
        d.text((x+2, y+2), line, font=font, fill=(0,0,0,160))
        d.text((x,   y),   line, font=font, fill=(240,235,220,255))
    _caption_cache[key] = (strip, total_h)
    return strip, total_h


def overlay_caption(base_arr, text, alpha=1.0, font_size=30,
                    y_frac=0.83):
    """Composite a text caption onto base_arr (H,W,3 uint8)."""
    strip, sh = _make_caption_strip(text, font_size)
    # Semi-dark bar behind text
    bar_arr  = np.array(strip)
    y_pos    = int(H * y_frac)
    y_end    = min(H, y_pos + sh)
    actual_h = y_end - y_pos

    img = Image.fromarray(base_arr, "RGB").convert("RGBA")
    # Dark bar
    bar = Image.new("RGBA", (W, actual_h), (0,0,0,0))
    bda = ImageDraw.Draw(bar)
    bda.rectangle([0, 0, W, actual_h], fill=(8,8,12,int(155*alpha)))
    img.paste(bar, (0, y_pos), bar)
    # Text
    strip_alpha = strip.copy()
    sa_arr = np.array(strip_alpha)
    sa_arr[:,:,3] = (sa_arr[:,:,3] * alpha).astype(np.uint8)
    strip_alpha = Image.fromarray(sa_arr)
    img.paste(strip_alpha, (0, y_pos), strip_alpha)
    return np.array(img.convert("RGB"))


# ════════════════════════════════════════════════════════════════
# STAT GRAPHIC — "Bridgewater +14% vs S&P -37%"
# ════════════════════════════════════════════════════════════════

def make_stat_graphic(duration=8.0):
    """Bold animated stat comparison card."""

    # Pre-render static background
    bg = Image.new("RGB", (W, H), (6, 6, 10))
    d  = ImageDraw.Draw(bg)

    # Thin amber top accent line
    d.rectangle([0, 0, W, 3], fill=(210, 158, 50))

    f_big  = _load_font(FONT_SANS_BOLD, 88)
    f_med  = _load_font(FONT_SANS_BOLD, 36)
    f_sm   = _load_font(FONT_SANS,      22)
    f_year = _load_font(FONT_SANS_BOLD, 20)

    # Labels
    BW_label = "BRIDGEWATER"
    SP_label = "S&P 500"
    BW_val   = "+14%"
    SP_val   = "−37%"
    year_txt = "2008 Financial Crisis"

    # Divider
    d.line([W//2, 80, W//2, H-80], fill=(50,50,60), width=1)

    static_bg = np.array(bg)

    def frame(t):
        prog = ease(min(t / 1.2, 1.0))   # numbers count-up feel
        arr  = static_bg.copy().astype(np.float32)

        # Year label
        img2 = Image.fromarray(arr.astype(np.uint8))
        d2   = ImageDraw.Draw(img2)

        # Year banner top center
        yb = d2.textbbox((0,0), year_txt, font=f_year)
        d2.text(((W-(yb[2]-yb[0]))//2, 18), year_txt, font=f_year,
                fill=(180, 150, 80))

        # LEFT — Bridgewater (green)
        # Label
        blb = d2.textbbox((0,0), BW_label, font=f_sm)
        d2.text(((W//2 - (blb[2]-blb[0]))//2, 110), BW_label,
                font=f_sm, fill=(140,140,150))

        # Big number (animate count-up from 0 to +14)
        bw_num = f"+{int(14*prog)}%"
        bvb = d2.textbbox((0,0), bw_num, font=f_big)
        d2.text(((W//2 - (bvb[2]-bvb[0]))//2, 155), bw_num,
                font=f_big, fill=(80, 210, 120))

        # Sub
        sub_bw = "PROFIT WHILE WORLD BURNED"
        sbb = d2.textbbox((0,0), sub_bw, font=f_year)
        d2.text(((W//2 - (sbb[2]-sbb[0]))//2, 290), sub_bw,
                font=f_year, fill=(80,170,100))

        # RIGHT — S&P (red)
        spb = d2.textbbox((0,0), SP_label, font=f_sm)
        d2.text((W//2 + (W//2 - (spb[2]-spb[0]))//2, 110), SP_label,
                font=f_sm, fill=(140,140,150))

        sp_num = f"−{int(37*prog)}%"
        svb = d2.textbbox((0,0), sp_num, font=f_big)
        d2.text((W//2 + (W//2 - (svb[2]-svb[0]))//2, 155), sp_num,
                font=f_big, fill=(220, 65, 55))

        sub_sp = "MARKET COLLAPSE"
        ssb = d2.textbbox((0,0), sub_sp, font=f_year)
        d2.text((W//2 + (W//2 - (ssb[2]-ssb[0]))//2, 290), sub_sp,
                font=f_year, fill=(180, 55, 50))

        # VS badge (center)
        vs_font = _load_font(FONT_SANS_BOLD, 28)
        vsb = d2.textbbox((0,0), "VS", font=vs_font)
        vx  = (W - (vsb[2]-vsb[0]))//2
        vy  = 210
        d2.ellipse([vx-22, vy-10, vx+(vsb[2]-vsb[0])+22, vy+38],
                   fill=(30,30,40))
        d2.text((vx, vy), "VS", font=vs_font, fill=(200,190,170))

        # Fade in overall
        fi = min(t/0.5, 1.0)
        fo = min((duration-t)/0.5, 1.0)
        alpha = ease(min(fi, fo))

        result = np.array(img2).astype(np.float32)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        result = np.clip(result + GRAIN * 4.5, 0, 255)
        result = result * alpha
        return np.clip(result, 0, 255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# SCRIPTED CAPTION SEGMENTS
# Each tuple: (start, end, text)  — times relative to clip start
# ════════════════════════════════════════════════════════════════

CRASH_CAPTIONS = [
    (0.5,  7.5,  "In 2008, while the entire global financial system was collapsing —"),
    (7.5,  14.0, "one man was making money."),
    (14.5, 22.0, "Not a little money. His fund returned 14% while the market lost 37%."),
    (22.0, 30.0, "He had predicted the crash years in advance. He warned the US government."),
    (30.0, 36.0, "Nobody listened."),
]

DALIO_CAPTIONS = [
    (0.5,  8.0,  "That man built the world's largest hedge fund"),
    (8.0,  15.0, "from a two-bedroom apartment in New York City."),
    (15.5, 22.0, "He started with nothing. He lost everything — twice."),
    (22.0, 29.0, "And he came back both times stronger."),
]


def make_captioned_photo(photo_path, duration, captions,
                         zoom_start=1.0, zoom_end=1.10,
                         pan_start=(0.5,0.5), pan_end=(0.52,0.52),
                         grade="netflix"):
    """Ken Burns photo with timed caption overlays."""
    kb = make_ken_burns(photo_path, duration, W, H,
                        zoom_start, zoom_end, pan_start, pan_end,
                        grade, fade_in=0.5, fade_out=0.5)

    def frame(t):
        base = kb(t)

        # Find active caption
        active = ""
        cap_alpha = 0.0
        for (cs, ce, txt) in captions:
            if cs <= t <= ce:
                active = txt
                f_in  = min((t-cs)/0.4, 1.0)
                f_out = min((ce-t)/0.4, 1.0)
                cap_alpha = ease(min(f_in, f_out))
                break

        if active and cap_alpha > 0.01:
            base = overlay_caption(base, active, alpha=cap_alpha,
                                   font_size=30)
        return base

    return frame


# ════════════════════════════════════════════════════════════════
# BUILD TIMELINE
# ════════════════════════════════════════════════════════════════

tl = Timeline(W=W, H=H)

# 1. OPENING TITLE — 3.5s
tl.add_title(
    title="THE MAN WHO CALLED EVERY CRASH",
    subtitle="A Film About Ray Dalio",
    duration=3.5,
    transition="fade_black",
    transition_dur=0.7,
    bg_color=(4, 4, 8),
    title_color=(230, 220, 200),
    sub_color=(150, 140, 120),
)

# 2. CRASH PHOTO (NYSE) with captions — 38s
crash_fn = make_captioned_photo(
    PHOTO_CRASH, duration=38.0,
    captions=CRASH_CAPTIONS,
    zoom_start=1.0, zoom_end=1.08,
    pan_start=(0.50, 0.50),
    pan_end  =(0.53, 0.52),
    grade="netflix",
)
tl.add_clip(crash_fn, duration=38.0, transition="dissolve", transition_dur=1.0)

# 3. STAT GRAPHIC — Bridgewater vs S&P — 9s
tl.add_clip(make_stat_graphic(duration=9.0),
            duration=9.0, transition="flash", transition_dur=0.35)

# 4. RAY DALIO PORTRAIT with captions — 30s
dalio_fn = make_captioned_photo(
    PHOTO_DALIO, duration=30.0,
    captions=DALIO_CAPTIONS,
    zoom_start=1.0,  zoom_end=1.06,
    pan_start=(0.50, 0.48),
    pan_end  =(0.50, 0.52),
    grade="netflix",
)
tl.add_clip(dalio_fn, duration=30.0, transition="burn", transition_dur=0.8)

# 5. CLOSING HOOK QUOTE — 7s
tl.add_quote(
    quote="This is the story of Ray Dalio.\nAnd it will change the way you think\nabout failure, success, and money.",
    attribution="",
    duration=7.0,
    transition="dissolve",
    transition_dur=1.0,
    bg_color=(4, 4, 8),
    text_color=(235, 228, 212),
    attr_color=(160, 148, 128),
)

# 6. END CARD
tl.add_title(
    title="RAY DALIO",
    subtitle="From Nothing · To Everything",
    duration=3.5,
    transition="fade_black",
    transition_dur=0.8,
    bg_color=(4, 4, 8),
    title_color=(210, 170, 70),
    sub_color=(140, 128, 105),
)

frame_fn, total = tl.build()
print(f"Total: {total:.1f}s")
render(frame_fn, total, OUTPUT, fps=FPS, crf=20)
