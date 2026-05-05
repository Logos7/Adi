from __future__ import annotations

import os
from dataclasses import dataclass

import app_paths
from viewer_palette import DEFAULT_PALETTE, PALETTE_KEYS, normalize_palette

DEFAULT_SOURCE = os.path.join("examples", "bija", "fractals", "julia.sutra")


@dataclass(frozen=True)
class ViewerDefaults:
    port: str | None
    baud: int
    source: str
    upload: str | None
    width: int
    height: int
    max_iter: int
    scale: int
    palette: str
    boot_timeout: float
    ack_timeout: float


def parse_int(value: str, name: str, min_value: int, max_value: int) -> int:
    try:
        x = int(value.strip())
    except Exception:
        raise ValueError(f"{name} must be an integer.")
    if x < min_value or x > max_value:
        raise ValueError(f"{name} must be in range {min_value}..{max_value}.")
    return x


def optional_byte(value: str, name: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    return parse_int(text, name, 1, 255)


def build_defaults(args) -> ViewerDefaults:
    if not 1 <= args.width <= 255:
        raise SystemExit("width must be in range 1..255.")
    if not 1 <= args.height <= 255:
        raise SystemExit("height must be in range 1..255.")
    if not 1 <= args.max_iter <= 255:
        raise SystemExit("max-iter must be in range 1..255.")
    if not 1 <= args.scale <= 32:
        raise SystemExit("scale must be in range 1..32.")

    upload = app_paths.as_repo_path(app_paths.resolve_repo_path(args.upload, DEFAULT_SOURCE)) if args.upload else None
    return ViewerDefaults(
        port=args.port,
        baud=args.baud,
        source=DEFAULT_SOURCE,
        upload=upload,
        width=args.width,
        height=args.height,
        max_iter=args.max_iter,
        scale=args.scale,
        palette=normalize_palette(args.palette),
        boot_timeout=args.boot_timeout,
        ack_timeout=args.ack_timeout,
    )


def add_viewer_args(parser) -> None:
    parser.add_argument("port", nargs="?", help="COM port, for example COM9. Without a port, the GUI opens disconnected.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--upload", help="Sutra program to upload before receiving ADI0 / ADI1 frames.")
    parser.add_argument("--width", type=int, default=64, help="Frame width, 1..255.")
    parser.add_argument("--height", type=int, default=64, help="Frame height, 1..255.")
    parser.add_argument("--max-iter", type=int, default=64, help="Iteration value treated as interior color, 1..255.")
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--palette", choices=PALETTE_KEYS, default=DEFAULT_PALETTE)
    parser.add_argument("--text", action="store_true", help="Deprecated. Use apps/bija/uart_terminal.py for text UART.")
    parser.add_argument("--boot-timeout", type=float, default=30.0)
    parser.add_argument("--ack-timeout", type=float, default=12.0)
