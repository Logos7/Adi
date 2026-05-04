#!/usr/bin/env python3
from __future__ import annotations

import argparse

from uart_viewer_core import add_viewer_args, build_defaults, run_viewer_gui


def main() -> None:
    parser = argparse.ArgumentParser()
    add_viewer_args(parser)
    args = parser.parse_args()
    if args.text:
        raise SystemExit("Text mode was moved to apps/bija/uart_terminal.py.")
    run_viewer_gui(build_defaults(args))


if __name__ == "__main__":
    main()
