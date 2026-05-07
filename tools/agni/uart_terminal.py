#!/usr/bin/env python3
"""
Adi UART Terminal

Single-window text UART terminal and uploader for Agni.

Typical usage:

    py tools/agni/uart_terminal.py

    py tools/agni/uart_terminal.py COM9 examples/agni/basics/blink.sutra

CLI mode:

    py tools/agni/uart_terminal.py COM9 examples/agni/basics/blink.sutra --no-gui
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SUTRA_ROOT = os.path.join(ROOT, "sutra")

for path in (SUTRA_ROOT, ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from terminal_args import add_terminal_args
from uart_terminal_core import run_cli, run_terminal_gui


def main() -> None:
    parser = argparse.ArgumentParser()
    add_terminal_args(parser)
    args = parser.parse_args()

    if args.no_gui:
        if not args.port:
            raise SystemExit("A port is required in --no-gui mode.")
        run_cli(args.port, args.baud, args.upload, args.boot_timeout, args.ack_timeout)
        return

    run_terminal_gui(args.port, args.baud, args.upload, args.boot_timeout, args.ack_timeout)


if __name__ == "__main__":
    main()
