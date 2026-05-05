from __future__ import annotations

from dataclasses import dataclass

from adi_frames import AdiFrame
from viewer_palette import frame_pixel_rgb, rgb_hex


@dataclass(frozen=True)
class RenderedFrame:
    photo_rows: str
    display_width: int
    display_height: int
    rgb: bytes


def render_frame(frame: AdiFrame, max_iter: int, scale: int, palette: str) -> RenderedFrame:
    display_width = frame.width * scale
    display_height = frame.height * scale
    rgb_bytes = bytearray(display_width * display_height * 3)
    photo_rows: list[str] = []

    for y in range(frame.height):
        start = y * frame.width
        row_hex: list[str] = []
        row_rgb: list[tuple[int, int, int]] = []
        for x in range(frame.width):
            rgb = frame_pixel_rgb(frame.pixels[start + x], max_iter, palette, frame.kind)
            row_hex.append(rgb_hex(rgb))
            row_rgb.append(rgb)
        photo_rows.append("{" + " ".join(row_hex) + "}")

        for sy in range(scale):
            dest = ((y * scale + sy) * display_width) * 3
            for r, g, b in row_rgb:
                for _ in range(scale):
                    rgb_bytes[dest] = r
                    rgb_bytes[dest + 1] = g
                    rgb_bytes[dest + 2] = b
                    dest += 3

    return RenderedFrame(
        photo_rows=" ".join(photo_rows),
        display_width=display_width,
        display_height=display_height,
        rgb=bytes(rgb_bytes),
    )
