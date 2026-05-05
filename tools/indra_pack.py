#!/usr/bin/env python3
"""
Indra v0 binary packer.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Iterable

try:
    from .indra_asm import ACTIVATIONS, Assembly, parse_file
except ImportError:
    from indra_asm import ACTIVATIONS, Assembly, parse_file

OP_DENSE = 0x01
OP_END = 0xFF


def _u16(value: int) -> bytes:
    return struct.pack("<H", value)


def _i32(value: int) -> bytes:
    return struct.pack("<i", value)


def _build_data_offsets(assembly: Assembly) -> tuple[dict[str, int], dict[str, int], bytes, bytes]:
    weight_offsets: dict[str, int] = {}
    bias_offsets: dict[str, int] = {}
    weights = bytearray()
    biases = bytearray()

    for layer in assembly.brain.layers:
        if layer.weight_label not in weight_offsets:
            weight_offsets[layer.weight_label] = len(weights)
            for value in assembly.data.i8[layer.weight_label]:
                weights.append(value & 0xFF)

        if layer.bias_label not in bias_offsets:
            bias_offsets[layer.bias_label] = len(biases) // 4
            for value in assembly.data.i32[layer.bias_label]:
                biases.extend(_i32(value))

    return weight_offsets, bias_offsets, bytes(weights), bytes(biases)


def pack_program(assembly: Assembly, weight_offsets: dict[str, int], bias_offsets: dict[str, int]) -> bytes:
    program = bytearray()

    for layer in assembly.brain.layers:
        program.append(OP_DENSE)
        program.append(layer.input_count & 0xFF)
        program.append(layer.output_count & 0xFF)
        program.append(ACTIVATIONS[layer.activation] & 0xFF)
        program.append(layer.shift & 0xFF)
        program.append(0)
        program.extend(_u16(weight_offsets[layer.weight_label]))
        program.extend(_u16(bias_offsets[layer.bias_label]))
        program.extend(_u16(0))

    program.append(OP_END)
    return bytes(program)


def _write_hex(path: Path, data: bytes) -> None:
    path.write_text("\n".join(f"{byte:02x}" for byte in data) + "\n", encoding="utf-8")


def pack_to_directory(source_path: str | Path, output_dir: str | Path = "artifacts/indra") -> dict[str, str]:
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    assembly = parse_file(source_path)
    weight_offsets, bias_offsets, weights, biases = _build_data_offsets(assembly)
    program = pack_program(assembly, weight_offsets, bias_offsets)

    stem = assembly.brain.name

    paths = {
        "program_bin": output_dir / f"{stem}.program.bin",
        "weights_bin": output_dir / f"{stem}.weights.bin",
        "biases_bin": output_dir / f"{stem}.biases.bin",
        "program_hex": output_dir / f"{stem}.program.hex",
        "weights_hex": output_dir / f"{stem}.weights.hex",
        "biases_hex": output_dir / f"{stem}.biases.hex",
        "manifest": output_dir / f"{stem}.manifest.json",
    }

    paths["program_bin"].write_bytes(program)
    paths["weights_bin"].write_bytes(weights)
    paths["biases_bin"].write_bytes(biases)

    _write_hex(paths["program_hex"], program)
    _write_hex(paths["weights_hex"], weights)
    _write_hex(paths["biases_hex"], biases)

    manifest = {
        "brain": assembly.brain.name,
        "source": str(source_path),
        "format": "indra-binary-v0",
        "numeric": {
            "int8_scale": "1/128",
            "accumulator_scale": "1/16384",
            "default_shift": 7,
        },
        "files": {key: str(value) for key, value in paths.items() if key != "manifest"},
        "sizes": {
            "program_bytes": len(program),
            "weights_bytes": len(weights),
            "biases_bytes": len(biases),
        },
        "weight_offsets_bytes": weight_offsets,
        "bias_offsets_i32": bias_offsets,
    }

    paths["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pack an Indra v0 brain file.")
    parser.add_argument("source", help="Path to .indra source file.")
    parser.add_argument("--out", default="artifacts/indra", help="Output directory.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    paths = pack_to_directory(args.source, args.out)
    for key, path in paths.items():
        print(f"{key}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
