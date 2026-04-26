#!/usr/bin/env python3
"""
sutra2hex — konwertuj plik .sutra do .hex (jeden 32-bit hex per linia, dla $readmemh).

Użycie:
    python tools/sutra2hex.py examples/05_fractals/mandelbrot_uart.sutra cores/bija/rtl/src/program.hex
    python tools/sutra2hex.py --list-instructions
"""

import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "sutra"))

from sutra import assemble, flatten_program, INSTRUCTION_SUMMARY, CONSTANT_SUMMARY


USAGE = """Użycie:
  sutra2hex.py <input.sutra> <output.hex>
  sutra2hex.py --list-instructions
  sutra2hex.py --help
"""


def print_instructions():
    print("Instrukcje Sutra / Brahma-Bija:")
    for item in INSTRUCTION_SUMMARY:
        print(f"  {item}")
    print("\nStałe 32-bit:")
    for item in CONSTANT_SUMMARY:
        print(f"  {item}")
    print("\nPredykacja:")
    print("  (B0)  INSTR ...     wykonaj jeśli B0=1")
    print("  (!B0) INSTR ...     wykonaj jeśli B0=0")
    print("  B0..B7 są dostępne dla predykacji dodatniej; (!B7) jest zarezerwowane przez kod ALWAYS.")


def main():
    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        print(USAGE)
        return

    if len(sys.argv) == 2 and sys.argv[1] == "--list-instructions":
        print_instructions()
        return

    if len(sys.argv) != 3:
        print(USAGE)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, encoding="utf-8") as f:
        source = f.read()

    lines = assemble(source)
    words = flatten_program(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        for w in words:
            f.write(f"{w:08x}\n")

    print(f"Zapisano {len(words)} słów do {output_path}")
    print(f"Liczba instrukcji: {len(lines)}")


if __name__ == "__main__":
    main()
