#!/usr/bin/env python3
"""Pack Indra v0 brain programs into binary and hex files."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from indra_asm import ACTIVATIONS, BrainProgram, IndraError, parse_indra_file

OP_DENSE = 0x01
OP_END = 0xFF
RECORD_SIZE = 16


@dataclass(frozen=True)
class PackedBrain:
    program: bytes
    weights: bytes
    biases: bytes
    manifest: dict


def _pack_i8(values: list[int]) -> bytes:
    return bytes((value + 256) % 256 for value in values)


def _pack_i32_le(values: list[int]) -> bytes:
    return b"".join(struct.pack("<i", value) for value in values)


def _hex_lines(blob: bytes) -> str:
    return "\n".join(f"{byte:02x}" for byte in blob) + ("\n" if blob else "")


def pack_program(program: BrainProgram) -> PackedBrain:
    weight_offsets: dict[str, int] = {}
    bias_offsets: dict[str, int] = {}
    weight_blob = bytearray()
    bias_blob = bytearray()

    for layer in program.layers:
        if layer.weight_label not in weight_offsets:
            weight_offsets[layer.weight_label] = len(weight_blob)
            weight_blob.extend(_pack_i8(program.data[layer.weight_label].values))
        if layer.bias_label not in bias_offsets:
            bias_offsets[layer.bias_label] = len(bias_blob)
            bias_blob.extend(_pack_i32_le(program.data[layer.bias_label].values))

    program_blob = bytearray()
    manifest_layers = []
    for layer in program.layers:
        weight_offset = weight_offsets[layer.weight_label]
        bias_offset = bias_offsets[layer.bias_label]
        activation_id = ACTIVATIONS[layer.activation]

        program_blob.extend(
            struct.pack(
                "<BBBBIIBBBB",
                OP_DENSE,
                layer.input_count,
                layer.output_count,
                activation_id,
                weight_offset,
                bias_offset,
                layer.shift,
                0,
                0,
                0,
            )
        )

        manifest_layers.append(
            {
                "op": "DENSE",
                "input_count": layer.input_count,
                "output_count": layer.output_count,
                "weight_label": layer.weight_label,
                "bias_label": layer.bias_label,
                "activation": layer.activation,
                "activation_id": activation_id,
                "shift": layer.shift,
                "weight_offset": weight_offset,
                "bias_offset": bias_offset,
            }
        )

    program_blob.extend(struct.pack("<BBBBIIBBBB", OP_END, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    manifest = {
        "format": "indra-binary-v0",
        "record_size": RECORD_SIZE,
        "brain": program.name,
        "source": str(program.source_path) if program.source_path else None,
        "program_size": len(program_blob),
        "weights_size": len(weight_blob),
        "biases_size": len(bias_blob),
        "layers": manifest_layers,
        "weight_offsets": weight_offsets,
        "bias_offsets": bias_offsets,
    }

    return PackedBrain(
        program=bytes(program_blob),
        weights=bytes(weight_blob),
        biases=bytes(bias_blob),
        manifest=manifest,
    )


def write_packed_brain(packed: PackedBrain, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{stem}.program.bin").write_bytes(packed.program)
    (output_dir / f"{stem}.weights.bin").write_bytes(packed.weights)
    (output_dir / f"{stem}.biases.bin").write_bytes(packed.biases)

    (output_dir / f"{stem}.program.hex").write_text(_hex_lines(packed.program), encoding="utf-8")
    (output_dir / f"{stem}.weights.hex").write_text(_hex_lines(packed.weights), encoding="utf-8")
    (output_dir / f"{stem}.biases.hex").write_text(_hex_lines(packed.biases), encoding="utf-8")

    (output_dir / f"{stem}.manifest.json").write_text(
        json.dumps(packed.manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pack an Indra v0 brain into binary files.")
    parser.add_argument("source", help="Path to a .indra file.")
    parser.add_argument(
        "--out-dir",
        default="artifacts/indra",
        help="Output directory. Default: artifacts/indra",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        source = Path(args.source)
        program = parse_indra_file(source)
        packed = pack_program(program)
        write_packed_brain(packed, Path(args.out_dir), source.stem)
    except IndraError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Packed brain: {program.name}")
    print(f"Program: {len(packed.program)} bytes")
    print(f"Weights: {len(packed.weights)} bytes")
    print(f"Biases:  {len(packed.biases)} bytes")
    print(f"Output:  {Path(args.out_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
