#!/usr/bin/env python3
"""
20-Minute European Investing Guide — Full Netflix Doc Video
8 chapters, animated backgrounds, stat cards, charts, captions
"""
import math, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from cinematic import (
    Timeline, render,
    make_quote_card, make_title_card,
    grade_netflix, add_vignette, add_grain,
    ease_in_out, ease_out, ease_in,
    FONT_SANS, FONT_SANS_BOLD, FONT_SERIF_IT,
)

W, H   = 1280, 536
FPS    = 24
OUTPUT = "/home/user/Bistro-Control/investing_guide_20min.mp4"

# ─── FONTS ─────────────────────────────────────────────────────────
def _font(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

F_CAP    = _font(FONT_SANS,      30)   # caption body
F_CAP_SM = _font(FONT_SANS,      26)   # small caption
F_CAP_LG = _font(FONT_SANS_BOLD, 34)   # emphasis caption
F_STAT   = _font(FONT_SANS_BOLD, 96)   # big stat number
F_STAT_S = _font(FONT_SANS_BOLD, 48)
F_LABEL  = _font(FONT_SANS,      22)
F_LABEL2 = _font(FONT_SANS_BOLD, 20)
F_CHART  = _font(FONT_SANS,      18)

# ─── SHARED ASSETS ─────────────────────────────────────────────────
rng   = np.random.default_rng(42)
GRAIN = rng.normal(0, 1.0, (H, W, 3)).astype(np.float32)

_yi, _xi = np.mgrid[0:H, 0:W]
VIG = np.clip(1.0 - (np.sqrt(((_xi-W/2)/(W/2))**2 +
                              ((_yi-H/2)/(H/2)*1.18)**2) - 0.42)*1.85,
              0.16, 1.0).astype(np.float32)

# Chapter accent colors  (R,G,B)
ACCENT = {
    "intro"    : (210, 180,  70),   # gold
    "invest"   : (80,  180, 220),   # blue
    "property" : (200, 130,  60),   # amber
    "etf"      : (80,  210, 130),   # green
    "compound" : (160, 100, 240),   # purple
    "risk"     : (220,  80,  70),   # red
    "howto"    : ( 80, 160, 220),   # teal
    "outro"    : (210, 180,  70),   # gold
}

BG_BASE = {
    "intro"    : (  6,   8,  14),
    "invest"   : (  4,   8,  16),
    "property" : ( 10,   8,   4),
    "etf"      : (  4,  10,   6),
    "compound" : (  6,   4,  14),
    "risk"     : ( 12,   4,   4),
    "howto"    : (  4,   8,  12),
    "outro"    : (  8,   6,   4),
}

def lp(a, b, f):
    f = max(0., min(1., f))
    return tuple(int(x+(y-x)*f) for x, y in zip(a, b))

def ease(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)

# ─── ANIMATED BACKGROUND GENERATOR ─────────────────────────────────

def make_bg(chapter: str):
    """Return a frame-fn for an animated background."""
    base = np.array(BG_BASE[chapter], dtype=np.float32)
    acc  = np.array(ACCENT[chapter],  dtype=np.float32)

    # Particle data (static per chapter)
    pr = np.random.default_rng(hash(chapter) % 2**31)
    PX = pr.uniform(0, W, 60).astype(np.float32)
    PY = pr.uniform(0, H, 60).astype(np.float32)
    PS = pr.uniform(0.2, 1.5, 60).astype(np.float32)   # speed
    PP = pr.uniform(0, math.tau, 60).astype(np.float32) # phase

    def frame(t):
        arr = np.empty((H, W, 3), dtype=np.float32)

        # Slowly breathing gradient
        pulse = 0.5 + 0.5 * math.sin(t * 0.12)
        top_f = base * (1 + pulse * 0.08)
        bot_f = base * (1 - pulse * 0.04)
        yf = np.arange(H, dtype=np.float32) / H
        for c in range(3):
            arr[:, :, c] = (top_f[c] + (bot_f[c]-top_f[c])*yf)[:, np.newaxis]

        # Radial accent glow (bottom-right, slow drift)
        gx = W * (0.72 + 0.08 * math.sin(t * 0.07))
        gy = H * (0.78 + 0.06 * math.sin(t * 0.11))
        dx = (_xi - gx) / (W * 0.55)
        dy = (_yi - gy) / (H * 0.55)
        glow = np.clip(1.0 - np.sqrt(dx**2 + dy**2)*1.4, 0, 1) * 0.12
        for c in range(3):
            arr[:, :, c] += glow * acc[c]

        # Convert to PIL for particles + lines
        img  = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        draw = ImageDraw.Draw(img)

        # Floating particles
        for i in range(len(PX)):
            px = (PX[i] + t * PS[i] * 12) % W
            py = PY[i] + 6 * math.sin(PS[i] * t + PP[i])
            r  = int(acc[0]); g = int(acc[1]); b = int(acc[2])
            draw.ellipse([px-1.5, py-1.5, px+1.5, py+1.5], fill=(r,g,b,40))

        # Thin horizontal scan line
        sl_y = int((H * 0.5 + H * 0.3 * math.sin(t * 0.05)) % H)
        ac   = tuple(int(c) for c in acc)
        draw.line([0, sl_y, W, sl_y], fill=(*ac, 18), width=1)

        arr2 = np.array(img).astype(np.float32)
        # Grain
        arr2 = np.clip(arr2 + GRAIN * 5.5, 0, 255)
        # Vignette
        arr2[:,:,0] *= VIG; arr2[:,:,1] *= VIG; arr2[:,:,2] *= VIG
        return np.clip(arr2, 0, 255).astype(np.uint8)

    return frame


# ─── CAPTION SYSTEM ────────────────────────────────────────────────

_strip_cache = {}

def _caption_strip(text, bold=False, size=30, color=(240,235,220)):
    key = (text, bold, size)
    if key in _strip_cache:
        return _strip_cache[key]

    font = F_CAP_LG if bold else (_font(FONT_SANS, size))
    tmp  = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    max_w = int(W * 0.84)
    words  = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bb   = tmp.textbbox((0,0), test, font=font)
        if bb[2]-bb[0] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)

    lh     = size + int(size * 0.45)
    total_h= len(lines) * lh + 22
    strip  = Image.new("RGBA", (W, total_h), (0,0,0,0))
    d      = ImageDraw.Draw(strip)
    for i, line in enumerate(lines):
        bb = d.textbbox((0,0), line, font=font)
        x  = (W - (bb[2]-bb[0])) // 2
        y  = i * lh + 10
        d.text((x+2, y+2), line, font=font, fill=(0,0,0,155))
        d.text((x,   y  ), line, font=font, fill=(*color, 255))
    _strip_cache[key] = (np.array(strip), total_h)
    return _strip_cache[key]


def composite_caption(base_arr, text, alpha=1.0,
                      bold=False, size=30, y_frac=0.82,
                      color=(240,235,220)):
    if alpha < 0.01 or not text:
        return base_arr
    strip_arr, sh = _caption_strip(text, bold, size, color)
    y_pos = min(int(H * y_frac), H - sh - 4)
    y_end = min(H, y_pos + sh)
    ah    = y_end - y_pos

    out   = base_arr.copy().astype(np.float32)
    # Dark bar
    out[y_pos:y_end, :] = out[y_pos:y_end, :] * (1 - alpha * 0.62)

    sa = strip_arr[:ah].astype(np.float32)
    # Alpha composite text
    a_ch = sa[:, :, 3:4] / 255.0 * alpha
    for c in range(3):
        out[y_pos:y_end, :, c] = np.clip(
            out[y_pos:y_end, :, c] * (1 - a_ch[:,:,0]) +
            sa[:, :, c] * a_ch[:,:,0], 0, 255)
    return np.clip(out, 0, 255).astype(np.uint8)


def accent_bar(base_arr, chapter, alpha=1.0):
    """Thin accent line at top."""
    if alpha < 0.01:
        return base_arr
    out   = base_arr.copy()
    r,g,b = ACCENT[chapter]
    a     = int(255 * alpha)
    out[:3, :] = np.array([r, g, b], dtype=np.uint8)
    return out


# ─── CAPTION SEQUENCE BUILDER ──────────────────────────────────────

def caption_seq(items, bg_fn, chapter):
    """
    items: list of (text, duration) or (text, duration, bold)
    Returns (frame_fn, total_duration)
    """
    total = sum(it[1] for it in items)
    times = []
    t = 0.0
    for it in items:
        times.append(t)
        t += it[1]

    def frame(t_abs):
        base = bg_fn(t_abs)
        base = accent_bar(base, chapter)
        # Find active caption
        active_text  = ""
        active_alpha = 0.0
        active_bold  = False
        for i, (it, t_start) in enumerate(zip(items, times)):
            text  = it[0]
            dur   = it[1]
            bold  = it[2] if len(it) > 2 else False
            t_end = t_start + dur
            if t_start <= t_abs < t_end:
                rel   = t_abs - t_start
                fi    = ease(min(rel / 0.5, 1.0))
                fo    = ease(min((dur - rel) / 0.5, 1.0))
                active_alpha = min(fi, fo)
                active_text  = text
                active_bold  = bold
                break
        base = composite_caption(base, active_text, active_alpha,
                                 bold=active_bold)
        return base

    return frame, total


# ─── STAT / INFOGRAPHIC CARDS ──────────────────────────────────────

def stat_two(
    val1, label1, sub1, color1,
    val2, label2, sub2, color2,
    title, duration,
):
    """Side-by-side stat comparison card."""
    bg_arr = np.full((H, W, 3), (6, 6, 10), dtype=np.float32)

    def frame(t):
        prog = ease(min(t / 1.0, 1.0))
        fi   = ease(min(t / 0.5, 1.0))
        fo   = ease(min((duration-t) / 0.5, 1.0))
        alp  = min(fi, fo)

        img = Image.fromarray(
            np.clip(bg_arr * alp, 0, 255).astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # Top accent line
        acc_c = (210, 178, 68)
        d.rectangle([0, 0, W, 3], fill=acc_c)

        # Title
        tb = d.textbbox((0,0), title, font=F_LABEL2)
        d.text(((W-(tb[2]-tb[0]))//2, 18), title,
               font=F_LABEL2, fill=(*acc_c, 255))

        # Divider
        d.line([W//2, 70, W//2, H-60], fill=(40,40,55), width=1)

        for side, val, lbl, sub, col in [
            (0, val1, label1, sub1, color1),
            (1, val2, label2, sub2, color2),
        ]:
            cx = W//4 if side == 0 else 3*W//4

            # Label
            lb = d.textbbox((0,0), lbl, font=F_LABEL)
            d.text((cx-(lb[2]-lb[0])//2, 80), lbl,
                   font=F_LABEL, fill=(140,140,152))

            # Big value (count-up for numbers)
            import re
            num_m = re.search(r'[0-9]+', val)
            if num_m and prog < 0.999:
                num   = int(num_m.group())
                shown = int(num * prog)
                disp  = val.replace(num_m.group(), str(shown))
            else:
                disp  = val
            vb = d.textbbox((0,0), disp, font=F_STAT)
            d.text((cx-(vb[2]-vb[0])//2, 115), disp,
                   font=F_STAT, fill=col)

            # Sub
            sb = d.textbbox((0,0), sub, font=F_LABEL2)
            d.text((cx-(sb[2]-sb[0])//2, 270), sub,
                   font=F_LABEL2, fill=tuple(int(c*0.7) for c in col))

        arr = np.array(img).astype(np.float32)
        arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
        arr = np.clip(arr + GRAIN * 3.5, 0, 255)
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame, duration


def stat_single(value, label, sublabel, color, title, duration):
    """Single large stat card."""
    def frame(t):
        fi  = ease(min(t/0.5, 1.0))
        fo  = ease(min((duration-t)/0.5, 1.0))
        alp = min(fi, fo)

        import re
        prog  = ease(min(t/1.2, 1.0))
        num_m = re.search(r'[0-9]+', value)
        if num_m and prog < 0.999:
            shown = int(int(num_m.group()) * prog)
            disp  = value.replace(num_m.group(), str(shown))
        else:
            disp  = value

        img = Image.new("RGB", (W, H), (6,6,10))
        d   = ImageDraw.Draw(img)
        acc = (210,178,68)
        d.rectangle([0,0,W,3], fill=acc)

        tb = d.textbbox((0,0), title, font=F_LABEL2)
        d.text(((W-(tb[2]-tb[0]))//2, 18), title, font=F_LABEL2, fill=acc)

        vb = d.textbbox((0,0), disp, font=F_STAT)
        d.text(((W-(vb[2]-vb[0]))//2, 130), disp, font=F_STAT, fill=color)

        lb = d.textbbox((0,0), label, font=F_STAT_S)
        d.text(((W-(lb[2]-lb[0]))//2, 270), label, font=F_STAT_S,
               fill=(210,208,200))

        slb = d.textbbox((0,0), sublabel, font=F_LABEL)
        d.text(((W-(slb[2]-slb[0]))//2, 340), sublabel, font=F_LABEL,
               fill=(140,138,128))

        arr = np.array(img).astype(np.float32) * alp
        arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
        arr = np.clip(arr + GRAIN*3.5, 0, 255)
        return np.clip(arr, 0, 255).astype(np.uint8)
    return frame, duration


def animated_growth_chart(duration=14.0):
    """Animated compound interest chart €10k → €56k over 20 years."""
    YEARS  = list(range(0, 21))
    VALUES = [10000 * (1.09 ** y) for y in YEARS]
    MAX_V  = VALUES[-1]

    def frame(t):
        fi  = ease(min(t/0.6, 1.0))
        fo  = ease(min((duration-t)/0.6, 1.0))
        alp = min(fi, fo)
        prog = ease(min(t/5.0, 1.0))   # chart draws in over 5s

        img = Image.new("RGB", (W, H), (6,6,10))
        d   = ImageDraw.Draw(img)

        acc  = (160, 100, 240)   # purple chapter
        d.rectangle([0,0,W,3], fill=acc)
        title = "THE POWER OF COMPOUND INTEREST — 9% ANNUAL RETURN"
        tb = d.textbbox((0,0), title, font=F_LABEL2)
        d.text(((W-(tb[2]-tb[0]))//2, 12), title, font=F_LABEL2, fill=acc)

        # Chart area
        cx1, cy1 = 110, 60
        cx2, cy2 = W - 60, H - 80

        # Grid lines + year labels
        for i, yr in enumerate(YEARS):
            x = cx1 + (cx2-cx1) * yr/20
            d.line([x, cy1, x, cy2], fill=(30,30,45), width=1)
            if yr % 5 == 0:
                lb = str(yr) + "yr"
                bb = d.textbbox((0,0), lb, font=F_CHART)
                d.text((x-(bb[2]-bb[0])//2, cy2+6), lb, font=F_CHART,
                       fill=(100,100,115))

        # Value grid lines
        for v in [10000, 20000, 30000, 40000, 56000]:
            y = cy2 - (cy2-cy1)*(v/MAX_V)
            d.line([cx1, y, cx2, y], fill=(28,28,42), width=1)
            label = f"€{v//1000}k"
            bb = d.textbbox((0,0), label, font=F_CHART)
            d.text((cx1-bb[2]-6, y-bb[3]//2), label, font=F_CHART,
                   fill=(100,100,115))

        # Animated curve
        shown_years = int(prog * 20)
        pts = []
        for yr in range(shown_years + 1):
            x = cx1 + (cx2-cx1) * yr/20
            y = cy2 - (cy2-cy1) * (VALUES[yr]/MAX_V)
            pts.append((x, y))

        if len(pts) >= 2:
            # Area fill under curve
            fill_pts = [(cx1, cy2)] + pts + [(pts[-1][0], cy2)]
            d.polygon(fill_pts, fill=(*acc, 25))
            # Curve line
            for i in range(len(pts)-1):
                d.line([pts[i], pts[i+1]], fill=(*acc,), width=3)
            # Current dot
            cx_pt, cy_pt = pts[-1]
            d.ellipse([cx_pt-6, cy_pt-6, cx_pt+6, cy_pt+6], fill=acc)
            # Value label at current point
            cur_v = VALUES[min(shown_years, 20)]
            vlb   = f"€{int(cur_v):,}"
            vbb   = d.textbbox((0,0), vlb, font=F_LABEL2)
            d.text((cx_pt-(vbb[2]-vbb[0])//2, cy_pt-26), vlb,
                   font=F_LABEL2, fill=acc)

        arr = np.array(img).astype(np.float32) * alp
        arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
        arr = np.clip(arr + GRAIN*4, 0, 255)
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame, duration


def animated_crash_recovery(duration=12.0):
    """Animated stock market chart showing crash + recovery."""
    # Simulated S&P data (normalized): pre-crash, crash, recovery
    import numpy as np
    pts_data = []
    # 2006-2012 rough shape
    # Build a simple path
    path = []
    # Rising 2006-2007
    for i in range(24):
        path.append(1.0 + i*0.012)
    # Peak + crash 2008-2009 (-50%)
    peak = path[-1]
    for i in range(18):
        path.append(peak * (1 - i/18 * 0.5))
    # Recovery 2009-2012
    bottom = path[-1]
    for i in range(30):
        path.append(bottom * (1 + i/30 * 1.3))

    N = len(path)
    MAX_V = max(path)
    MIN_V = min(path)

    def frame(t):
        fi  = ease(min(t/0.6, 1.0))
        fo  = ease(min((duration-t)/0.6, 1.0))
        alp = min(fi, fo)
        prog = ease(min(t/5.0, 1.0))

        img = Image.new("RGB", (W, H), (6,6,10))
        d   = ImageDraw.Draw(img)

        acc = (220,80,70)
        d.rectangle([0,0,W,3], fill=acc)
        title = "MARKET CRASH & RECOVERY — DON'T TIME THE MARKET"
        tb = d.textbbox((0,0), title, font=F_LABEL2)
        d.text(((W-(tb[2]-tb[0]))//2, 12), title, font=F_LABEL2, fill=acc)

        cx1, cy1 = 70, 60
        cx2, cy2 = W-50, H-75

        shown = max(2, int(prog * N))
        pts   = []
        for i in range(shown):
            x = cx1 + (cx2-cx1) * i/(N-1)
            v = path[i]
            y = cy2 - (cy2-cy1) * ((v-MIN_V)/(MAX_V-MIN_V))
            pts.append((int(x), int(y)))

        if len(pts) >= 2:
            # Color segments: green before crash, red during, green after
            crash_start = 24; crash_end = 42
            for i in range(len(pts)-1):
                if i < crash_start:
                    col = (80,200,120)
                elif i < crash_end:
                    col = (220,70,60)
                else:
                    col = (80,200,120)
                d.line([pts[i], pts[i+1]], fill=col, width=3)

        # Labels
        if shown > crash_start + 2:
            cx_crash = cx1 + (cx2-cx1)*crash_start/(N-1)
            d.line([int(cx_crash), cy1, int(cx_crash), cy2],
                   fill=(180,60,50,120), width=1)
            lb = "2008 CRISIS"
            bb = d.textbbox((0,0), lb, font=F_CHART)
            d.text((int(cx_crash)-(bb[2]-bb[0])//2, cy1+4),
                   lb, font=F_CHART, fill=(220,80,70))

        if shown == N:
            # End annotation
            ex, ey = pts[-1]
            d.ellipse([ex-5,ey-5,ex+5,ey+5], fill=(80,200,120))
            recov = "FULL RECOVERY"
            rb = d.textbbox((0,0), recov, font=F_LABEL2)
            d.text((ex-(rb[2]-rb[0])//2, ey-26), recov,
                   font=F_LABEL2, fill=(80,200,120))

        # Y-axis labels
        for pct, label in [(0,"−50%"), (0.5,"0%"), (1.0,"+50%")]:
            y = cy2 - (cy2-cy1)*pct
            d.line([cx1-5, y, cx2, y], fill=(25,25,38), width=1)
            lb = label
            bb = d.textbbox((0,0), lb, font=F_CHART)
            d.text((cx1-bb[2]-6, y-bb[3]//2), lb,
                   font=F_CHART, fill=(100,100,115))

        arr = np.array(img).astype(np.float32) * alp
        arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
        arr = np.clip(arr + GRAIN*4, 0, 255)
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame, duration


def two_engine_diagram(duration=10.0):
    """Animated two-engine vs one-engine investment diagram."""
    def frame(t):
        fi  = ease(min(t/0.6, 1.0))
        fo  = ease(min((duration-t)/0.6, 1.0))
        alp = min(fi, fo)
        prog = ease(min(t/1.5, 1.0))

        img = Image.new("RGB", (W, H), (6,6,10))
        d   = ImageDraw.Draw(img)

        acc = (80,180,220)
        d.rectangle([0,0,W,3], fill=acc)
        title = "THE TWO-ENGINE INVESTMENT PRINCIPLE"
        tb = d.textbbox((0,0), title, font=F_LABEL2)
        d.text(((W-(tb[2]-tb[0]))//2, 12), title, font=F_LABEL2, fill=acc)

        # Left side: ONE ENGINE (bad)
        cx_bad = W//4
        d.text((cx_bad-80, 50), "ONE ENGINE", font=F_LABEL2,
               fill=(220,80,70))
        # Circle
        r = 85
        cy = H//2 + 10
        d.ellipse([cx_bad-r, cy-r, cx_bad+r, cy+r], fill=(35,8,8),
                  outline=(220,80,70), width=2)
        d.text((cx_bad-40, cy-18), "Price ↑", font=F_LABEL2,
               fill=(240,235,220))
        d.text((cx_bad-50, cy+4), "ONLY", font=F_LABEL2,
               fill=(220,80,70))
        # X mark
        d.text((cx_bad-18, cy+55), "SPECULATION", font=_font(FONT_SANS,16),
               fill=(220,80,70))

        if prog > 0.3:
            # Right side: TWO ENGINES (good)
            cx_good = 3*W//4
            d.text((cx_good-90, 50), "TWO ENGINES", font=F_LABEL2,
                   fill=(80,210,130))
            # Engine 1
            r2 = 72
            cy1_e = cy - 60
            d.ellipse([cx_good-r2, cy1_e-r2, cx_good+r2, cy1_e+r2],
                      fill=(4,20,10), outline=(80,210,130), width=2)
            d.text((cx_good-40, cy1_e-12), "Price ↑", font=F_LABEL2,
                   fill=(240,235,220))

            # Engine 2
            cy2_e = cy + 55
            d.ellipse([cx_good-r2, cy2_e-r2, cx_good+r2, cy2_e+r2],
                      fill=(4,14,10), outline=(80,210,130), width=2)
            d.text((cx_good-50, cy2_e-12), "Dividends $", font=F_LABEL2,
                   fill=(240,235,220))
            d.text((cx_good-52, cy2_e+55), "REAL INVESTMENT",
                   font=_font(FONT_SANS,16), fill=(80,210,130))

        # Divider line
        d.line([W//2, 60, W//2, H-50], fill=(35,35,50), width=1)

        arr = np.array(img).astype(np.float32) * alp
        arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
        arr = np.clip(arr + GRAIN*4, 0, 255)
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame, duration


def pie_chart_85(duration=10.0):
    """85% of active funds underperform — animated pie chart."""
    def frame(t):
        fi  = ease(min(t/0.5, 1.0))
        fo  = ease(min((duration-t)/0.5, 1.0))
        alp = min(fi, fo)
        prog = ease(min(t/2.5, 1.0))

        img  = Image.new("RGB", (W, H), (6,6,10))
        d    = ImageDraw.Draw(img)
        acc  = (80,210,130)
        d.rectangle([0,0,W,3], fill=acc)
        title = "ACTIVE FUNDS vs INDEX FUNDS — 10-YEAR PERFORMANCE"
        tb = d.textbbox((0,0), title, font=F_LABEL2)
        d.text(((W-(tb[2]-tb[0]))//2, 12), title, font=F_LABEL2, fill=acc)

        # Pie chart
        cx, cy = W//2, H//2 + 20
        r = 150
        angle_85 = 360 * 0.85 * prog

        # 85% red (underperform)
        if angle_85 > 0:
            d.pieslice([cx-r, cy-r, cx+r, cy+r], -90, -90+angle_85,
                       fill=(200,60,55), outline=(6,6,10), width=3)
        # 15% green (outperform)
        if angle_85 < 360:
            d.pieslice([cx-r, cy-r, cx+r, cy+r], -90+angle_85, 270,
                       fill=(70,180,110), outline=(6,6,10), width=3)

        # Labels
        if prog > 0.6:
            d.text((cx-42, cy-22), "85%", font=F_STAT_S, fill=(240,235,220))
            d.text((cx-68, cy+28), "UNDERPERFORM", font=F_LABEL2,
                   fill=(220,100,95))
        if prog > 0.8:
            d.text((cx+r+20, cy-30), "15%", font=F_LABEL2, fill=(240,235,220))
            d.text((cx+r+12, cy-8),  "BEAT THE", font=F_LABEL2,
                   fill=(80,200,120))
            d.text((cx+r+12, cy+12), "INDEX", font=F_LABEL2,
                   fill=(80,200,120))

        # Source
        src = "Source: S&P Dow Jones SPIVA Report"
        sb  = d.textbbox((0,0), src, font=F_CHART)
        d.text(((W-(sb[2]-sb[0]))//2, H-36), src, font=F_CHART,
               fill=(80,82,95))

        arr = np.array(img).astype(np.float32) * alp
        arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
        arr = np.clip(arr + GRAIN*3.5, 0, 255)
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame, duration


# ─── CHAPTER TITLE CARD ────────────────────────────────────────────

def chapter_card(title, subtitle, chapter, duration=4.5):
    acc = ACCENT[chapter]
    def frame(t):
        fi  = ease(min(t/0.5, 1.0))
        fo  = ease(min((duration-t)/0.5, 1.0))
        alp = min(fi, fo)

        img = Image.new("RGB", (W, H), BG_BASE[chapter])
        d   = ImageDraw.Draw(img)

        # Accent bar
        d.rectangle([0,0,W,4], fill=acc)

        # Chapter number line
        f_ch = _font(FONT_SANS, 16)
        d.text((60, 20), subtitle, font=f_ch, fill=tuple(int(c*0.7) for c in acc))
        # Divider
        d.line([58, 44, 58+len(subtitle)*9, 44], fill=acc, width=1)

        # Main title
        f_title = _font(FONT_SANS_BOLD, 48)
        # Wrap if too long
        tmp = ImageDraw.Draw(Image.new("RGB",(1,1)))
        words = title.split()
        lines, cur = [], ""
        for w in words:
            test = (cur+" "+w).strip()
            bb = tmp.textbbox((0,0),test,font=f_title)
            if bb[2]-bb[0] <= W-120: cur=test
            else:
                if cur: lines.append(cur)
                cur=w
        if cur: lines.append(cur)
        lh = 58
        y0 = H//2 - len(lines)*lh//2
        for i,line in enumerate(lines):
            bb = d.textbbox((0,0),line,font=f_title)
            x  = (W-(bb[2]-bb[0]))//2
            d.text((x+2,y0+i*lh+2), line, font=f_title, fill=(0,0,0,80))
            d.text((x,  y0+i*lh),   line, font=f_title,
                   fill=(240,235,222))

        arr = np.array(img).astype(np.float32) * alp
        arr[:,:,0] *= VIG; arr[:,:,1] *= VIG; arr[:,:,2] *= VIG
        arr = np.clip(arr + GRAIN*4, 0, 255)
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame, duration


# ════════════════════════════════════════════════════════════════════
# CONTENT — all captions per chapter
# Each item: (text, duration_seconds) or (text, dur, bold)
# ════════════════════════════════════════════════════════════════════

BG = {k: make_bg(k) for k in ACCENT}   # pre-build bg generators

# ── INTRO ───────────────────────────────────────────────────────────
INTRO_CAPS = [
    ("I spent 17 years in professional investing...", 6),
    ("after helping launch a European investment firm", 6),
    ("that now serves over 140,000 clients.", 6),
    ("My own portfolio exceeds one million euros.", 6),
    ("And here's exactly how I'd approach investing from scratch", 6),
    ("with just €100.", 5, True),
    ("", 2),
    ("So you've got some cash sitting idle in your bank account", 6),
    ("and you're ready to put it to work.", 5),
    ("Maybe you came across the fact that", 4),
    ("a €5,000 stake in Nvidia a decade ago would be worth over a million today.", 8),
    ("Or perhaps you've heard about ETFs —", 5),
    ("the hands-off approach that lets everyday investors", 6),
    ("consistently outperform seasoned professionals", 5),
    ("with just a few hours of attention per year.", 6),
    ("", 2),
    ("When you search for beginner investing advice online,", 6),
    ("you mostly find content aimed at Americans —", 5),
    ("or worse, get-rich-quick schemes.", 5),
    ("I've put together a practical, step-by-step framework", 6),
    ("built specifically for people living in Europe.", 6),
    ("We'll cover how to pick solid investments,", 5),
    ("how to automate the whole process,", 5),
    ("and I'll walk you through a live example", 5),
    ("of how I personally invest my own money.", 6),
]

# ── CHAPTER 1 ───────────────────────────────────────────────────────
CH1_CAPS = [
    ("Starting out is confusing because everyone has a different opinion.", 7),
    ("A family member swears by property.", 5),
    ("A friend is convinced Bitcoin is the answer.", 6),
    ("Someone else is pushing peer-to-peer lending, individual stocks,", 6),
    ("bonds, options, currency trading, or day trading.", 6),
    ("So how do you tell a sound investment from a dangerous bet?", 7),
    ("", 2),
    ("I faced this exact dilemma myself.", 5),
    ("I grew up in Eastern Europe in a family of teachers —", 6),
    ("money was tight and nobody knew the first thing about investing.", 7),
    ("When I moved to the US and landed a job in finance,", 6),
    ("I received my first bonus of $10,000 and wanted to invest it.", 7),
    ("But my background was in physics, not financial markets.", 6),
    ("What I did have, though, was access to experienced, wealthy investors.", 7),
    ("", 2),
    ("One of them — a mentor of mine — put it to me this way:", 6),
    ("If you're boarding a plane, do you want one engine or two?", 7, True),
    ("Two, obviously — if one fails, you don't go down.", 6),
    ("He told me the same logic applies to investments.", 6),
    ("", 2),
    ("Many popular assets have only one profit engine:", 6),
    ("you buy, you hope the price rises, and if it doesn't — you lose.", 7),
    ("That's not investing. That's speculation.", 6, True),
    ("You're simply guessing at price movements.", 5),
    ("", 2),
    ("What you want instead is a two-engine investment.", 6),
]

CH1_POST_DIAG = [
    ("Engine one: price appreciation.", 5),
    ("Engine two: cash flow generated by the asset itself.", 6),
    ("The best investments pay you regardless of what the market is doing.", 7),
    ("If prices rise, great. If they fall, you're still receiving income.", 7),
    ("", 2),
    ("Single-engine assets — gold, silver, currencies, commodities —", 6),
    ("depend entirely on price movement.", 5),
    ("Gold had a strong two decades recently,", 5),
    ("but before that it delivered two decades of poor returns.", 6),
    ("Over the very long run, it has barely kept pace with inflation.", 7),
    ("", 2),
    ("By contrast, the two asset classes with the strongest track records over centuries", 8),
    ("are both dual-engine: real estate and stocks.", 6, True),
    ("Property earns through both price appreciation and rental income.", 7),
    ("Stocks earn through both price appreciation and dividends —", 6),
    ("your share of the company's profits.", 5),
]

# ── CHAPTER 2 ───────────────────────────────────────────────────────
CH2_CAPS = [
    ("Both are strong, but there's one issue with real estate", 6),
    ("that can quietly wreck your quality of life if you're not prepared.", 7),
    ("", 2),
    ("Growing up, I had relatives who owned a large apartment building.", 7),
    ("I loved visiting — it felt like an adventure.", 5),
    ("But every single time, I heard my cousin's mother dealing with something:", 7),
    ("a broken toilet, a damaged roof,", 5),
    ("a tenant who refused to pay and ended up in court.", 6),
    ("", 2),
    ("I quickly understood: rental property is not passive income.", 6, True),
    ("It's a second job.", 5, True),
    ("", 2),
    ("If you're already stretched between work and family,", 6),
    ("managing tenants and maintenance is the last thing you need.", 6),
    ("You want your money working for you — not the other way around.", 7),
    ("", 2),
    ("Stocks, by comparison, are genuinely hands-off.", 6),
    ("Nobody is calling you at midnight about a burst pipe.", 6),
    ("Companies have management teams and employees —", 5),
    ("your only job is to own a share.", 5),
    ("", 2),
    ("The challenge, however, is picking the right ones.", 6),
]

# ── CHAPTER 3 ───────────────────────────────────────────────────────
CH3_CAPS = [
    ("The overall stock market has created extraordinary wealth over time.", 7),
    ("But research from Arizona State University revealed something surprising:", 7),
    ("out of roughly 26,000 US stocks over the past 90 years,", 6),
    ("just 83 companies accounted for half of all the gains.", 6, True),
    ("", 2),
    ("Finding those 83 in a pool of 26,000 is not a skill — it's a lottery.", 8),
    ("And buying the obvious winners — Apple, Microsoft, Nvidia, Amazon —", 7),
    ("comes with its own trap: everyone already knows about them.", 6),
    ("The growth is already priced in.", 5),
    ("By the time something is famous, you're often arriving late.", 7),
    ("", 2),
    ("Fifty years ago, this was an unsolvable problem for ordinary people.", 7),
    ("Either you were a professional, or you paid steep fees to someone who was.", 8),
    ("But then a simple, radical idea changed everything —", 6),
    ("an idea championed by John C. Bogle", 5),
    ("in The Little Book of Common Sense Investing,", 5),
    ("endorsed by Warren Buffett, Nobel laureates Paul Samuelson and Eugene Fama,", 8),
    ("and decades of hard data.", 5),
    ("", 2),
    ("The idea: instead of searching for the needle in the haystack,", 7),
    ("buy the entire haystack.", 5, True),
    ("", 2),
    ("Rather than identifying the handful of winning stocks from thousands of options,", 8),
    ("you simply buy a small piece of every stock in the market.", 7),
    ("At first this sounds almost too simple —", 5),
    ("surely it can't beat professionals who dedicate their careers to stock analysis?", 8),
    ("But the data is clear.", 5, True),
]

CH3_POST_PIE = [
    ("According to the S&P Dow Jones SPIVA report, over the past decade,", 7),
    ("85% of actively managed funds underperformed the S&P 500.", 7, True),
    ("This isn't a recent anomaly —", 5),
    ("it has held true in every decade since index funds were introduced.", 7),
    ("", 2),
    ("This is the index fund —", 5),
    ("or in its most accessible form, the ETF: exchange-traded fund.", 7),
    ("The distinction between the two is roughly like iPhone versus Android:", 7),
    ("different packaging, same underlying result.", 6),
]

# ── CHAPTER 4 ───────────────────────────────────────────────────────
CH4_CAPS = [
    ("Global stock index funds have delivered an average annual return", 6),
    ("of around 9% over the long term.", 5),
    ("When I first heard that figure with $10,000 saved, I thought:", 6),
    ("is that really worth it?", 4),
    ("", 2),
    ("A senior banker I worked with didn't mince words.", 6),
    ("He told me I clearly hadn't paid attention", 5),
    ("to what Einstein reportedly called", 5),
    ("the eighth wonder of the world: compound interest.", 6, True),
    ("", 2),
    ("Here's how it works.", 4),
    ("You invest €10,000.", 4),
    ("After one year at 9%, you have €10,900.", 5),
    ("The following year, your 9% return is calculated on €10,900 —", 6),
    ("not the original €10,000.", 5),
    ("Each year, the base grows, and so does the return.", 6),
    ("The acceleration is slow at first — and then dramatic.", 6),
]

CH4_POST_CHART = [
    ("After 20 years, that initial €10,000 becomes roughly €56,000 —", 7, True),
    ("with no additional contributions.", 5, True),
    ("", 2),
    ("The single most important thing you can do:", 6),
    ("start as early as possible and leave it alone.", 6, True),
]

# ── CHAPTER 5 ───────────────────────────────────────────────────────
CH5_CAPS = [
    ("Index funds reduce risk substantially", 5),
    ("by spreading your money across hundreds of companies.", 6),
    ("No single bankruptcy can hurt you significantly.", 5),
    ("", 2),
    ("But markets do fall — sometimes sharply.", 5),
    ("The dot-com crash, the 2008 financial crisis — a 50% drop —", 7),
    ("the 2020 pandemic sell-off — these events happen, and they're uncomfortable.", 8),
    ("", 2),
    ("I made a costly mistake during the 2008 crisis.", 6),
    ("I was new to Wall Street, the market was collapsing,", 6),
    ("and my employer was rumoured to be cutting thousands of jobs.", 7),
    ("I told myself I was being smart by staying out.", 6),
    ("", 2),
    ("An experienced colleague warned me that this kind of thinking", 6),
    ("is exactly what keeps people on the sidelines permanently —", 6),
    ("waiting for the right moment that never comes,", 5),
    ("then finally jumping in just before the next downturn.", 6),
    ("", 2),
    ("He was right. And I ignored him.", 5, True),
    ("I sat out one of the best buying opportunities in a generation.", 7, True),
]

CH5_POST_CHART = [
    ("Nobel laureate Robert C. Merton describes trying to time the market", 7),
    ("as 'a fool's errand.'", 5),
    ("The investors who wait for certainty before committing", 6),
    ("almost always wait forever — because certainty never arrives.", 7),
    ("", 2),
    ("The data is consistent:", 4),
    ("those who invest regularly, regardless of conditions,", 6),
    ("outperform those who try to pick their moments.", 6, True),
]

# ── CHAPTER 6 ───────────────────────────────────────────────────────
CH6_CAPS = [
    ("Now that you understand the principles,", 5),
    ("how do you actually put money to work?", 5),
    ("", 2),
    ("The popular ETFs you'll read about online — SPY, VOO, QQQ —", 7),
    ("are American products and are not available for purchase in Europe.", 7),
    ("You need European-domiciled equivalents.", 5),
    ("", 2),
    ("The best place to find them is justETF.com —", 6),
    ("a database of thousands of ETFs available to European investors.", 7),
    ("Filtering by 'Equity' shows stock-based funds.", 5),
    ("Sorting by fund size surfaces the most established options.", 6),
    ("For example, the iShares Core S&P 500 UCITS ETF —", 6),
    ("which holds every stock in the S&P 500,", 5),
    ("and is the European counterpart to American index funds.", 6),
    ("", 2),
    ("To actually buy ETFs, you need a brokerage —", 6),
    ("essentially a regulated marketplace for investments.", 5),
    ("There are many reputable options available across Europe.", 6),
    ("For demonstration, I'll use Trading 212 —", 5),
    ("because of its straightforward interface.", 5),
    ("", 2),
    ("After searching for the ETF by name,", 5),
    ("you'll notice it costs around €611 per share.", 6),
    ("But most modern brokerages offer fractional investing —", 6),
    ("meaning you can invest €100 and receive a proportional slice of the fund.", 8),
    ("You enter your amount, review the order, confirm —", 6),
    ("and within seconds you own a fraction of hundreds of the world's largest companies.", 8, True),
    ("", 2),
    ("Something that would have been impossible", 5),
    ("for even the wealthiest individuals half a century ago", 6),
    ("is now available to anyone with €100 and a phone.", 6, True),
]

# ── OUTRO ───────────────────────────────────────────────────────────
OUTRO_CAPS = [
    ("If you arrived at this video knowing nothing about investing,", 6),
    ("you now understand more than the vast majority of beginners.", 6),
    ("", 3),
    ("Focus on dual-engine investments —", 5),
    ("assets that generate both price growth and cash flow.", 6),
    ("", 2),
    ("Use index funds and ETFs —", 5),
    ("rather than trying to pick individual stocks.", 5),
    ("", 2),
    ("Start as early as possible and invest consistently —", 6),
    ("don't wait for the 'right' moment.", 5),
    ("", 2),
    ("Let compound interest do the heavy lifting over time.", 6, True),
    ("", 3),
    ("The remaining complexity — choosing the right ETF for your country's tax rules,", 8),
    ("selecting a trustworthy brokerage,", 5),
    ("understanding accumulating versus distributing funds —", 6),
    ("is worth a dedicated deep dive,", 5),
    ("which I cover in detail in other videos.", 6),
    ("", 3),
    ("Thank you for watching.", 5),
]


# ════════════════════════════════════════════════════════════════════
# BUILD TIMELINE
# ════════════════════════════════════════════════════════════════════

def add(tl, fn, dur, tr="dissolve", td=0.8):
    tl.add_clip(fn, duration=dur, transition=tr, transition_dur=td)

tl = Timeline(W=W, H=H)

# ── OPENING TITLE ────────────────────────────────────────────────────
fn, d = chapter_card("FROM €100 TO FINANCIAL FREEDOM",
                     "A Complete European Investor's Guide", "intro", 6)
add(tl, fn, d, "fade_black", 0.8)

# ── INTRO CAPTIONS ───────────────────────────────────────────────────
fn, d = caption_seq(INTRO_CAPS, BG["intro"], "intro")
add(tl, fn, d, "dissolve", 0.9)

# ── CH1 TITLE ────────────────────────────────────────────────────────
fn, d = chapter_card("WHAT SEPARATES A REAL INVESTMENT FROM A GAMBLE",
                     "Chapter 1", "invest", 5)
add(tl, fn, d, "fade_black", 0.7)

# CH1 part A
fn, d = caption_seq(CH1_CAPS, BG["invest"], "invest")
add(tl, fn, d, "dissolve", 0.9)

# Two-engine diagram
fn, d = two_engine_diagram(10)
add(tl, fn, d, "dissolve", 0.8)

# CH1 part B
fn, d = caption_seq(CH1_POST_DIAG, BG["invest"], "invest")
add(tl, fn, d, "dissolve", 0.9)

# ── CH2 TITLE ────────────────────────────────────────────────────────
fn, d = chapter_card("WHY STOCKS BEAT PROPERTY FOR MOST PEOPLE",
                     "Chapter 2", "property", 5)
add(tl, fn, d, "fade_black", 0.7)

fn, d = caption_seq(CH2_CAPS, BG["property"], "property")
add(tl, fn, d, "dissolve", 0.9)

# ── CH3 TITLE ────────────────────────────────────────────────────────
fn, d = chapter_card("THE STOCK-PICKING PROBLEM AND THE ELEGANT SOLUTION",
                     "Chapter 3", "etf", 5)
add(tl, fn, d, "fade_black", 0.7)

fn, d = caption_seq(CH3_CAPS, BG["etf"], "etf")
add(tl, fn, d, "dissolve", 0.9)

# Stat: 83 out of 26,000
fn, d = stat_single("83", "out of 26,000 stocks", "accounted for half of all S&P gains — 90 years",
                    (220,80,70), "THE NEEDLE IN THE HAYSTACK", 10)
add(tl, fn, d, "flash", 0.3)

# Quote: Bogle
fn = make_quote_card(
    "Don't look for the needle in the haystack. Just buy the haystack.",
    "John C. Bogle — Founder, Vanguard",
    duration=8, W=W, H=H,
    bg_color=(4,6,10), text_color=(235,228,210), attr_color=(150,145,130),
)
add(tl, fn, 8, "dissolve", 0.9)

# 85% pie chart
fn, d = pie_chart_85(10)
add(tl, fn, d, "flash", 0.35)

fn, d = caption_seq(CH3_POST_PIE, BG["etf"], "etf")
add(tl, fn, d, "dissolve", 0.9)

# ── CH4 TITLE ────────────────────────────────────────────────────────
fn, d = chapter_card("HOW MUCH CAN YOU REALISTICALLY EARN?",
                     "Chapter 4", "compound", 5)
add(tl, fn, d, "fade_black", 0.7)

fn, d = caption_seq(CH4_CAPS, BG["compound"], "compound")
add(tl, fn, d, "dissolve", 0.9)

# Einstein quote
fn = make_quote_card(
    "Compound interest is the eighth wonder of the world. He who understands it, earns it.",
    "Attributed to Albert Einstein",
    duration=8, W=W, H=H,
    bg_color=(6,4,14), text_color=(235,228,215), attr_color=(145,135,125),
)
add(tl, fn, 8, "dissolve", 0.9)

# Animated growth chart
fn, d = animated_growth_chart(14)
add(tl, fn, d, "dissolve", 0.9)

fn, d = caption_seq(CH4_POST_CHART, BG["compound"], "compound")
add(tl, fn, d, "dissolve", 0.9)

# Stat card
fn, d = stat_two(
    "€10,000", "INVESTED TODAY", "at 9% average annual return", (80,200,140),
    "€56,000", "AFTER 20 YEARS", "no additional contributions needed", (160,100,240),
    "COMPOUND INTEREST IN ACTION", 10,
)
add(tl, fn, d, "flash", 0.35)

# ── CH5 TITLE ────────────────────────────────────────────────────────
fn, d = chapter_card("THE ONE RISK YOU CAN'T IGNORE — AND HOW TO HANDLE IT",
                     "Chapter 5", "risk", 5)
add(tl, fn, d, "fade_black", 0.7)

fn, d = caption_seq(CH5_CAPS, BG["risk"], "risk")
add(tl, fn, d, "dissolve", 0.9)

# Market crash chart
fn, d = animated_crash_recovery(12)
add(tl, fn, d, "dissolve", 0.8)

fn, d = caption_seq(CH5_POST_CHART, BG["risk"], "risk")
add(tl, fn, d, "dissolve", 0.9)

# Merton quote
fn = make_quote_card(
    "Trying to time the market is a fool's errand.",
    "Robert C. Merton — Nobel Laureate in Economics",
    duration=7, W=W, H=H,
    bg_color=(12,4,4), text_color=(235,228,215), attr_color=(155,140,128),
)
add(tl, fn, 7, "dissolve", 0.9)

# Stat
fn, d = stat_single("85%", "INVEST REGULARLY — BEAT THE TIMERS",
                    "Data across every market cycle since 1970",
                    (80,200,130), "STAY THE COURSE", 9)
add(tl, fn, d, "flash", 0.35)

# ── CH6 TITLE ────────────────────────────────────────────────────────
fn, d = chapter_card("HOW TO ACTUALLY GET STARTED IN EUROPE",
                     "Chapter 6", "howto", 5)
add(tl, fn, d, "fade_black", 0.7)

fn, d = caption_seq(CH6_CAPS, BG["howto"], "howto")
add(tl, fn, d, "dissolve", 0.9)

# Platform stat
fn, d = stat_single("€100", "IS ALL YOU NEED TO START",
                    "Fractional ETF investing • Available on Trading 212 and others",
                    (80,160,220), "YOUR FIRST INVESTMENT", 9)
add(tl, fn, d, "flash", 0.35)

# ── OUTRO ────────────────────────────────────────────────────────────
fn, d = chapter_card("WHERE TO GO FROM HERE",
                     "Summary", "outro", 5)
add(tl, fn, d, "fade_black", 0.7)

fn, d = caption_seq(OUTRO_CAPS, BG["outro"], "outro")
add(tl, fn, d, "dissolve", 0.9)

# Final quote
fn = make_quote_card(
    "The stock market is a device for transferring money from the impatient to the patient.",
    "Warren Buffett",
    duration=9, W=W, H=H,
    bg_color=(8,6,4), text_color=(235,228,210), attr_color=(158,145,120),
)
add(tl, fn, 9, "dissolve", 0.9)

# Closing title card
fn, d = chapter_card("START TODAY. STAY THE COURSE.",
                     "europeaninvestor.guide", "outro", 7)
add(tl, fn, d, "fade_black", 1.0)

# ════════════════════════════════════════════════════════════════════
# RENDER
# ════════════════════════════════════════════════════════════════════
frame_fn, total = tl.build()
mins = int(total // 60)
secs = int(total % 60)
print(f"\nTotal duration: {mins}m {secs}s  ({total:.0f}s, {int(total*FPS)} frames)")
print(f"Output: {OUTPUT}")
render(frame_fn, total, OUTPUT, fps=FPS, crf=20, preset="fast")
