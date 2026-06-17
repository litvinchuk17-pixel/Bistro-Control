#!/usr/bin/env python3
"""
БАФФЕТ vs ДАЛІО: ЯК БАГАТІЮТЬ НАСПРАВДІ?
~7 minutes | 1280×536 | 24fps | Netflix documentary style
Fast cuts · kinetic text · lower thirds · split screen · impact cards
"""
import math, os as _os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from cinematic import (
    Timeline, render, make_ken_burns,
    grade_netflix, add_vignette, add_grain,
    ease_in_out, ease_out, ease_in,
    FONT_SANS, FONT_SANS_BOLD, FONT_SERIF_IT,
)

W, H   = 1280, 536
FPS    = 24
_HERE  = _os.path.dirname(_os.path.abspath(__file__))
OUTPUT = _os.path.join(_HERE, "buffett_vs_dalio.mp4")

# Drop your photos here (WebP or JPG)
PHOTO_B = _os.path.join(_HERE, "photo_buffett.webp")
PHOTO_D = _os.path.join(_HERE, "photo_dalio.webp")
if not _os.path.exists(PHOTO_D):
    PHOTO_D = _os.path.join(_HERE, "photo_2.webp")

HAS_B = _os.path.exists(PHOTO_B)
HAS_D = _os.path.exists(PHOTO_D)

# ── BRAND PALETTE ─────────────────────────────────────────────
CB  = (210, 165,  50)   # Buffett amber / old money
CD  = ( 45, 185, 200)   # Dalio teal   / modern quant
BG  = (  6,   6,  10)   # near-black
TXT = (235, 228, 212)   # cream
DIM = (110, 105,  95)   # muted
RED = (220,  55,  55)
GRN = ( 65, 210, 100)

# ── PRE-BAKE ──────────────────────────────────────────────────
_rng  = np.random.default_rng(42)
GRAIN = _rng.normal(0, 1.0, (H, W, 3)).astype(np.float32)
_y, _x = np.mgrid[0:H, 0:W]
VIG = np.clip(
    1.0 - (np.sqrt(((_x-W/2)/(W/2))**2 + ((_y-H/2)/(H/2)*1.15)**2) - 0.42)*1.9,
    0.16, 1.0
).astype(np.float32)

# ── HELPERS ───────────────────────────────────────────────────
def ease(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)

def _lf(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def _vfx(arr, g=5.5):
    """Apply grain + vignette. arr can be float32 or uint8."""
    a = arr.astype(np.float32)
    a = np.clip(a + GRAIN*g, 0, 255)
    a[:,:,0] *= VIG; a[:,:,1] *= VIG; a[:,:,2] *= VIG
    return np.clip(a, 0, 255).astype(np.uint8)

def _fade_arr(arr, t, dur, fi=0.45, fo=0.5):
    f = ease(min(t/fi, 1.0)) * ease(min((dur-t)/fo, 1.0))
    return np.clip(arr.astype(np.float32)*f, 0, 255).astype(np.uint8)

def _paste(base_f32, overlay_rgba, x, y, alpha=1.0):
    """Alpha-composite RGBA overlay onto float32 base in-place."""
    sh, sw = overlay_rgba.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x+sw, W), min(y+sh, H)
    if x1 >= x2 or y1 >= y2: return
    sx1, sy1 = x1-x, y1-y
    sx2, sy2 = sx1+(x2-x1), sy1+(y2-y1)
    a = overlay_rgba[sy1:sy2, sx1:sx2, 3:4].astype(np.float32)/255.0 * alpha
    rgb = overlay_rgba[sy1:sy2, sx1:sx2, :3].astype(np.float32)
    base_f32[y1:y2, x1:x2] = base_f32[y1:y2, x1:x2]*(1-a) + rgb*a

_sc = {}
def _strip(text, font, color=TXT):
    """Pre-render text as RGBA numpy array (cached)."""
    key = (text, id(font), color)
    if key in _sc: return _sc[key]
    dummy = ImageDraw.Draw(Image.new("L",(1,1)))
    bb = dummy.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    img = Image.new("RGBA", (tw+8, th+8), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    d.text((4, 4), text, font=font, fill=(0,0,0,155))
    d.text((2, 2), text, font=font, fill=(*color, 255))
    s = np.array(img)
    _sc[key] = s
    return s

def _proc_bg(color, t=0.0):
    """Procedural gradient bg with radial glow of given color."""
    arr = np.full((H, W, 3), BG, dtype=np.float32)
    dist = np.sqrt(((_x-W/2)/(W*0.55))**2 + ((_y-H/2)/(H*0.65))**2)
    glow = np.clip(1.0-dist*1.3, 0, 1)**2 * (0.22+0.05*math.sin(t*0.8))
    arr[:,:,0] += glow*color[0]*0.55
    arr[:,:,1] += glow*color[1]*0.55
    arr[:,:,2] += glow*color[2]*0.55
    return np.clip(arr, 0, 255).astype(np.uint8)


# ════════════════════════════════════════════════════════════════
# 1. KINETIC TEXT — words/lines slide up and fade in sequentially
# items = [(text, color, font_size, appear_at_seconds), ...]
# ════════════════════════════════════════════════════════════════
def kinetic_text(items, duration, bg=BG, accent=CB, center=True):
    font_cache = {}
    def _font(sz):
        if sz not in font_cache: font_cache[sz] = _lf(FONT_SANS_BOLD, sz)
        return font_cache[sz]

    # Pre-render each strip
    strips = []
    # Compute total block height for centering
    total_h = sum(sz + int(sz*0.4) for (_,_,sz,_) in items)
    y = (H - total_h)//2
    for (txt, col, sz, at) in items:
        s = _strip(txt, _font(sz), color=col)
        sx = (W - s.shape[1])//2 if center else 60
        strips.append((s, sx, y, at))
        y += sz + int(sz*0.4)

    def frame(t):
        base = np.full((H,W,3), bg, dtype=np.float32)
        base[0:4]   = np.array(accent, dtype=np.float32)
        base[H-4:H] = np.array(accent, dtype=np.float32)

        for (s, sx, sy, at) in strips:
            age  = t - at
            if age < -0.08: continue
            t_in = ease(min(max(age/0.32, 0), 1.0))
            yoff = int((1-t_in)*28)
            _paste(base, s, sx, sy+yoff, alpha=t_in)

        fi = ease(min(t/0.45, 1.0))
        fo = ease(min((duration-t)/0.5, 1.0))
        base *= min(fi, fo)
        return _vfx(base, g=4.0)

    return frame


# ════════════════════════════════════════════════════════════════
# 2. SPLIT VS SCENE — Buffett | VS | Dalio
# ════════════════════════════════════════════════════════════════
def split_vs(duration):
    if HAS_B:
        kb_b = make_ken_burns(PHOTO_B, duration, W, H, 1.0, 1.05,
                              (0.5,0.5),(0.52,0.5),"netflix",0.3,0.3)
    if HAS_D:
        kb_d = make_ken_burns(PHOTO_D, duration, W, H, 1.0, 1.05,
                              (0.5,0.5),(0.48,0.5),"netflix",0.3,0.3)

    f_name = _lf(FONT_SANS_BOLD, 22)
    f_sub  = _lf(FONT_SANS, 15)
    f_vs   = _lf(FONT_SANS_BOLD, 80)

    def _side(t, is_left):
        col = CB if is_left else CD
        if is_left and HAS_B:
            arr = kb_b(t).astype(np.float32)
        elif not is_left and HAS_D:
            arr = kb_d(t).astype(np.float32)
        else:
            cx = W//4 if is_left else 3*W//4
            arr = np.full((H,W,3), BG, dtype=np.float32)
            dist = np.sqrt(((_x-cx)/(W*0.3))**2 + ((_y-H//2)/(H*0.5))**2)
            g = np.clip(1.0-dist*1.3,0,1)**1.5 * 0.35
            arr[:,:,0] += g*col[0]; arr[:,:,1] += g*col[1]; arr[:,:,2] += g*col[2]
        # Color tint
        tint = np.array(col, dtype=np.float32) * 0.14
        arr = arr*0.86 + tint[np.newaxis,np.newaxis,:]
        return np.clip(arr, 0, 255)

    def frame(t):
        left  = _side(t, True)
        right = _side(t, False)
        result = np.empty((H,W,3), dtype=np.float32)
        result[:, :W//2] = left[:, :W//2]
        result[:, W//2:] = right[:, W//2:]

        # Divider
        result[:, W//2-1:W//2+2] = 160

        img = Image.fromarray(np.clip(result,0,255).astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # VS badge (pulses in)
        vp = ease(min(max((t-0.55)/0.45,0),1.0))
        if vp > 0.01:
            pulse = 1.0 + 0.045*math.sin(t*math.pi*2.3)
            f_vsc = _lf(FONT_SANS_BOLD, int(80*vp*pulse))
            vsb   = d.textbbox((0,0),"VS",font=f_vsc)
            vw,vh = vsb[2]-vsb[0], vsb[3]-vsb[1]
            vx    = (W-vw)//2
            vy    = (H-vh)//2 - 8
            d.ellipse([vx-32,vy-16,vx+vw+32,vy+vh+16], fill=(6,6,14))
            d.ellipse([vx-30,vy-14,vx+vw+30,vy+vh+14], outline=(160,140,80), width=2)
            d.text((vx+3,vy+3),"VS",font=f_vsc,fill=(0,0,0,180))
            d.text((vx,vy),"VS",font=f_vsc,fill=(230,215,180))

        # Name badges (slide in from bottom)
        np_ = ease(min(max((t-0.3)/0.5,0),1.0))
        if np_ > 0.01:
            yoff_n = int((1-np_)*22)
            for (nm, sb, col, bx) in [
                ("WARREN BUFFETT","Berkshire Hathaway · $178B",CB,0),
                ("RAY DALIO","Bridgewater Associates · $20B",CD,W//2),
            ]:
                ny = int(H*0.82)+yoff_n
                nb = d.textbbox((0,0),nm,font=f_name)
                nw = nb[2]-nb[0]
                nx = bx+(W//2-nw)//2
                # accent bar above name
                d.rectangle([bx+22,ny-8,bx+W//2-22,ny-5],fill=col)
                d.text((nx+2,ny+2),nm,font=f_name,fill=(0,0,0))
                d.text((nx,ny),nm,font=f_name,fill=col)
                sbb = d.textbbox((0,0),sb,font=f_sub)
                sw  = sbb[2]-sbb[0]
                d.text((bx+(W//2-sw)//2,ny+30),sb,font=f_sub,fill=DIM)

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*5.5, 0, 255)
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        result *= min(fi,fo)
        return np.clip(result,0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 3. PROFILE SCENE — Ken Burns photo + lower third + captions
# captions = [(start, end, text), ...]
# ════════════════════════════════════════════════════════════════
def profile_scene(photo, name, role, color, captions, duration,
                  zoom_s=1.0, zoom_e=1.07, pan_s=(0.5,0.5), pan_e=(0.5,0.5)):
    has_p = photo and _os.path.exists(photo)
    if has_p:
        kb = make_ken_burns(photo, duration, W, H,
                            zoom_s, zoom_e, pan_s, pan_e,
                            "netflix", fade_in=0.5, fade_out=0.5)

    f_name = _lf(FONT_SANS_BOLD, 26)
    f_role = _lf(FONT_SANS, 16)
    f_cap  = _lf(FONT_SANS, 28)

    # Pre-render caption strips (word-wrapped RGBA)
    cap_data = []
    dummy_d = ImageDraw.Draw(Image.new("L",(1,1)))
    max_cw   = int(W*0.78)
    for (cs, ce, txt) in captions:
        words = txt.split(); lines, cur = [], ""
        for w in words:
            test = (cur+" "+w).strip()
            bb = dummy_d.textbbox((0,0), test, font=f_cap)
            if bb[2]-bb[0] <= max_cw: cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        lh = 36; sh = len(lines)*lh+22
        img_c = Image.new("RGBA",(W,sh),(0,0,0,0))
        dc    = ImageDraw.Draw(img_c)
        for i, ln in enumerate(lines):
            lb = dc.textbbox((0,0),ln,font=f_cap)
            lw = lb[2]-lb[0]
            lx = (W-lw)//2; ly = i*lh+11
            dc.text((lx+2,ly+2),ln,font=f_cap,fill=(0,0,0,155))
            dc.text((lx,ly),ln,font=f_cap,fill=(242,237,224,255))
        cap_data.append((np.array(img_c), cs, ce, sh))

    def frame(t):
        if has_p:
            base = kb(t).astype(np.float32)
        else:
            base = _proc_bg(color, t).astype(np.float32)

        # Lower third — slides up at 0.6s
        lt_p = ease(min(max((t-0.6)/0.5,0),1.0))
        if lt_p > 0.01:
            ylt = int(H*0.79 + (1-lt_p)*28)
            bh  = 52
            y1  = max(0,ylt); y2 = min(H,ylt+bh)
            if y1 < y2:
                # Semi-dark bar with color left edge
                bar = np.zeros((y2-y1,W,3), dtype=np.float32)
                bar[:] = np.array([10,10,16], dtype=np.float32)
                bar[:,:6] = np.array(color, dtype=np.float32)
                base[y1:y2] = base[y1:y2]*(1-0.80*lt_p) + bar*(0.80*lt_p)
            # Draw name + role
            img_tmp = Image.fromarray(np.clip(base,0,255).astype(np.uint8))
            dlt     = ImageDraw.Draw(img_tmp)
            tx = 22
            dlt.text((tx+2,ylt+5+2), name, font=f_name, fill=(0,0,0,200))
            dlt.text((tx,   ylt+5),  name, font=f_name, fill=color)
            dlt.text((tx,   ylt+35), role, font=f_role, fill=DIM)
            base = np.array(img_tmp).astype(np.float32)

        # Caption overlay
        for (cs_arr, cs, ce, sh) in cap_data:
            if cs <= t <= ce:
                fi = ease(min((t-cs)/0.38,1.0))
                fo = ease(min((ce-t)/0.38,1.0))
                a  = min(fi, fo)
                yc = H - sh - 24
                # Dark bar behind caption
                base[max(0,yc-10):min(H,yc+sh+10)] = (
                    base[max(0,yc-10):min(H,yc+sh+10)]*0.22 +
                    np.array([8,8,14], dtype=np.float32)*0.78
                )
                _paste(base, cs_arr, 0, yc, alpha=a)
                break

        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        base *= min(fi,fo)
        return _vfx(base, g=5.5)

    return frame


# ════════════════════════════════════════════════════════════════
# 4. IMPACT STAT CARD — full-screen number with count-up
# ════════════════════════════════════════════════════════════════
def impact_stat(value_str, label, sublabel, color, duration,
                prefix="", suffix="", count_from=0, count_to=None):
    f_big  = _lf(FONT_SANS_BOLD, 110)
    f_lbl  = _lf(FONT_SANS_BOLD, 32)
    f_sub  = _lf(FONT_SANS,      20)
    f_pre  = _lf(FONT_SANS_BOLD, 48)

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        # Color accent bar top
        arr[0:5] = np.array(color, dtype=np.float32)

        img = Image.fromarray(arr.astype(np.uint8))
        d   = ImageDraw.Draw(img)

        prog = ease(min(t/1.1, 1.0))

        # Animated number
        if count_to is not None:
            num = int(count_from + (count_to - count_from)*prog)
            val = f"{prefix}{num}{suffix}"
        else:
            val = value_str

        # Scale-in effect (we simulate with just alpha+position)
        scale_p = ease(min(t/0.45, 1.0))
        alpha_v = int(255 * scale_p)

        vb  = d.textbbox((0,0), val, font=f_big)
        vw  = vb[2]-vb[0]
        vx  = (W-vw)//2
        vy  = H//2 - 80

        # Glow behind number
        glow_surf = Image.new("RGBA",(W,H),(0,0,0,0))
        gd = ImageDraw.Draw(glow_surf)
        gd.text((vx+4,vy+4), val, font=f_big, fill=(*color, 40))
        img.paste(Image.fromarray(np.array(glow_surf)[:,:,:3]),
                  (0,0), glow_surf)
        d   = ImageDraw.Draw(img)

        d.text((vx+4,vy+4), val, font=f_big, fill=(0,0,0,200))
        d.text((vx,  vy),   val, font=f_big, fill=(*color, alpha_v))

        # Label
        lb = d.textbbox((0,0), label, font=f_lbl)
        lx = (W-(lb[2]-lb[0]))//2
        d.text((lx, vy+130), label, font=f_lbl, fill=TXT)

        # Sublabel
        if sublabel:
            sb = d.textbbox((0,0), sublabel, font=f_sub)
            sx = (W-(sb[2]-sb[0]))//2
            d.text((sx, vy+175), sublabel, font=f_sub, fill=DIM)

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.0, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi = ease(min(t/0.4,1.0)); fo = ease(min((duration-t)/0.45,1.0))
        return np.clip(result*min(fi,fo), 0, 255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 5. IMPACT SPLIT — two numbers side by side (2008 comparison)
# ════════════════════════════════════════════════════════════════
def impact_split(title, val_l, lbl_l, col_l, val_r, lbl_r, col_r, duration):
    f_title = _lf(FONT_SANS_BOLD, 28)
    f_big   = _lf(FONT_SANS_BOLD, 96)
    f_lbl   = _lf(FONT_SANS_BOLD, 26)
    f_sub   = _lf(FONT_SANS,      18)

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        arr[0:5]   = np.array(col_l, dtype=np.float32)
        arr[H-5:H] = np.array(col_r, dtype=np.float32)

        img = Image.fromarray(arr.astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # Title
        tb = d.textbbox((0,0), title, font=f_title)
        tx = (W-(tb[2]-tb[0]))//2
        d.text((tx+2,22), title, font=f_title, fill=(0,0,0,160))
        d.text((tx,  20), title, font=f_title, fill=TXT)

        # Divider
        d.line([W//2,70,W//2,H-20], fill=(40,40,55), width=1)

        prog = ease(min(t/1.0, 1.0))
        fi_l = ease(min(max((t-0.3)/0.4,0),1.0))
        fi_r = ease(min(max((t-0.7)/0.4,0),1.0))

        for (val, lbl, col, bx, fi) in [
            (val_l, lbl_l, col_l, 0,    fi_l),
            (val_r, lbl_r, col_r, W//2, fi_r),
        ]:
            vb  = d.textbbox((0,0), val, font=f_big)
            vw  = vb[2]-vb[0]
            vx  = bx + (W//2-vw)//2
            vy  = H//2 - 75
            d.text((vx+4,vy+4), val, font=f_big, fill=(0,0,0,180))
            d.text((vx,  vy),   val, font=f_big,
                   fill=(*col, int(255*fi)))
            lb  = d.textbbox((0,0), lbl, font=f_lbl)
            lx  = bx + (W//2-(lb[2]-lb[0]))//2
            d.text((lx, vy+115), lbl, font=f_lbl,
                   fill=(*col, int(255*fi)))

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.5, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi_g = ease(min(t/0.4,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi_g,fo),0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 6. COMPARISON TABLE — rows slide in one by one
# ════════════════════════════════════════════════════════════════
def comparison_table(duration):
    rows = [
        ("Стиль",          "Концентрований",    "Диверсифікований"),
        ("Горизонт",       "10–50 років",       "Будь-який ринок"),
        ("Ризик",          "Середній–Вис.",      "Низький–Серед."),
        ("Що вивчати",     "Глибокий аналіз",   "Системи/цикли"),
        ("2008 рік",       "−25%",              "+14%"),
        ("30 років",       "~20%/рік",          "~12%/рік"),
        ("Ідеальний для",  "Любитель бізнесу",  "Любитель систем"),
        ("Філософія",      "Мистецтво вибору",  "Математика ризику"),
    ]
    row_interval = (duration - 1.5) / len(rows)

    f_hdr  = _lf(FONT_SANS_BOLD, 20)
    f_lbl  = _lf(FONT_SANS,      18)
    f_val  = _lf(FONT_SANS_BOLD, 20)
    f_tit  = _lf(FONT_SANS_BOLD, 30)

    XL, XB, XD = 52, 340, 730
    RH = 44

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        arr[0:4] = np.array([80,60,20], dtype=np.float32)
        img = Image.fromarray(arr.astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # Title
        d.text((XL, 16), "БАФФЕТ  vs  ДАЛІО — ПОРІВНЯННЯ", font=f_tit, fill=TXT)

        # Column headers
        d.text((XB, 58), "БАФФЕТ", font=f_hdr, fill=CB)
        d.text((XD, 58), "ДАЛІО",  font=f_hdr, fill=CD)
        d.line([40, 90, W-40, 90], fill=(45,45,58), width=1)

        for i, (lbl, bv, dv) in enumerate(rows):
            at = 0.8 + i*row_interval
            if t < at - 0.04: continue
            age  = t - at
            t_in = ease(min(max(age/0.38,0),1.0))
            xoff = int((1-t_in)*50)   # slides in from right

            ry = 100 + i*RH
            if i%2 == 0:
                d.rectangle([40, ry-4, W-40, ry+RH-6], fill=(14,14,20))

            # Draw with slide
            d.text((XL+xoff, ry), lbl, font=f_lbl, fill=DIM)

            # Color-code numeric values
            bv_col = (GRN if bv.startswith("+") or ("20" in bv and "рік" in rows[i][0]) else
                      RED if bv.startswith("−") or bv.startswith("-") else TXT)
            dv_col = (GRN if dv.startswith("+") or ("14" in dv)      else
                      RED if dv.startswith("−") or dv.startswith("-") else TXT)

            d.text((XB+xoff, ry), bv, font=f_val, fill=bv_col)
            d.text((XD+xoff, ry), dv, font=f_val, fill=dv_col)

            # Thin divider
            if i < len(rows)-1:
                d.line([40, ry+RH-7, W-40, ry+RH-7], fill=(28,28,38), width=1)

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.0, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 7. ANIMATED GROWTH CHART
# ════════════════════════════════════════════════════════════════
def growth_chart(title, subtitle, data_points, color, duration,
                 y_label_fmt="${}k", baseline_label="$10k"):
    """
    data_points: list of (year_label, value) — values normalized 0-1
    Line draws progressively over first ~2/3 of duration.
    """
    f_tit  = _lf(FONT_SANS_BOLD, 28)
    f_sub  = _lf(FONT_SANS,      17)
    f_ax   = _lf(FONT_SANS,      14)
    f_val  = _lf(FONT_SANS_BOLD, 22)

    CX1, CX2 = 80, W-60     # chart area X
    CY1, CY2 = 85, H-65     # chart area Y
    cw = CX2 - CX1
    ch = CY2 - CY1

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        arr[0:4] = np.array(color, dtype=np.float32)
        img = Image.fromarray(arr.astype(np.uint8))
        d   = ImageDraw.Draw(img)

        d.text((CX1, 14), title,    font=f_tit, fill=TXT)
        d.text((CX1, 50), subtitle, font=f_sub, fill=DIM)

        # Grid lines
        for gy in [0.0, 0.25, 0.5, 0.75, 1.0]:
            y = CY2 - int(gy*ch)
            d.line([CX1, y, CX2, y], fill=(28,28,40), width=1)

        # Baseline axis
        d.line([CX1, CY2, CX2, CY2], fill=(55,55,68), width=2)
        d.line([CX1, CY1, CX1, CY2], fill=(55,55,68), width=2)

        # How many points to draw (animates in)
        draw_frac = ease(min(t/max(duration*0.65, 1.0), 1.0))
        n  = len(data_points)
        nd = max(1, int(draw_frac * (n-1)) + 1)

        # X positions
        xs = [CX1 + int(i/(n-1)*cw) for i in range(n)]

        # Draw line
        pts = []
        for i in range(min(nd, n)):
            lbl, val = data_points[i]
            y = CY2 - int(val*ch)
            pts.append((xs[i], y))

        # Gradient fill under line
        if len(pts) >= 2:
            poly = pts + [(pts[-1][0], CY2), (pts[0][0], CY2)]
            fill_img = Image.new("RGBA",(W,H),(0,0,0,0))
            fd = ImageDraw.Draw(fill_img)
            fd.polygon(poly, fill=(*color, 30))
            img.paste(Image.fromarray(np.array(fill_img)[:,:,:3]),
                      mask=fill_img.split()[3])
            d = ImageDraw.Draw(img)

        for i in range(len(pts)-1):
            d.line([pts[i], pts[i+1]], fill=color, width=3)

        # Dot at last drawn point
        if pts:
            lx, ly = pts[-1]
            d.ellipse([lx-7,ly-7,lx+7,ly+7], fill=color)
            d.ellipse([lx-4,ly-4,lx+4,ly+4], fill=BG)

        # X labels (years)
        step = max(1, n//8)
        for i in range(0, n, step):
            lbl, _ = data_points[i]
            lb = d.textbbox((0,0), lbl, font=f_ax)
            d.text((xs[i]-(lb[2]-lb[0])//2, CY2+8), lbl, font=f_ax, fill=DIM)

        # Current value label
        if pts and draw_frac > 0.1:
            lx, ly = pts[-1]
            idx = min(len(pts)-1, len(data_points)-1)
            _, raw_v = data_points[idx]
            lv_txt = y_label_fmt.format(int(raw_v*100))
            lv_b = d.textbbox((0,0), lv_txt, font=f_val)
            lv_x = min(lx+10, W-80)
            d.text((lv_x+2,ly-20+2), lv_txt, font=f_val, fill=(0,0,0,140))
            d.text((lv_x,  ly-20),   lv_txt, font=f_val, fill=color)

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.0, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 8. CTA CARD — viewer engagement
# ════════════════════════════════════════════════════════════════
def cta_scene(duration):
    f_q    = _lf(FONT_SANS_BOLD, 40)
    f_sub  = _lf(FONT_SANS,      24)
    f_hint = _lf(FONT_SANS,      19)

    question = "Якби тобі дали $10,000 прямо зараз —"
    q2       = "чий підхід ти б обрав?"
    hint     = "Пиши в коментарях: БАФФЕТ або ДАЛІО  ↓"

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        # Animated gradient accent
        sweep = (t*0.22) % 1.0
        cx    = int(sweep*W*1.3 - W*0.15)
        dist2 = np.sqrt(((_x-cx)/(W*0.45))**2 + ((_y-H/2)/(H*0.6))**2)
        glow  = np.clip(1.0-dist2*1.1,0,1)*0.14
        arr[:,:,0] += glow*CB[0]; arr[:,:,1] += glow*CB[1]; arr[:,:,2] += glow*CB[2]
        arr[:,:,0] += glow*CD[0]*0.5; arr[:,:,1] += glow*CD[1]*0.5; arr[:,:,2] += glow*CD[2]*0.5

        img = Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # Central line
        d.line([W//2-1, 60, W//2-1, H-60], fill=(35,35,50), width=1)

        p1 = ease(min(max((t-0.4)/0.5,0),1.0))
        p2 = ease(min(max((t-0.9)/0.5,0),1.0))
        p3 = ease(min(max((t-1.5)/0.5,0),1.0))

        for (txt, font, col, prog, ypos) in [
            (question, f_q,   TXT, p1, H//2-80),
            (q2,       f_q,   TXT, p2, H//2-20),
            (hint,     f_hint,DIM, p3, H//2+65),
        ]:
            if prog < 0.01: continue
            tb = d.textbbox((0,0), txt, font=font)
            tw = tb[2]-tb[0]
            tx = (W-tw)//2
            yoff = int((1-prog)*22)
            d.text((tx+2,ypos+yoff+2), txt, font=font, fill=(0,0,0,int(160*prog)))
            d.text((tx,  ypos+yoff),   txt, font=font, fill=(*col[:3],int(255*prog)))

        # Pulsing bar at bottom
        pulse = (math.sin(t*math.pi*1.6)+1)/2
        bar_col = tuple(int(c*0.5 + c*0.5*pulse) for c in CB)
        d.rectangle([0,H-6,W,H], fill=bar_col)
        d.rectangle([0,0,W,4],   fill=bar_col)

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.5, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 9. PERSONALITY TEST — split screen "Who are you?"
# ════════════════════════════════════════════════════════════════
def personality_test(duration):
    buffett_traits = [
        "Читаєш 500 сторінок на тиждень",
        "Любиш вивчати бізнес у деталях",
        "Готовий чекати роками",
        "Ok з тим, що акція падає -30%",
        "Хочеш BEAT the market",
    ]
    dalio_traits = [
        "Хочеш спати спокійно",
        "Ринок тебе нервує",
        "Захист важливіший за прибуток",
        "Любиш правила та системи",
        "Хочеш SURVIVE the market",
    ]

    f_hdr   = _lf(FONT_SANS_BOLD, 26)
    f_sub   = _lf(FONT_SANS_BOLD, 16)
    f_trait = _lf(FONT_SANS,      20)
    f_q     = _lf(FONT_SANS_BOLD, 22)

    trait_interval = (duration - 2.0) / max(len(buffett_traits), 1)

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        # Halves tint
        arr[:, :W//2, 0] += 8; arr[:, :W//2, 1] += 4  # subtle amber tint
        arr[:, W//2:, 2] += 10                           # subtle teal tint
        arr[0:4]   = np.array(CB, dtype=np.float32)
        arr[H-4:H] = np.array(CD, dtype=np.float32)

        img = Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # Center divider
        d.line([W//2, 0, W//2, H], fill=(35,35,50), width=2)

        # Question header
        qp = ease(min(t/0.45,1.0))
        if qp > 0.01:
            q_txt = "ХТО ТИ ЗА ТИПОМ ІНВЕСТОРА?"
            qb = d.textbbox((0,0), q_txt, font=f_q)
            d.text(((W-(qb[2]-qb[0]))//2+2, 14), q_txt, font=f_q, fill=(0,0,0,160))
            d.text(((W-(qb[2]-qb[0]))//2,   12), q_txt, font=f_q, fill=TXT)

        # Column headers
        hp = ease(min(max((t-0.4)/0.45,0),1.0))
        if hp > 0.01:
            for (nm, col, bx) in [("ТИ — БАФФЕТ, якщо...",CB,0),
                                   ("ТИ — ДАЛІО, якщо...",CD,W//2)]:
                nb = d.textbbox((0,0), nm, font=f_hdr)
                nw = nb[2]-nb[0]
                nx = bx+(W//2-nw)//2
                d.rectangle([bx+15, 50, bx+W//2-15, 53], fill=col)
                d.text((nx, 58), nm, font=f_hdr, fill=col)

        # Traits appear one by one
        for i, (bt, dt) in enumerate(zip(buffett_traits, dalio_traits)):
            at = 1.0 + i*trait_interval
            if t < at - 0.04: continue
            age  = t - at
            t_in = ease(min(max(age/0.38,0),1.0))
            ypos = 105 + i*50
            xoff = int((1-t_in)*30)

            # Buffett trait (left)
            d.text((30+xoff, ypos), "▸", font=f_sub, fill=CB)
            d.text((50+xoff, ypos), bt,  font=f_trait, fill=TXT)

            # Dalio trait (right)
            d.text((W//2+30+xoff, ypos), "▸", font=f_sub, fill=CD)
            d.text((W//2+50+xoff, ypos), dt,  font=f_trait, fill=TXT)

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.0, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 10. ALL WEATHER PORTFOLIO VISUAL
# ════════════════════════════════════════════════════════════════
def allweather_diagram(duration):
    """Animated All Weather portfolio allocation bars."""
    allocations = [
        ("Акції США",          30, CD),
        ("Довг. облігації",    40, (100,160,220)),
        ("Серед. облігації",   15, (70,130,190)),
        ("Золото",              7.5, (210,180,60)),
        ("Сировина",           7.5, (160,130,80)),
    ]
    f_tit = _lf(FONT_SANS_BOLD, 28)
    f_sub = _lf(FONT_SANS,      17)
    f_lbl = _lf(FONT_SANS_BOLD, 18)
    f_pct = _lf(FONT_SANS_BOLD, 22)

    BAR_X1, BAR_X2 = 320, W-60
    ROW_H = 62

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        arr[0:4] = np.array(CD, dtype=np.float32)
        img = Image.fromarray(arr.astype(np.uint8))
        d   = ImageDraw.Draw(img)

        d.text((50, 14), "ALL WEATHER PORTFOLIO", font=f_tit, fill=CD)
        d.text((50, 50), "Ray Dalio · Bridgewater — «Захист від будь-якої погоди»",
               font=f_sub, fill=DIM)

        bar_interval = (duration-1.2) / len(allocations)

        for i, (lbl, pct, col) in enumerate(allocations):
            at   = 0.8 + i*bar_interval
            if t < at - 0.04: continue
            age  = t - at
            prog = ease(min(max(age/0.6,0),1.0))

            ry = 95 + i*ROW_H

            # Label
            d.text((50, ry+12), lbl, font=f_lbl, fill=TXT)

            # Bar track
            d.rectangle([BAR_X1, ry+10, BAR_X2, ry+36], fill=(20,20,28))

            # Animated fill
            max_bw = BAR_X2 - BAR_X1
            fill_w = int(max_bw * (pct/100) * prog)
            if fill_w > 0:
                d.rectangle([BAR_X1, ry+10, BAR_X1+fill_w, ry+36], fill=col)

            # Percentage label
            pct_txt = f"{pct}%"
            pb = d.textbbox((0,0), pct_txt, font=f_pct)
            px = BAR_X1 + fill_w + 10
            d.text((px+2, ry+8+2), pct_txt, font=f_pct, fill=(0,0,0,150))
            d.text((px,   ry+8),   pct_txt, font=f_pct, fill=col)

        # Footer
        d.text((50, H-35),
               "Мета: максимум 10% просадки за будь-якого ринку",
               font=f_sub, fill=(80,80,90))

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.0, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# 11. BERKSHIRE TOP HOLDINGS
# ════════════════════════════════════════════════════════════════
def berkshire_holdings(duration):
    holdings = [
        ("Apple (AAPL)",       47.0, CB),
        ("Bank of America",    10.2, (180,140,40)),
        ("American Express",    8.0, (160,120,30)),
        ("Coca-Cola",           6.5, (140,100,20)),
        ("Chevron",             5.8, (120, 90,15)),
    ]
    f_tit = _lf(FONT_SANS_BOLD, 28)
    f_sub = _lf(FONT_SANS,      17)
    f_lbl = _lf(FONT_SANS_BOLD, 18)
    f_pct = _lf(FONT_SANS_BOLD, 22)
    f_note= _lf(FONT_SANS,      15)

    BAR_X1, BAR_X2 = 320, W-60
    ROW_H = 60

    def frame(t):
        arr = np.full((H,W,3), BG, dtype=np.float32)
        arr[0:4] = np.array(CB, dtype=np.float32)
        img = Image.fromarray(arr.astype(np.uint8))
        d   = ImageDraw.Draw(img)

        d.text((50, 14), "BERKSHIRE HATHAWAY — ТОП ПОЗИЦІЇ", font=f_tit, fill=CB)
        d.text((50, 50), "Warren Buffett · % від портфеля (2024)",
               font=f_sub, fill=DIM)

        bar_interval = (duration-1.2) / len(holdings)

        for i, (lbl, pct, col) in enumerate(holdings):
            at   = 0.8 + i*bar_interval
            if t < at - 0.04: continue
            age  = t - at
            prog = ease(min(max(age/0.55,0),1.0))

            ry = 95 + i*ROW_H
            d.text((50, ry+10), lbl, font=f_lbl, fill=TXT)

            # Bar track + fill
            d.rectangle([BAR_X1, ry+8, BAR_X2, ry+34], fill=(20,20,28))
            max_bw = BAR_X2 - BAR_X1
            fill_w = int(max_bw * (pct/50) * prog)  # scale: 50% = full bar
            if fill_w > 0:
                d.rectangle([BAR_X1, ry+8, BAR_X1+fill_w, ry+34], fill=col)

            pct_txt = f"{pct}%"
            pb = d.textbbox((0,0), pct_txt, font=f_pct)
            d.text((BAR_X1+fill_w+10+2, ry+6+2), pct_txt,
                   font=f_pct, fill=(0,0,0,150))
            d.text((BAR_X1+fill_w+10,   ry+6),   pct_txt, font=f_pct, fill=col)

        d.text((50, H-35),
               "47% в одній компанії — це і є «концентрований» підхід",
               font=f_note, fill=(80,80,90))

        result = np.array(img).astype(np.float32)
        result = np.clip(result + GRAIN*4.0, 0, 255)
        result[:,:,0] *= VIG; result[:,:,1] *= VIG; result[:,:,2] *= VIG
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


# ════════════════════════════════════════════════════════════════
# DATA FOR CHARTS
# ════════════════════════════════════════════════════════════════

# Berkshire vs S&P — 30 years (relative growth, normalized)
_berk_years = list(range(1994, 2025, 2))
_berk_vals  = [0.05, 0.10, 0.17, 0.25, 0.35, 0.30, 0.42,
               0.50, 0.60, 0.68, 0.72, 0.78, 0.83, 0.88,
               0.94, 1.00]
_berk_data  = [(str(y), v) for y, v in zip(_berk_years, _berk_vals)]

# All Weather smooth curve (much less volatility)
_aw_years = list(range(1994, 2025, 2))
_aw_vals  = [0.05, 0.10, 0.15, 0.21, 0.29, 0.35, 0.40,
             0.47, 0.53, 0.58, 0.63, 0.68, 0.73, 0.78,
             0.84, 0.90]
_aw_data  = [(str(y), v) for y, v in zip(_aw_years, _aw_vals)]


# ════════════════════════════════════════════════════════════════
# CAPTIONS
# ════════════════════════════════════════════════════════════════
BUFFETT_CAPS = [
    (1.0,  9.0,  "Народився в Омасі, Небраска. 1930 рік."),
    (9.5,  18.0, "Перша інвестиція — $114 в 11 років. Повернув 50%."),
    (18.5, 28.0, "Запустив Berkshire Hathaway з $10 мільйонів."),
    (28.5, 37.0, "Сьогодні — $178 мільярдів особистого капіталу."),
]

DALIO_CAPS = [
    (1.0,  9.0,  "Народився в Нью-Йорку. 1949 рік."),
    (9.5,  18.0, "Перший офіс — двокімнатна квартира на Манхеттені."),
    (18.5, 28.0, "2008 рік: Bridgewater заробив +14% поки ринок впав -37%."),
    (28.5, 37.0, "Найбільший хедж-фонд у світі — $150 мільярдів під управлінням."),
]


# ════════════════════════════════════════════════════════════════
# BUILD TIMELINE
# ════════════════════════════════════════════════════════════════
tl = Timeline(W=W, H=H)

# ── HOOK ────────────────────────────────────────────────────────
tl.add_clip(kinetic_text([
    ("Двоє людей.",         TXT, 58,  0.3),
    ("Два підходи.",        TXT, 58,  1.4),
    ("Два мільярди.",       CB,  74,  2.5),
    ("Один правий для тебе.",DIM, 36, 3.8),
], duration=9.0, accent=CB),
duration=9.0, transition="fade_black", transition_dur=0.6)

# ── SPLIT VS ────────────────────────────────────────────────────
tl.add_clip(split_vs(duration=10.0),
            duration=10.0, transition="dissolve", transition_dur=0.7)

# ── BUFFETT PROFILE ─────────────────────────────────────────────
tl.add_clip(
    profile_scene(PHOTO_B, "WARREN BUFFETT", "Berkshire Hathaway",
                  CB, BUFFETT_CAPS, duration=40.0,
                  zoom_s=1.0, zoom_e=1.08,
                  pan_s=(0.50,0.50), pan_e=(0.53,0.52)),
    duration=40.0, transition="burn", transition_dur=0.8)

# ── BUFFETT PHILOSOPHY ──────────────────────────────────────────
tl.add_clip(kinetic_text([
    ("«Купуй великі компанії.",    CB,  44, 0.3),
    ("Тримай їх вічно.»",          CB,  44, 1.6),
    ("",                            TXT, 10, 2.8),
    ("Правило №1: Не втрачай гроші.", TXT, 30, 3.0),
    ("Правило №2: Не забувай правило №1.", TXT, 30, 4.4),
], duration=12.0, accent=CB),
duration=12.0, transition="dissolve", transition_dur=0.7)

# ── 2008 CRISIS IMPACT ──────────────────────────────────────────
tl.add_clip(impact_stat(
    "2008", "Фінансова криза", "Рік що все змінив",
    TXT, duration=5.0),
duration=5.0, transition="flash", transition_dur=0.35)

tl.add_clip(impact_split(
    "2008 — ХТО ВИЖИВ?",
    "+14%", "ДАЛІО / Bridgewater", GRN,
    "−25%", "БАФФЕТ / Berkshire",  RED,
    duration=9.0),
duration=9.0, transition="cut", transition_dur=0.0)

# ── DALIO PROFILE ───────────────────────────────────────────────
tl.add_clip(
    profile_scene(PHOTO_D, "RAY DALIO", "Bridgewater Associates",
                  CD, DALIO_CAPS, duration=40.0,
                  zoom_s=1.0, zoom_e=1.06,
                  pan_s=(0.50,0.48), pan_e=(0.50,0.52)),
    duration=40.0, transition="dissolve", transition_dur=0.9)

# ── DALIO PHILOSOPHY ────────────────────────────────────────────
tl.add_clip(kinetic_text([
    ("«Не намагайся вгадати переможця.",  CD,  40, 0.3),
    ("Диверсифікуй, розумій цикли.»",     CD,  40, 1.7),
    ("",                                   TXT, 10, 3.0),
    ("Мета: пережити БУДЬ-ЯКУ кризу.",    TXT, 30, 3.2),
    ("Максимальна просадка — 10%.",        DIM, 26, 4.6),
], duration=12.0, accent=CD),
duration=12.0, transition="dissolve", transition_dur=0.7)

# ── COMPARISON TABLE ────────────────────────────────────────────
tl.add_clip(comparison_table(duration=40.0),
            duration=40.0, transition="dissolve", transition_dur=0.8)

# ── BERKSHIRE HOLDINGS ──────────────────────────────────────────
tl.add_clip(berkshire_holdings(duration=22.0),
            duration=22.0, transition="dissolve", transition_dur=0.7)

# ── ALL WEATHER DIAGRAM ─────────────────────────────────────────
tl.add_clip(allweather_diagram(duration=22.0),
            duration=22.0, transition="dissolve", transition_dur=0.7)

# ── GROWTH CHARTS ───────────────────────────────────────────────
tl.add_clip(growth_chart(
    "BERKSHIRE HATHAWAY — 30 РОКІВ",
    "Дохідність ~20%/рік · Концентровані ставки",
    _berk_data, CB, duration=20.0, y_label_fmt="${}x",
), duration=20.0, transition="dissolve", transition_dur=0.7)

tl.add_clip(growth_chart(
    "ALL WEATHER PORTFOLIO — 30 РОКІВ",
    "Дохідність ~12%/рік · Мінімальна просадка",
    _aw_data, CD, duration=20.0, y_label_fmt="${}x",
), duration=20.0, transition="dissolve", transition_dur=0.7)

# ── CTA ─────────────────────────────────────────────────────────
tl.add_clip(cta_scene(duration=20.0),
            duration=20.0, transition="fade_black", transition_dur=0.6)

# ── PERSONALITY TEST ────────────────────────────────────────────
tl.add_clip(personality_test(duration=50.0),
            duration=50.0, transition="dissolve", transition_dur=0.8)

# ── VERDICT QUOTE ───────────────────────────────────────────────
tl.add_clip(kinetic_text([
    ("Немає правильної відповіді.", TXT, 46, 0.3),
    ("Є твоя відповідь.",           TXT, 46, 1.8),
    ("",                             TXT,  8, 3.2),
    ("Баффет = мистецтво вибору.",  CB,  32, 3.5),
    ("Даліо = математика захисту.", CD,  32, 5.0),
    ("Обидва = результат.",         GRN, 36, 6.5),
], duration=15.0, accent=GRN),
duration=15.0, transition="dissolve", transition_dur=0.8)

# ── OUTRO ───────────────────────────────────────────────────────
tl.add_title(
    title="БАФФЕТ vs ДАЛІО",
    subtitle="Якого інвестора ти обрав?  ↓ Коментар",
    duration=8.0,
    transition="fade_black",
    transition_dur=0.8,
    bg_color=(4, 4, 8),
    title_color=(220, 200, 160),
    sub_color=(140, 130, 110),
)

# ── RENDER ──────────────────────────────────────────────────────
frame_fn, total = tl.build()
print(f"Total duration: {total:.1f}s  ({total/60:.1f} min)")
print(f"Frames: {int(total*FPS):,}  •  Output: {OUTPUT}")
render(frame_fn, total, OUTPUT, fps=FPS, crf=20)
