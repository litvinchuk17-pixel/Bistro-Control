"""
cinematic.py — Reusable Netflix-doc style video editing library
Transitions, color grading, photo inserts (Ken Burns), quote cards,
title cards, and film effects.
"""
from __future__ import annotations
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from typing import Callable, List, Tuple, Optional

# ─── TYPES ─────────────────────────────────────────────────────────
Frame    = np.ndarray   # shape (H, W, 3), dtype uint8
FrameFn  = Callable[[float], Frame]   # t → frame

# ─── CONSTANTS ─────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS = os.path.join(_HERE, "fonts")
FONT_SANS      = os.path.join(_FONTS, "LiberationSans-Regular.ttf")
FONT_SANS_BOLD = os.path.join(_FONTS, "LiberationSans-Bold.ttf")
FONT_SERIF     = os.path.join(_FONTS, "FreeSerif.ttf")
FONT_SERIF_IT  = os.path.join(_FONTS, "FreeSerifItalic.ttf")


# ══════════════════════════════════════════════════════════════════
# EASING
# ══════════════════════════════════════════════════════════════════

def ease_in_out(t: float, p: float = 2.0) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return (2 * t) ** p / 2
    return 1 - (2 * (1 - t)) ** p / 2

def ease_out(t: float, p: float = 2.0) -> float:
    return 1 - (1 - max(0.0, min(1.0, t))) ** p

def ease_in(t: float, p: float = 2.0) -> float:
    return max(0.0, min(1.0, t)) ** p


# ══════════════════════════════════════════════════════════════════
# COLOR GRADING
# ══════════════════════════════════════════════════════════════════

def grade_netflix(arr: np.ndarray) -> np.ndarray:
    """
    Netflix documentary look:
    - Lifted blacks (no pure black)
    - Slightly desaturated midtones
    - Cool shadows, warm highlights
    - High contrast S-curve
    """
    f = arr.astype(np.float32) / 255.0

    # Lift blacks slightly
    f = f * 0.92 + 0.03

    # S-curve contrast
    f = np.where(f < 0.5,
                 2 * f * f,
                 1 - 2 * (1 - f) ** 2)
    f = f * 0.85 + 0.075   # re-range after S

    # Use per-pixel luminance (2-D) for shadow/hi masks to avoid shape mismatch
    _lum = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]

    # Cool shadows (reduce red / boost blue in darks)
    shadow_mask = np.clip(1.0 - _lum * 2.5, 0, 1)  # (H,W)
    f[:, :, 0] -= shadow_mask * 0.018   # R −
    f[:, :, 2] += shadow_mask * 0.025   # B +

    # Warm highlights (boost red/green in brights)
    hi_mask = np.clip((_lum - 0.6) * 2.5, 0, 1)    # (H,W)
    f[:, :, 0] += hi_mask * 0.02        # R +
    f[:, :, 1] += hi_mask * 0.012       # G +

    # Luminance (2-D) used for shadow/hi masks and desaturation
    lum2d = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]

    # Very slight desaturation
    lum = lum2d[:, :, np.newaxis]
    f = f * 0.90 + lum * 0.10

    return np.clip(f * 255, 0, 255).astype(np.uint8)


def grade_sepia_archive(arr: np.ndarray, strength: float = 0.55) -> np.ndarray:
    """Warm sepia / archive look."""
    a = arr.astype(np.float32)
    r = a[:, :, 0] * 0.393 + a[:, :, 1] * 0.769 + a[:, :, 2] * 0.189
    g = a[:, :, 0] * 0.349 + a[:, :, 1] * 0.686 + a[:, :, 2] * 0.168
    b = a[:, :, 0] * 0.272 + a[:, :, 1] * 0.534 + a[:, :, 2] * 0.131
    sepia = np.stack([r, g, b], axis=2)
    return np.clip(a * (1 - strength) + sepia * strength, 0, 255).astype(np.uint8)


def add_vignette(arr: np.ndarray, strength: float = 0.65,
                 aspect: float = 1.4) -> np.ndarray:
    H, W = arr.shape[:2]
    y_idx, x_idx = np.mgrid[0:H, 0:W]
    dx = (x_idx - W / 2) / (W / 2)
    dy = (y_idx - H / 2) / (H / 2)
    dist = np.sqrt(dx ** 2 + (dy * aspect) ** 2)
    mask = np.clip(1.0 - (dist - 0.45) * strength * 1.8, 0.15, 1.0)
    out = arr.astype(np.float32)
    out[:, :, 0] *= mask
    out[:, :, 1] *= mask
    out[:, :, 2] *= mask
    return np.clip(out, 0, 255).astype(np.uint8)


def add_grain(arr: np.ndarray, intensity: float = 6.0,
              rng: Optional[np.random.Generator] = None) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng()
    noise = rng.normal(0, intensity, arr.shape).astype(np.float32)
    return np.clip(arr.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def add_letterbox(arr: np.ndarray, ratio: float = 2.39) -> np.ndarray:
    """Add black letterbox bars to reach target aspect ratio."""
    H, W = arr.shape[:2]
    current = W / H
    if abs(current - ratio) < 0.02:
        return arr
    if current < ratio:
        # Need to add bars on sides — unusual, skip
        return arr
    # Add bars top/bottom
    target_h = int(W / ratio)
    if target_h >= H:
        return arr
    pad = (H - target_h) // 2
    out = arr.copy()
    out[:pad] = 0
    out[H - pad:] = 0
    return out


# ══════════════════════════════════════════════════════════════════
# TRANSITIONS
# ══════════════════════════════════════════════════════════════════

def _alpha_blend(a: Frame, b: Frame, f: float) -> Frame:
    f = max(0.0, min(1.0, f))
    return np.clip(a.astype(np.float32) * (1 - f) + b.astype(np.float32) * f,
                   0, 255).astype(np.uint8)


def tr_cross_dissolve(fn_a: FrameFn, fn_b: FrameFn,
                      dur_a: float, dur_b: float,
                      tr_dur: float) -> FrameFn:
    """Smooth cross-dissolve between two clips."""
    def frame(t: float) -> Frame:
        if t <= dur_a - tr_dur:
            return fn_a(t)
        if t >= dur_a:
            return fn_b(t - dur_a)
        f = ease_in_out((t - (dur_a - tr_dur)) / tr_dur)
        ta = t
        tb = t - (dur_a - tr_dur)
        fa = fn_a(min(ta, dur_a - 0.001))
        fb = fn_b(max(tb, 0))
        return _alpha_blend(fa, fb, f)
    return frame


def tr_fade_black(fn_a: FrameFn, fn_b: FrameFn,
                  dur_a: float, dur_b: float,
                  fade_out: float = 0.5, fade_in: float = 0.5) -> FrameFn:
    """Fade to black, then fade in next clip."""
    def frame(t: float) -> Frame:
        if t <= dur_a - fade_out:
            return fn_a(t)
        elif t <= dur_a:
            f = ease_in((t - (dur_a - fade_out)) / fade_out)
            fa = fn_a(min(t, dur_a - 0.001))
            black = np.zeros_like(fa)
            return _alpha_blend(fa, black, f)
        elif t <= dur_a + fade_in:
            f = ease_out((t - dur_a) / fade_in)
            fb = fn_b(max(0.0, t - dur_a))
            black = np.zeros_like(fb)
            return _alpha_blend(black, fb, f)
        else:
            return fn_b(t - dur_a)
    return frame


def tr_flash_white(fn_a: FrameFn, fn_b: FrameFn,
                   dur_a: float, dur_b: float,
                   flash_dur: float = 0.35) -> FrameFn:
    """Quick flash to white — modern documentary cut."""
    half = flash_dur / 2
    def frame(t: float) -> Frame:
        if t <= dur_a - half:
            return fn_a(t)
        elif t <= dur_a:
            f = ease_in((t - (dur_a - half)) / half)
            fa = fn_a(min(t, dur_a - 0.001))
            white = np.full_like(fa, 255)
            return _alpha_blend(fa, white, f)
        elif t <= dur_a + half:
            f = ease_out((t - dur_a) / half)
            fb = fn_b(max(0.0, t - dur_a))
            white = np.full_like(fb, 255)
            return _alpha_blend(white, fb, f)
        else:
            return fn_b(t - dur_a)
    return frame


def tr_film_burn(fn_a: FrameFn, fn_b: FrameFn,
                 dur_a: float, dur_b: float,
                 burn_dur: float = 0.6) -> FrameFn:
    """Warm orange film burn between clips."""
    burn_color = np.array([255, 140, 30], dtype=np.float32)
    half = burn_dur / 2
    def frame(t: float) -> Frame:
        if t <= dur_a - half:
            return fn_a(t)
        elif t <= dur_a:
            f = ease_in((t - (dur_a - half)) / half)
            fa = fn_a(min(t, dur_a - 0.001))
            out = fa.astype(np.float32)
            out[:, :] = out * (1 - f) + burn_color * f
            return np.clip(out, 0, 255).astype(np.uint8)
        elif t <= dur_a + half:
            f = ease_out((t - dur_a) / half)
            fb = fn_b(max(0.0, t - dur_a))
            out = fb.astype(np.float32)
            out[:, :] = burn_color * (1 - f) + out * f
            return np.clip(out, 0, 255).astype(np.uint8)
        else:
            return fn_b(t - dur_a)
    return frame


def tr_push_left(fn_a: FrameFn, fn_b: FrameFn,
                 dur_a: float, dur_b: float,
                 tr_dur: float = 0.5) -> FrameFn:
    """Horizontal push (slide left) — Netflix-style."""
    def frame(t: float) -> Frame:
        if t <= dur_a - tr_dur:
            return fn_a(t)
        if t >= dur_a:
            return fn_b(t - dur_a)
        f = ease_in_out((t - (dur_a - tr_dur)) / tr_dur)
        fa = fn_a(min(t, dur_a - 0.001))
        fb = fn_b(max(0.0, t - (dur_a - tr_dur)))
        H, W = fa.shape[:2]
        off = int(W * f)
        out = np.empty_like(fa)
        if off < W:
            out[:, :W - off] = fa[:, off:]
            out[:, W - off:] = fb[:, :off]
        else:
            out = fb
        return out
    return frame


# ══════════════════════════════════════════════════════════════════
# PHOTO INSERT  (Ken Burns effect)
# ══════════════════════════════════════════════════════════════════

def make_ken_burns(image_path: str,
                   duration: float,
                   W: int, H: int,
                   zoom_start: float = 1.0,
                   zoom_end:   float = 1.12,
                   pan_start:  Tuple[float, float] = (0.5, 0.5),
                   pan_end:    Tuple[float, float] = (0.52, 0.52),
                   grade: str = "netflix",
                   fade_in: float = 0.4,
                   fade_out: float = 0.4) -> FrameFn:
    """
    Ken Burns pan+zoom effect on a still photo.
    pan values are (cx, cy) in 0–1 relative to source image.
    grade: "netflix" | "sepia" | "none"
    """
    src = Image.open(image_path).convert("RGB")
    sw, sh = src.size

    def frame(t: float) -> Frame:
        f = ease_in_out(t / max(duration, 0.001))
        zoom = zoom_start + (zoom_end - zoom_start) * f
        cx   = pan_start[0] + (pan_end[0] - pan_start[0]) * f
        cy   = pan_start[1] + (pan_end[1] - pan_start[1]) * f

        # Region to crop from source
        crop_w = sw / zoom
        crop_h = sh / zoom
        x0 = cx * sw - crop_w / 2
        y0 = cy * sh - crop_h / 2
        x0 = max(0, min(sw - crop_w, x0))
        y0 = max(0, min(sh - crop_h, y0))

        cropped = src.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        resized = cropped.resize((W, H), Image.LANCZOS)
        arr = np.array(resized)

        # Color grade
        if grade == "netflix":
            arr = grade_netflix(arr)
        elif grade == "sepia":
            arr = grade_sepia_archive(arr)

        arr = add_vignette(arr)

        # Fade
        alpha = 1.0
        if t < fade_in:
            alpha = ease_out(t / fade_in)
        elif t > duration - fade_out:
            alpha = ease_out((duration - t) / fade_out)

        if alpha < 0.999:
            arr = (arr.astype(np.float32) * alpha).astype(np.uint8)

        return arr

    return frame


# ══════════════════════════════════════════════════════════════════
# QUOTE / TITLE CARDS
# ══════════════════════════════════════════════════════════════════

def _wrap_text(text: str, font: ImageFont.FreeTypeFont,
               max_w: int, draw: ImageDraw.Draw) -> List[str]:
    """Wrap text to fit max_w pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_quote_card(quote: str,
                    attribution: str = "",
                    duration: float = 5.0,
                    W: int = 1280,
                    H: int = 536,
                    style: str = "netflix",
                    fade_in: float = 0.6,
                    fade_out: float = 0.6,
                    bg_color: Tuple = (8, 8, 12),
                    text_color: Tuple = (240, 235, 225),
                    attr_color: Tuple = (150, 140, 125)) -> FrameFn:
    """
    Netflix doc-style quote card.
    Renders once, then fades in/out.
    """
    # Build static frame
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    pad = int(W * 0.10)
    max_w = W - pad * 2

    # Quote text
    q_size = max(24, W // 26)
    q_font = ImageFont.truetype(FONT_SERIF_IT, q_size)
    q_lines = _wrap_text(f'"{quote}"', q_font, max_w, draw)
    q_line_h = q_size + int(q_size * 0.45)
    q_total_h = len(q_lines) * q_line_h

    # Attribution text
    a_size = max(16, W // 42)
    a_font = ImageFont.truetype(FONT_SANS, a_size)

    total_h = q_total_h + (a_size + 24 if attribution else 0)
    y_start = (H - total_h) // 2

    # Thin decorative line above
    line_y = y_start - 20
    line_x1 = W // 2 - 40
    line_x2 = W // 2 + 40
    draw.line([line_x1, line_y, line_x2, line_y], fill=attr_color, width=1)

    for i, line in enumerate(q_lines):
        bbox = draw.textbbox((0, 0), line, font=q_font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = y_start + i * q_line_h
        # Shadow
        draw.text((x + 2, y + 2), line, font=q_font, fill=(0, 0, 0, 180))
        draw.text((x, y), line, font=q_font, fill=text_color)

    # Attribution
    if attribution:
        a_text = f"— {attribution}"
        a_bbox = draw.textbbox((0, 0), a_text, font=a_font)
        a_x = (W - (a_bbox[2] - a_bbox[0])) // 2
        a_y = y_start + q_total_h + 18
        draw.text((a_x, a_y), a_text, font=a_font, fill=attr_color)

    # Thin line below
    bl_y = y_start + total_h + 24
    draw.line([line_x1, bl_y, line_x2, bl_y], fill=attr_color, width=1)

    static = np.array(img)

    def frame(t: float) -> Frame:
        alpha = 1.0
        if t < fade_in:
            alpha = ease_in_out(t / fade_in)
        elif t > duration - fade_out:
            alpha = ease_in_out((duration - t) / fade_out)
        arr = static.astype(np.float32) * alpha
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame


def make_title_card(title: str,
                    subtitle: str = "",
                    duration: float = 4.0,
                    W: int = 1280,
                    H: int = 536,
                    fade_in: float = 0.5,
                    fade_out: float = 0.5,
                    bg_color: Tuple = (6, 6, 10),
                    title_color: Tuple = (240, 235, 220),
                    sub_color: Tuple = (160, 150, 135)) -> FrameFn:
    """
    Netflix documentary title card (e.g. date/location chyron).
    """
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    t_size = max(32, W // 20)
    s_size = max(18, W // 38)
    t_font = ImageFont.truetype(FONT_SANS_BOLD, t_size)
    s_font = ImageFont.truetype(FONT_SANS, s_size)

    # Title
    tb = draw.textbbox((0, 0), title, font=t_font)
    tx = (W - (tb[2] - tb[0])) // 2
    ty = H // 2 - t_size - (s_size + 10 if subtitle else 0) // 2
    draw.text((tx, ty), title, font=t_font, fill=title_color)

    # Thin accent line
    line_x1 = W // 2 - 60
    line_x2 = W // 2 + 60
    draw.line([line_x1, ty + t_size + 8, line_x2, ty + t_size + 8],
              fill=(180, 140, 80), width=1)

    if subtitle:
        sb = draw.textbbox((0, 0), subtitle, font=s_font)
        sx = (W - (sb[2] - sb[0])) // 2
        sy = ty + t_size + 20
        draw.text((sx, sy), subtitle, font=s_font, fill=sub_color)

    static = np.array(img)

    def frame(t: float) -> Frame:
        alpha = 1.0
        if t < fade_in:
            alpha = ease_in_out(t / fade_in)
        elif t > duration - fade_out:
            alpha = ease_in_out((duration - t) / fade_out)
        arr = static.astype(np.float32) * alpha
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame


def make_lower_third(name: str, title: str,
                     W: int = 1280, H: int = 536,
                     appear_at: float = 0.0, duration: float = 3.5,
                     total_clip_dur: float = 10.0) -> FrameFn:
    """
    Netflix lower-third chyron: name + title on semi-transparent bar.
    Returns a frame function that composites over a transparent base.
    """
    n_size = max(20, W // 30)
    t_size = max(14, W // 50)
    n_font = ImageFont.truetype(FONT_SANS_BOLD, n_size)
    t_font = ImageFont.truetype(FONT_SANS, t_size)

    bar_h = n_size + t_size + 28
    bar_y = int(H * 0.72)
    pad_x = int(W * 0.06)

    # Build static RGBA layer
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Semi-transparent dark bar
    d.rectangle([0, bar_y, W, bar_y + bar_h], fill=(6, 6, 10, 210))

    # Amber accent stripe
    d.rectangle([0, bar_y, 3, bar_y + bar_h], fill=(210, 160, 60, 255))

    d.text((pad_x, bar_y + 8), name, font=n_font, fill=(240, 235, 220, 255))
    d.text((pad_x, bar_y + 8 + n_size + 5), title, font=t_font,
           fill=(170, 160, 140, 255))

    static_rgba = np.array(layer).astype(np.float32)

    def frame(t: float) -> np.ndarray:
        """Returns RGBA array to composite over video frame."""
        t_rel = t - appear_at
        alpha = 0.0
        fade = 0.3
        if 0 <= t_rel < fade:
            alpha = ease_out(t_rel / fade)
        elif t_rel < duration - fade:
            alpha = 1.0
        elif t_rel < duration:
            alpha = ease_in((duration - t_rel) / fade)
        arr = static_rgba.copy()
        arr[:, :, 3] *= alpha
        return np.clip(arr, 0, 255).astype(np.uint8)

    return frame


# ══════════════════════════════════════════════════════════════════
# TIMELINE  — sequence clips and build the final FrameFn
# ══════════════════════════════════════════════════════════════════

TRANSITIONS = {
    "cut"       : None,
    "dissolve"  : tr_cross_dissolve,
    "fade_black": tr_fade_black,
    "flash"     : tr_flash_white,
    "burn"      : tr_film_burn,
    "push_left" : tr_push_left,
}


class Clip:
    def __init__(self, fn: FrameFn, duration: float,
                 transition: str = "dissolve",
                 transition_dur: float = 0.8):
        self.fn = fn
        self.duration = duration
        self.transition = transition
        self.transition_dur = transition_dur


class Timeline:
    """
    Add clips sequentially; build() returns a single FrameFn for MoviePy.

    Usage:
        tl = Timeline(W=1280, H=536)
        tl.add_clip(my_fn, duration=10, transition="dissolve")
        tl.add_photo("photo.jpg", duration=6, transition="burn")
        tl.add_quote("Text here", "Author", duration=5)
        final_fn, total_dur = tl.build()
    """

    def __init__(self, W: int = 1280, H: int = 536):
        self.W = W
        self.H = H
        self._clips: List[Clip] = []

    def add_clip(self, fn: FrameFn, duration: float,
                 transition: str = "dissolve",
                 transition_dur: float = 0.8) -> "Timeline":
        self._clips.append(Clip(fn, duration, transition, transition_dur))
        return self

    def add_photo(self, path: str, duration: float = 6.0,
                  transition: str = "dissolve", transition_dur: float = 0.8,
                  zoom_start: float = 1.0, zoom_end: float = 1.10,
                  pan_start: Tuple = (0.5, 0.5), pan_end: Tuple = (0.52, 0.52),
                  grade: str = "netflix") -> "Timeline":
        fn = make_ken_burns(path, duration, self.W, self.H,
                            zoom_start, zoom_end, pan_start, pan_end, grade)
        return self.add_clip(fn, duration, transition, transition_dur)

    def add_quote(self, quote: str, attribution: str = "",
                  duration: float = 5.0,
                  transition: str = "dissolve", transition_dur: float = 0.8,
                  **kwargs) -> "Timeline":
        fn = make_quote_card(quote, attribution, duration,
                             self.W, self.H, **kwargs)
        return self.add_clip(fn, duration, transition, transition_dur)

    def add_title(self, title: str, subtitle: str = "",
                  duration: float = 4.0,
                  transition: str = "fade_black",
                  transition_dur: float = 0.6, **kwargs) -> "Timeline":
        fn = make_title_card(title, subtitle, duration,
                             self.W, self.H, **kwargs)
        return self.add_clip(fn, duration, transition, transition_dur)

    def build(self) -> Tuple[FrameFn, float]:
        """
        Chain all clips with transitions.
        Returns (frame_function, total_duration).
        """
        if not self._clips:
            raise ValueError("Timeline has no clips.")
        if len(self._clips) == 1:
            c = self._clips[0]
            return c.fn, c.duration

        # Merge clips pairwise left-to-right
        merged_fn   = self._clips[0].fn
        merged_dur  = self._clips[0].duration

        for clip in self._clips[1:]:
            tr_name = clip.transition
            tr_dur  = clip.transition_dur
            tr_fn   = TRANSITIONS.get(tr_name)

            if tr_fn is None:  # hard cut
                prev_fn   = merged_fn
                prev_dur  = merged_dur
                next_fn   = clip.fn
                next_dur  = clip.duration
                total     = prev_dur + next_dur

                def _cut(t, _pf=prev_fn, _pd=prev_dur, _nf=next_fn):
                    return _pf(t) if t < _pd else _nf(t - _pd)

                merged_fn  = _cut
                merged_dur = total

            else:
                td = min(tr_dur, merged_dur * 0.4, clip.duration * 0.4)
                merged_fn  = tr_fn(merged_fn, clip.fn, merged_dur,
                                   clip.duration, td)
                merged_dur = merged_dur + clip.duration - td

        return merged_fn, merged_dur


# ══════════════════════════════════════════════════════════════════
# RENDER HELPER
# ══════════════════════════════════════════════════════════════════

def render(frame_fn: FrameFn, duration: float, output: str,
           fps: int = 24, crf: int = 20, preset: str = "fast") -> None:
    from moviepy import VideoClip
    print(f"Rendering {duration:.1f}s → {output}")
    clip = VideoClip(frame_fn, duration=duration)
    clip.write_videofile(
        output, fps=fps, codec="libx264", audio=False,
        preset=preset,
        ffmpeg_params=[
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",       # QuickTime / iOS / macOS compatible
            "-movflags", "+faststart",    # streaming-friendly, fixes moov atom
            "-profile:v", "high",
            "-level", "4.0",
        ],
        logger="bar",
    )
    size_mb = os.path.getsize(output) / 1e6
    print(f"Done  {size_mb:.1f} MB → {output}")
