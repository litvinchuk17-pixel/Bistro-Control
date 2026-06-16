#!/usr/bin/env python3
"""
Buffett birth intro — 90-second Netflix doc style.
Procedural watercolor-style backgrounds + cinematic library.
Add photos by calling  tl.add_photo("path.jpg", ...)  before tl.build().
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
FPS    = 24
import os as _os
OUTPUT = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "buffett_intro.mp4")

# ─── COLOR PALETTE ─────────────────────────────────────────────────
SKY_COLD_TOP  = (58,  68,  88)
SKY_COLD_BOT  = (132, 142, 158)
SKY_WARM_TOP  = (85,  74,  54)
SKY_WARM_BOT  = (188, 158, 102)
GROUND_COLD   = (56,  60,  70)
GROUND_WARM   = (108, 90,  60)
BLDG_DARK     = (26,  29,  40)
BLDG_MID      = (46,  50,  63)
WIN_DARK      = (14,  16,  24)
WIN_AMBER     = (228, 158, 42)
WIN_DIM       = (165, 108, 36)
HOUSE_BODY    = (90,  76,  55)
HOUSE_SHADOW  = (40,  34,  24)
HOUSE_ROOF    = (50,  41,  31)
GLOW_C        = (255, 190, 70)
PEOPLE_C      = (16,  18,  28)
FOG_C         = (132, 138, 153)

def lp(a, b, f):
    f = max(0., min(1., f))
    return tuple(int(x + (y - x) * f) for x, y in zip(a, b))

def ease(t):
    t = max(0., min(1., t))
    return t * t * (3 - 2 * t)

# ─── PRE-GENERATED STATIC DATA ─────────────────────────────────────
rng = np.random.default_rng(42)

BUILDINGS = []
x = 0
while x < W * 2.7:
    bw = int(rng.integers(55, 200))
    bh = int(rng.integers(H // 5, H // 2 + 10))
    BUILDINGS.append((x, H - bh, x + bw, H))
    x += bw + int(rng.integers(2, 14))

WINDOWS = []
for (bx1, by1, bx2, by2) in BUILDINGS:
    for wy in range(by1 + 14, by2 - 12, 27):
        for wx in range(bx1 + 9, bx2 - 9, 21):
            lit = rng.random() < 0.09
            WINDOWS.append((wx, wy, wx + 9, wy + 13, lit))

PEOPLE = [(int(W * 0.05 + i * W * 0.078),
           int(rng.integers(int(H * 0.26), int(H * 0.38))),
           int(rng.integers(-4, 5))) for i in range(12)]

LEAVES = [{
    'x0': rng.uniform(-80, W + 180),
    'y0': rng.uniform(-160, H * 0.35),
    'vx': rng.uniform(-52, -16),
    'vy': rng.uniform(28, 85),
    'sw': rng.uniform(8, 32),
    'sf': rng.uniform(0.4, 1.8),
    'sp': rng.uniform(0, math.tau),
    'sz': rng.uniform(5, 13),
    'col': (int(rng.integers(125, 210)),
            int(rng.integers(62, 148)),
            int(rng.integers(10, 48))),
    't0': rng.uniform(0, 62),
} for _ in range(90)]

_y, _x = np.mgrid[0:H, 0:W]
_dx = (_x - W / 2) / (W / 2)
_dy = (_y - H / 2) / (H / 2)
VIG = np.clip(1.0 - (np.sqrt(_dx**2 + (_dy * 1.25)**2) - 0.42) * 1.9,
              0.18, 1.0).astype(np.float32)
GRAIN = rng.normal(0, 1.0, (H, W, 3)).astype(np.float32)


# ─── DRAW HELPERS ──────────────────────────────────────────────────

def sky(warmth):
    arr = np.empty((H, W, 3), dtype=np.float32)
    top = np.array(lp(SKY_COLD_TOP, SKY_WARM_TOP, warmth), dtype=np.float32)
    bot = np.array(lp(SKY_COLD_BOT, SKY_WARM_BOT, warmth), dtype=np.float32)
    sh  = int(H * 0.58)
    yf  = np.clip(np.arange(H, dtype=np.float32) / max(sh - 1, 1), 0, 1)
    for c in range(3):
        arr[:, :, c] = (top[c] + (bot[c] - top[c]) * yf)[:, np.newaxis]
    gnd = np.array(lp(GROUND_COLD, GROUND_WARM, warmth), dtype=np.float32)
    arr[sh:] = gnd
    # horizon haze
    fog = np.array(lp(FOG_C, lp(SKY_COLD_BOT, SKY_WARM_BOT, warmth), 0.5),
                   dtype=np.float32)
    haze = np.clip(1.0 - np.abs(np.arange(H) - sh) / 28.0, 0, 1)
    for c in range(3):
        arr[:, :, c] += haze[:, np.newaxis] * (fog[c] - arr[:, :, c]) * 0.20
    return arr


def draw_city(draw, pan_x, warmth):
    bc = lp(BLDG_DARK, lp(BLDG_DARK, BLDG_MID, 0.5), warmth * 0.4)
    pc = lp(bc, (80, 84, 97), 0.45)
    for (bx1, by1, bx2, by2) in BUILDINGS:
        x1, x2 = bx1 - pan_x, bx2 - pan_x
        if x2 < -10 or x1 > W + 10:
            continue
        draw.rectangle([x1, by1, x2, by2], fill=bc)
        draw.rectangle([x1, by1, x2, by1 + 3], fill=pc)
    for (wx1, wy1, wx2, wy2, lit) in WINDOWS:
        x1, x2 = wx1 - pan_x, wx2 - pan_x
        if x2 < -3 or x1 > W + 3 or wy1 < 0 or wy2 > H:
            continue
        draw.rectangle([x1, wy1, x2, wy2], fill=WIN_AMBER if lit else WIN_DARK)


def draw_people(draw, alpha):
    for px, ph, lean in PEOPLE:
        bw = int(ph * 0.33)
        by = int(H * 0.63)
        ty = by - ph
        draw.rectangle([px - bw//2 + lean, ty, px + bw//2 + lean, by],
                       fill=PEOPLE_C)
        hr = max(1, ph // 8)
        draw.ellipse([px - hr + lean, ty - hr*2, px + hr + lean, ty],
                     fill=PEOPLE_C)
        draw.ellipse([px - int(hr*1.4) + lean, ty - int(hr*2.6),
                      px + int(hr*1.4) + lean, ty - int(hr*1.7)],
                     fill=PEOPLE_C)


def draw_leaves(draw, t, alpha):
    if alpha < 0.01:
        return
    for lf in LEAVES:
        t_loc = (t - lf['t0']) % 76
        if t_loc < 0 or t_loc > 72:
            continue
        x = lf['x0'] + lf['vx'] * t_loc + lf['sw'] * math.sin(
            lf['sf'] * t_loc + lf['sp'])
        y = lf['y0'] + lf['vy'] * t_loc + 0.018 * t_loc**2
        if y > H + 18 or not (-60 < x < W + 60):
            continue
        sz = lf['sz']
        draw.ellipse([int(x-sz), int(y-sz*0.55),
                      int(x+sz), int(y+sz*0.55)], fill=lf['col'])


def make_house_layer(scale, glow):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = int(W * 0.50), int(H * 0.70)
    bw, bh = int(210 * scale), int(155 * scale)
    rh = int(72 * scale)
    x1, y1, x2, y2 = cx - bw//2, cy - bh, cx + bw//2, cy

    d.rectangle([x1-6, y2-8, x2+6, y2+6], fill=(*HOUSE_SHADOW, 255))
    d.rectangle([x1, y1, x2, y2], fill=(*HOUSE_BODY, 255))
    sc = lp(HOUSE_BODY, HOUSE_SHADOW, 0.28)
    for sx in range(x1+10, x2, 13):
        d.line([sx, y1, sx, y2], fill=(*sc, 175), width=1)
    d.polygon([(x1-14, y1+4), (x2+14, y1+4), (cx, y1-rh)],
              fill=(*HOUSE_ROOF, 255))
    chx = cx + bw//4
    d.rectangle([chx-7, y1-rh+14, chx+7, y1-4], fill=(36, 30, 22, 255))
    d.rectangle([x1+6, y2-int(28*scale), x2-6, y2],
                fill=(*lp(HOUSE_BODY, (112, 95, 72), 0.5), 255))
    dw, dh = int(26*scale), int(50*scale)
    d.rectangle([cx-dw//2, y2-dh, cx+dw//2, y2], fill=(36, 30, 22, 255))
    ww, wh = int(26*scale), int(33*scale)
    wy_pos = y1 + int((bh-wh)*0.42)
    for wxx in [cx-bw//3, cx+bw//3]:
        d.rectangle([wxx-ww//2, wy_pos, wxx+ww//2, wy_pos+wh],
                    fill=(*WIN_DARK, 255))
    # Glowing window
    gx = cx + bw//4
    gy = y1 + int(bh*0.08)
    gw, gh = int(28*scale), int(36*scale)
    gc = lp(WIN_DIM, GLOW_C, glow)
    d.rectangle([gx-gw//2, gy, gx+gw//2, gy+gh], fill=(*gc, 255))

    if glow > 0.05:
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        for sp in range(1, 9):
            s = sp * 12
            ha = int(88 * glow * (1 - sp/9))
            hd.rectangle([gx-gw//2-s, gy-s, gx+gw//2+s, gy+gh+s],
                         fill=(*lp(WIN_DIM, GLOW_C, 0.6), ha))
        halo = halo.filter(ImageFilter.GaussianBlur(radius=20*glow+5))
        layer = Image.alpha_composite(layer, halo)

    return layer


# ─── SCENE FRAME FUNCTION ──────────────────────────────────────────

TOTAL = 90.0

def make_scene_frame(t):
    breadline_a = max(0., min(1., min((t-18)/7., (50-t)/7.)))
    house_a     = max(0., min(1., (t-42)/10.))
    glow_s      = ease(max(0., (t-50)/40.))
    warm_bleed  = ease(max(0., (t-58)/32.))
    leaf_a      = max(0., min(1., min((t-14)/8., (74-t)/8.)))
    warmth      = warm_bleed*0.65 + house_a*0.12
    pan_x       = int(ease(min(t/26., 1.)) * W * 0.38)

    # Sky (numpy)
    arr = sky(warmth)

    # Convert to PIL for shapes
    img  = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img)
    draw_city(draw, pan_x, warmth)
    draw_leaves(draw, t, leaf_a)

    # Breadline layer
    if breadline_a > 0.01:
        bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_people(ImageDraw.Draw(bl), breadline_a)
        bl_arr = np.array(bl)
        bl_arr[:, :, 3] = (bl_arr[:, :, 3] * breadline_a).astype(np.uint8)
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, Image.fromarray(bl_arr, "RGBA"))
        img = img.convert("RGB")

    # House layer
    if house_a > 0.01:
        h_scale = 0.62 + 0.68 * ease(max(0., (t-42)/32.))
        hl = make_house_layer(h_scale, glow_s)
        hl_arr = np.array(hl)
        hl_arr[:, :, 3] = (hl_arr[:, :, 3] * house_a).astype(np.uint8)
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, Image.fromarray(hl_arr, "RGBA"))
        img = img.convert("RGB")

    # Warm radial bleed
    if warm_bleed > 0.02:
        arr_w = np.array(img).astype(np.float32)
        yi2, xi2 = np.mgrid[0:H, 0:W]
        dx2 = (xi2 - W*0.525) / (W*0.55)
        dy2 = (yi2 - H*0.50)  / (H*0.55)
        wm  = np.clip(1. - np.sqrt(dx2**2 + dy2**2)*1.55, 0, 1) * warm_bleed * 0.52
        wr  = np.array(SKY_WARM_BOT, dtype=np.float32)
        for c in range(3):
            arr_w[:, :, c] = np.clip(
                arr_w[:, :, c]*(1 - wm*(0.33 if c < 2 else 0.07))
                + wr[c]*wm*(0.33 if c < 2 else 0.07), 0, 255)
        img = Image.fromarray(arr_w.astype(np.uint8), "RGB")

    # Watercolor soft-focus
    img = img.filter(ImageFilter.GaussianBlur(radius=0.65 + 0.32*math.sin(t*0.28)))
    arr = np.array(img).astype(np.float32)

    # Grain
    arr = np.clip(arr + GRAIN * (7.2 + 2.4*math.sin(t*0.6)), 0, 255)

    # Sepia (less sepia as warmth increases)
    r2 = arr[:,:,0]*0.393 + arr[:,:,1]*0.769 + arr[:,:,2]*0.189
    g2 = arr[:,:,0]*0.349 + arr[:,:,1]*0.686 + arr[:,:,2]*0.168
    b2 = arr[:,:,0]*0.272 + arr[:,:,1]*0.534 + arr[:,:,2]*0.131
    sep = np.stack([r2, g2, b2], axis=2)
    ss  = 0.48 - 0.14*warm_bleed
    arr = np.clip(arr*(1-ss) + sep*ss, 0, 255)

    # Vignette
    arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG

    return np.clip(arr, 0, 255).astype(np.uint8)


# ─── BUILD TIMELINE ────────────────────────────────────────────────

def build_video(extra_photos=None):
    """
    extra_photos: list of dicts with keys:
      path, duration, transition, zoom_start, zoom_end,
      pan_start, pan_end, grade, insert_after_clip
    """
    tl = Timeline(W=W, H=H)

    # Main 90-second procedural scene
    tl.add_clip(make_scene_frame, duration=TOTAL, transition="fade_black")

    # Quote card example (customize text freely)
    tl.add_quote(
        quote="Правило перше: ніколи не втрачай гроші. Правило друге: ніколи не забувай правило перше.",
        attribution="Уоррен Баффет",
        duration=6.5,
        transition="dissolve",
        transition_dur=1.0,
    )

    tl.add_title(
        title="30 СЕРПНЯ 1930",
        subtitle="Омаха, Небраска",
        duration=4.0,
        transition="fade_black",
        transition_dur=0.7,
    )

    # Insert user photos here (examples — replace paths with real files)
    if extra_photos:
        for p in extra_photos:
            tl.add_photo(
                path=p["path"],
                duration=p.get("duration", 7.0),
                transition=p.get("transition", "dissolve"),
                transition_dur=p.get("transition_dur", 0.9),
                zoom_start=p.get("zoom_start", 1.0),
                zoom_end=p.get("zoom_end", 1.10),
                pan_start=p.get("pan_start", (0.48, 0.5)),
                pan_end=p.get("pan_end",   (0.52, 0.52)),
                grade=p.get("grade", "netflix"),
            )

    return tl.build()


if __name__ == "__main__":
    # ── To add photos, pass a list like this: ──────────────────────
    # photos = [
    #     {"path": "/path/to/depression_photo.jpg", "duration": 8,
    #      "transition": "burn", "zoom_start": 1.0, "zoom_end": 1.12},
    #     {"path": "/path/to/omaha_1930.jpg", "duration": 7,
    #      "transition": "dissolve"},
    # ]
    # frame_fn, total = build_video(extra_photos=photos)
    # ───────────────────────────────────────────────────────────────
    frame_fn, total = build_video()
    render(frame_fn, total, OUTPUT, fps=FPS, crf=20)
