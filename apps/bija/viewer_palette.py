from __future__ import annotations

import colorsys

from adi_frames import MAGIC_ADI1

PALETTES: list[tuple[str, str]] = [
    ("classic", "Classic"),
    ("inferno", "Inferno"),
    ("fire", "Fire"),
    ("ocean", "Ocean"),
    ("viridis", "Viridis"),
    ("neon", "Neon"),
    ("nebula", "Nebula"),
    ("gold", "Gold"),
]

PALETTE_LABELS = [label for _key, label in PALETTES]
PALETTE_KEYS = [key for key, _label in PALETTES]
PALETTE_KEY_BY_LABEL = {label: key for key, label in PALETTES}
PALETTE_LABEL_BY_KEY = {key: label for key, label in PALETTES}
DEFAULT_PALETTE = "classic"


def normalize_palette(value: str | None) -> str:
    if not value:
        return DEFAULT_PALETTE
    text = value.strip()
    if text in PALETTE_KEYS:
        return text
    lowered = text.lower()
    for key, label in PALETTES:
        if lowered == label.lower():
            return key
    return DEFAULT_PALETTE


def palette_label(value: str | None) -> str:
    return PALETTE_LABEL_BY_KEY.get(normalize_palette(value), PALETTE_LABEL_BY_KEY[DEFAULT_PALETTE])


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def gradient_color(stops: list[tuple[float, tuple[int, int, int]]], t: float) -> tuple[int, int, int]:
    t = clamp01(t)
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        left_t, left_rgb = stops[i - 1]
        right_t, right_rgb = stops[i]
        if t <= right_t:
            local = 0.0 if right_t == left_t else (t - left_t) / (right_t - left_t)
            return (
                lerp(left_rgb[0], right_rgb[0], local),
                lerp(left_rgb[1], right_rgb[1], local),
                lerp(left_rgb[2], right_rgb[2], local),
            )
    return stops[-1][1]


def classic_palette(v: int, max_iter: int) -> tuple[int, int, int]:
    if v >= max_iter:
        return 0, 0, 0
    if v <= 0:
        return 7, 19, 61
    t = clamp01(v / max_iter)
    hue = 0.68 - 0.68 * (t ** 0.82)
    sat = 0.88
    val = 0.20 + 0.80 * (t ** 0.35)
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return int(r * 255), int(g * 255), int(b * 255)


def palette_rgb(v: int, max_iter: int, palette: str) -> tuple[int, int, int]:
    if v >= max_iter:
        return 0, 0, 0
    t = 0.0 if max_iter <= 1 else clamp01(v / max_iter)
    t_soft = t ** 0.72
    t_hot = t ** 0.45
    key = normalize_palette(palette)

    if key == "classic":
        return classic_palette(v, max_iter)
    if key == "inferno":
        return gradient_color([
            (0.00, (0, 0, 4)),
            (0.18, (38, 12, 72)),
            (0.36, (113, 31, 93)),
            (0.58, (201, 65, 55)),
            (0.80, (249, 142, 8)),
            (1.00, (252, 255, 164)),
        ], t_soft)
    if key == "fire":
        return gradient_color([
            (0.00, (5, 0, 0)),
            (0.18, (80, 0, 0)),
            (0.42, (190, 28, 0)),
            (0.68, (255, 122, 16)),
            (0.88, (255, 220, 80)),
            (1.00, (255, 255, 230)),
        ], t_hot)
    if key == "ocean":
        return gradient_color([
            (0.00, (0, 6, 30)),
            (0.22, (0, 42, 92)),
            (0.46, (0, 112, 150)),
            (0.70, (0, 190, 185)),
            (0.90, (142, 238, 215)),
            (1.00, (235, 255, 247)),
        ], t_soft)
    if key == "viridis":
        return gradient_color([
            (0.00, (68, 1, 84)),
            (0.24, (59, 82, 139)),
            (0.48, (33, 145, 140)),
            (0.72, (94, 201, 98)),
            (1.00, (253, 231, 37)),
        ], t_soft)
    if key == "neon":
        return gradient_color([
            (0.00, (3, 0, 35)),
            (0.20, (30, 0, 130)),
            (0.42, (0, 96, 255)),
            (0.62, (0, 238, 255)),
            (0.82, (90, 255, 90)),
            (1.00, (255, 255, 255)),
        ], t_soft)
    if key == "nebula":
        return gradient_color([
            (0.00, (4, 0, 18)),
            (0.20, (28, 0, 70)),
            (0.42, (92, 24, 140)),
            (0.62, (190, 42, 150)),
            (0.82, (255, 126, 80)),
            (1.00, (255, 235, 170)),
        ], t_soft)
    if key == "gold":
        return gradient_color([
            (0.00, (18, 8, 0)),
            (0.22, (70, 38, 0)),
            (0.44, (150, 95, 18)),
            (0.66, (225, 165, 45)),
            (0.86, (255, 220, 115)),
            (1.00, (255, 252, 220)),
        ], t_soft)
    return classic_palette(v, max_iter)


def frame_pixel_rgb(v: int, max_iter: int, palette: str, frame_kind: bytes) -> tuple[int, int, int]:
    if frame_kind == MAGIC_ADI1:
        return (255, 255, 255) if v else (0, 0, 0)
    return palette_rgb(v, max_iter, palette)
