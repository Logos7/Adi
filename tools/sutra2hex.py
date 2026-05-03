#!/usr/bin/env python3
"""sutra2hex — convert Sutra source to code/data hex files."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "sutra"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from sutra import CONSTANT_SUMMARY, INSTRUCTION_SUMMARY, assemble_image
from sutra_expand import IncludeError, expand_file


def write_hex(path: str, words: list[int]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for w in words:
            f.write(f"{w & 0xFFFFFFFF:08x}\n")


def print_instructions() -> None:
    print("Sutra / Brahma-Bija instructions:")
    for item in INSTRUCTION_SUMMARY:
        print(f"  {item}")

    print("\nConstants:")
    for item in CONSTANT_SUMMARY:
        print(f"  {item}")

    print("\nSutra v1.5 data directives:")
    print("  .data / .code")
    print("  .org address")
    print("  label:")
    print("  .word a, b, c")
    print("  .q7_25 0.0, 1.0, -0.5")
    print("  .sin_lut 256")
    print("  .zero count")
    print("  .include \"path/to/file.sutra\"")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", help="input .sutra")
    parser.add_argument("output", nargs="?", help="output code .hex")
    parser.add_argument("--data-output", help="optional output data .hex")
    parser.add_argument("-I", "--include-path", action="append", default=[], help="additional include search path")
    parser.add_argument("--list-instructions", action="store_true")
    args = parser.parse_args()

    if args.list_instructions:
        print_instructions()
        return

    if not args.input or not args.output:
        parser.print_help()
        raise SystemExit(1)

    try:
        source = expand_file(args.input, args.include_path or None)
    except IncludeError as e:
        raise SystemExit(f"Sutra include error: {e}") from e

    image = assemble_image(source)

    write_hex(args.output, image.code_words)
    print(f"Wrote {len(image.code_words)} code words to {args.output}")

    if args.data_output:
        write_hex(args.data_output, image.data_words)
        print(f"Wrote {len(image.data_words)} data words to {args.data_output}")


if __name__ == "__main__":
    main()
