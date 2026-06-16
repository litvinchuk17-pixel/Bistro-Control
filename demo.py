#!/usr/bin/env python3
"""
45-second cinematic demo — showcases all library features:
Title card → Film burn → City scene → Dissolve →
Quote card → Flash → Warm archive scene → Push → End card
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from cinematic import (
    Timeline, render,
    grade_netflix, grade_sepia_archive,
    add_vignette, add_grain, add_letterbox,
    ease_in_out, ease_out,
)

W, H   = 1280, 536
OUTPUT = "/home/user/Bistro-Control/demo_cinematic.mp4"

rng    = np.random.default_rng(7)
GRAIN  = rng.normal(0, 1.0, (H, W, 3)).astype(np.float32)

_y, _x = np.mgrid[0:H, 0:W]
VIG = np.clip(1.0 - (np.sqrt(((_x - W/2)/(W/2))**2 +
                              ((_y - H/2)/(H/2)*1.2)**2) - 0.44)*1.85,
              0.15, 1.0).astype(np.float32)

def lp(a, b, f):
    f = max(0., min(1., f))
    return tuple(int(x + (y - x) * f) for x, y in zip(a, b))

# ── SCENE 1: COLD CITY NIGHT ────────────────────────────────────────
_bldgs = []
x = 0
r2 = np.random.default_rng(99)
while x < W * 2.5:
    bw = int(r2.integers(55, 185))
    bh = int(r2.integers(H//5, H//2 + 10))
    _bldgs.append((x, H - bh, x + bw, H))
    x += bw + int(r2.integers(2, 14))

_wins = []
for (bx1, by1, bx2, by2) in _bldgs:
    for wy in range(by1+14, by2-12, 27):
        for wx in range(bx1+9, bx2-9, 22):
            _wins.append((wx, wy, wx+9, wy+13, r2.random() < 0.10))

def city_cold(t):
    """Dark, cold, rainy-night city."""
    pan = int(ease_in_out(min(t / 12., 1.)) * W * 0.28)
    arr = np.empty((H, W, 3), dtype=np.float32)
    top = np.array((44, 52, 70), dtype=np.float32)
    bot = np.array((85, 95, 115), dtype=np.float32)
    sh  = int(H * 0.60)
    yf  = np.clip(np.arange(H, dtype=np.float32) / max(sh-1, 1), 0, 1)
    for c in range(3):
        arr[:, :, c] = (top[c] + (bot[c] - top[c]) * yf)[:, np.newaxis]
    arr[sh:] = np.array((52, 55, 65), dtype=np.float32)

    img  = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)
    bc   = (24, 27, 38)
    for (bx1, by1, bx2, by2) in _bldgs:
        x1, x2 = bx1 - pan, bx2 - pan
        if x2 < -10 or x1 > W + 10:
            continue
        draw.rectangle([x1, by1, x2, by2], fill=bc)
        draw.rectangle([x1, by1, x2, by1+3], fill=(36, 40, 54))
    for (wx1, wy1, wx2, wy2, lit) in _wins:
        x1 = wx1 - pan
        x2 = wx2 - pan
        if x2 < -3 or x1 > W + 3 or wy1 < 0 or wy2 > H:
            continue
        col = (215, 175, 80) if lit else (12, 14, 22)
        draw.rectangle([x1, wy1, x2, wy2], fill=col)

    # Rain streaks
    rain_rng = np.random.default_rng(int(t * 24) % 10000)
    for _ in range(120):
        rx = int(rain_rng.integers(0, W))
        ry = int(rain_rng.integers(0, H))
        draw.line([rx, ry, rx - 2, ry + 18],
                  fill=(130, 140, 160, 80), width=1)

    img  = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    arr  = np.array(img).astype(np.float32)
    arr  = np.clip(arr + GRAIN * 8.5, 0, 255)
    arr[:, :, 0] *= VIG; arr[:, :, 1] *= VIG; arr[:, :, 2] *= VIG
    return np.clip(arr, 0, 255).astype(np.uint8)


# ── SCENE 2: WARM ARCHIVE (sepia particles / dust) ─────────────────
_dust = [(rng.uniform(0, W), rng.uniform(0, H),
          rng.uniform(0.4, 2.2), rng.uniform(0.5, 3.5),
          rng.uniform(0, math.tau)) for _ in range(55)]

def warm_archive(t):
    """Warm sepia scene — like old film footage."""
    arr = np.empty((H, W, 3), dtype=np.float32)
    top = np.array((82, 68, 44), dtype=np.float32)
    bot = np.array((168, 140, 92), dtype=np.float32)
    yf  = np.arange(H, dtype=np.float32) / H
    for c in range(3):
        arr[:, :, c] = (top[c] + (bot[c] - top[c]) * yf)[:, np.newaxis]

    # Horizontal archive-photo border effect
    arr[:int(H*0.04)]  = np.array((8, 6, 4), dtype=np.float32)
    arr[-int(H*0.04):] = np.array((8, 6, 4), dtype=np.float32)

    img  = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)

    # Dust / film scratches
    for dx, dy, spd, amp, ph in _dust:
        x  = (dx + t * spd * 20) % W
        y  = dy + amp * math.sin(spd * t + ph) * 15
        draw.ellipse([int(x)-1, int(y)-1, int(x)+1, int(y)+1],
                     fill=(220, 200, 160))

    # Vertical scratch line (flickers)
    if int(t * 24) % 18 == 0:
        sx = rng.integers(W // 4, 3 * W // 4)
        draw.line([sx, 0, sx + 1, H], fill=(255, 245, 200, 60), width=1)

    arr  = np.array(img).astype(np.float32)
    # Sepia
    r2 = arr[:,:,0]*0.393 + arr[:,:,1]*0.769 + arr[:,:,2]*0.189
    g2 = arr[:,:,0]*0.349 + arr[:,:,1]*0.686 + arr[:,:,2]*0.168
    b2 = arr[:,:,0]*0.272 + arr[:,:,1]*0.534 + arr[:,:,2]*0.131
    arr = np.clip(np.stack([r2, g2, b2], axis=2), 0, 255)
    arr  = np.clip(arr + GRAIN * 11.0, 0, 255)
    arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
    return np.clip(arr, 0, 255).astype(np.uint8)


# ── SCENE 3: NEON MODERN (Netflix-graded) ──────────────────────────
def modern_scene(t):
    """Clean, modern doc scene — Netflix color grade."""
    # Abstract geometric background
    arr = np.full((H, W, 3), (10, 10, 14), dtype=np.float32)

    # Animated light sweep
    sweep = (t * 0.18) % 1.0
    cx    = int(sweep * W * 1.4 - W * 0.2)
    yi, xi = np.mgrid[0:H, 0:W]
    dist2  = np.sqrt(((xi - cx) / (W * 0.4))**2 + ((yi - H/2) / (H * 0.6))**2)
    glow   = np.clip(1.0 - dist2 * 1.2, 0, 1) * 0.18
    arr[:, :, 0] += glow * 80
    arr[:, :, 1] += glow * 55
    arr[:, :, 2] += glow * 30

    # Horizontal lines
    for ly in range(0, H, 60):
        arr[ly:ly+1, :] = np.clip(arr[ly:ly+1, :] + 8, 0, 255)

    arr  = np.clip(arr, 0, 255).astype(np.uint8)
    arr  = grade_netflix(arr)
    arr  = add_vignette(arr, strength=0.8)
    arr  = add_grain(arr, intensity=5.0)
    return arr


# ── BUILD TIMELINE ──────────────────────────────────────────────────
tl = Timeline(W=W, H=H)

# 1. Title card
tl.add_title(
    title="КІНЕМАТОГРАФІЧНИЙ ДВИЖОК",
    subtitle="Netflix Documentary Style • Demo 2026",
    duration=4.5,
    transition="fade_black",
    transition_dur=0.6,
)

# 2. Cold city night scene
tl.add_clip(city_cold, duration=10.0, transition="burn", transition_dur=0.7)

# 3. Quote card
tl.add_quote(
    quote="Місто, що не спить. Тисячі вогнів — і кожен чийсь страх.",
    attribution="",
    duration=5.5,
    transition="dissolve",
    transition_dur=0.9,
)

# 4. Warm archive footage
tl.add_clip(warm_archive, duration=9.0, transition="flash", transition_dur=0.4)

# 5. Second quote
tl.add_quote(
    quote="Архів не бреше. Він просто мовчить про незручне.",
    attribution="",
    duration=5.0,
    transition="dissolve",
    transition_dur=0.8,
)

# 6. Modern graded scene
tl.add_clip(modern_scene, duration=8.0, transition="push_left", transition_dur=0.6)

# 7. End card
tl.add_title(
    title="ПРОДОВЖЕННЯ СЛІДУЄ",
    subtitle="Залиш фото — я вставлю з Ken Burns ефектом",
    duration=4.0,
    transition="fade_black",
    transition_dur=0.8,
)

frame_fn, total = tl.build()
print(f"Total duration: {total:.1f}s")
render(frame_fn, total, OUTPUT, fps=24, crf=20)
