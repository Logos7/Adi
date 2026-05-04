from __future__ import annotations

import os

DEFAULT_SOURCE = os.path.join("examples", "bija", "basics", "echo_rx.sutra")


def add_terminal_args(parser) -> None:
    parser.add_argument("port", nargs="?", help="COM port, for example COM9.")
    parser.add_argument("upload", nargs="?", help="Optional Sutra program to upload before opening the terminal.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--no-gui", action="store_true", help="Run as a text terminal in the console.")
    parser.add_argument("--boot-timeout", type=float, default=30.0)
    parser.add_argument("--ack-timeout", type=float, default=12.0)
