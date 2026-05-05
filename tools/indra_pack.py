#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from indra_asm import ACTIVATIONS, BrainProgram, DenseLayer, IndraAsmError, read_indra_file

OP_DENSE = 1
OP_END = 255
RECORD_SIZE = 16


@dataclass(frozen=True)
class PackedBrain:
    program_bin: bytes
    weights_bin: bytes
    biases_bin: bytes
    manifest: dict[str, object]


def pack_i8(values: Iterable[int]) -> bytes:
    return bytes((value & 0xFF for value in values))


def pack_i32(values: Iterable[int]) -> bytes:
    return b"".join(struct.pack("<i", value) for value in values)


def build_data_images(program: BrainProgram) -> tuple[bytes, bytes, dict[str, int], dict[str, int]]:
    weights = bytearray()
    biases = bytearray()
    weight_offsets: dict[str, int] = {}
    bias_offsets: dict[str, int] = {}

    for layer in program.layers:
        if layer.weight_label not in weight_offsets:
            block = program.data[layer.weight_label]
            weight_offsets[layer.weight_label] = len(weights)
            weights.extend(pack_i8(block.values))
        if layer.bias_label not in bias_offsets:
            block = program.data[layer.bias_label]
            bias_offsets[layer.bias_label] = len(biases)
            biases.extend(pack_i32(block.values))

    return bytes(weights), bytes(biases), weight_offsets, bias_offsets


def pack_dense_record(layer: DenseLayer, weight_offset: int, bias_offset: int) -> bytes:
    if layer.input_count > 255 or layer.output_count > 255:
        raise IndraAsmError(f"line {layer.line_no}: layer dimensions must fit in one byte")
    return struct.pack(
        "<BBBBIII",
        OP_DENSE,
        ACTIVATIONS[layer.activation],
        layer.input_count,
        layer.output_count,
        weight_offset,
        bias_offset,
        0,
    )


def pack_end_record() -> bytes:
    return struct.pack("<BBBBIII", OP_END, 0, 0, 0, 0, 0, 0)


def pack_program(program: BrainProgram) -> PackedBrain:
    weights_bin, biases_bin, weight_offsets, bias_offsets = build_data_images(program)
    program_bytes = bytearray()
    manifest_layers: list[dict[str, object]] = []

    for index, layer in enumerate(program.layers):
        weight_offset = weight_offsets[layer.weight_label]
        bias_offset = bias_offsets[layer.bias_label]
        program_bytes.extend(pack_dense_record(layer, weight_offset, bias_offset))
        manifest_layers.append(
            {
                "index": index,
                "op": "DENSE",
                "input_count": layer.input_count,
                "output_count": layer.output_count,
                "weight_label": layer.weight_label,
                "bias_label": layer.bias_label,
                "weight_offset": weight_offset,
                "bias_offset": bias_offset,
                "activation": layer.activation,
                "activation_id": ACTIVATIONS[layer.activation],
            }
        )

    program_bytes.extend(pack_end_record())

    manifest: dict[str, object] = {
        "format": "indra-v0",
        "record_size": RECORD_SIZE,
        "brain": program.name,
        "layers": manifest_layers,
        "program_bytes": len(program_bytes),
        "weights_bytes": len(weights_bin),
        "biases_bytes": len(biases_bin),
        "opcodes": {
            "DENSE": OP_DENSE,
            "END": OP_END,
        },
        "activations": ACTIVATIONS,
    }

    return PackedBrain(bytes(program_bytes), weights_bin, biases_bin, manifest)


def bytes_to_hex_lines(data: bytes, width: int = 16) -> str:
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        lines.append(" ".join(f"{byte:02x}" for byte in chunk))
    return "\n".join(lines) + ("\n" if lines else "")


def write_packed(out_dir: Path, source: Path, packed: PackedBrain) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = source.stem
    paths = {
        "program_bin": out_dir / f"{stem}.program.bin",
        "weights_bin": out_dir / f"{stem}.weights.bin",
        "biases_bin": out_dir / f"{stem}.biases.bin",
        "program_hex": out_dir / f"{stem}.program.hex",
        "weights_hex": out_dir / f"{stem}.weights.hex",
        "biases_hex": out_dir / f"{stem}.biases.hex",
        "manifest": out_dir / f"{stem}.manifest.json",
    }
    paths["program_bin"].write_bytes(packed.program_bin)
    paths["weights_bin"].write_bytes(packed.weights_bin)
    paths["biases_bin"].write_bytes(packed.biases_bin)
    paths["program_hex"].write_text(bytes_to_hex_lines(packed.program_bin), encoding="utf-8")
    paths["weights_hex"].write_text(bytes_to_hex_lines(packed.weights_bin), encoding="utf-8")
    paths["biases_hex"].write_text(bytes_to_hex_lines(packed.biases_bin), encoding="utf-8")
    paths["manifest"].write_text(json.dumps(packed.manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pack an Indra v0 brain source file into binary images.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/indra"))
    args = parser.parse_args(argv)

    try:
        program = read_indra_file(args.source)
        packed = pack_program(program)
        paths = write_packed(args.out_dir, args.source, packed)
    except IndraAsmError as ex:
        print(f"ERROR: {ex}")
        return 1

    print(f"Brain: {program.name}")
    print(f"Program: {paths['program_bin']}")
    print(f"Weights: {paths['weights_bin']}")
    print(f"Biases: {paths['biases_bin']}")
    print(f"Manifest: {paths['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
