#!/usr/bin/env python3
"""Software executor for Indra v0 brain programs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from indra_asm import BrainProgram, DenseLayer, IndraError, parse_indra_file


def clamp_i8(value: int) -> int:
    return max(-128, min(127, value))


def arithmetic_shift(value: int, shift: int) -> int:
    if shift <= 0:
        return value
    return value >> shift


def apply_activation(value: int, activation: str) -> int:
    if activation == "NONE":
        return clamp_i8(value)
    if activation == "RELU":
        return clamp_i8(max(0, value))
    if activation == "CLAMP":
        return clamp_i8(value)
    if activation == "SIGN":
        return 127 if value >= 0 else -127
    raise IndraError(f"Unsupported activation '{activation}'.")


@dataclass(frozen=True)
class RunResult:
    output: list[int]
    layer_outputs: list[list[int]]


def run_dense_layer(program: BrainProgram, layer: DenseLayer, inputs: list[int]) -> list[int]:
    if len(inputs) != layer.input_count:
        raise IndraError(
            f"Layer expects {layer.input_count} inputs, got {len(inputs)}."
        )

    weights = program.data[layer.weight_label].values
    biases = program.data[layer.bias_label].values
    outputs: list[int] = []

    for out_index in range(layer.output_count):
        acc = biases[out_index]
        base = out_index * layer.input_count
        for in_index, input_value in enumerate(inputs):
            acc += input_value * weights[base + in_index]
        acc = arithmetic_shift(acc, layer.shift)
        outputs.append(apply_activation(acc, layer.activation))

    return outputs


def run_program(program: BrainProgram, inputs: list[int]) -> RunResult:
    if len(inputs) != program.layers[0].input_count:
        raise IndraError(
            f"Brain '{program.name}' expects {program.layers[0].input_count} inputs, got {len(inputs)}."
        )
    for index, value in enumerate(inputs):
        if not -128 <= value <= 127:
            raise IndraError(f"Input {index} value {value} is outside -128..127.")

    current = list(inputs)
    layer_outputs: list[list[int]] = []
    for layer in program.layers:
        current = run_dense_layer(program, layer, current)
        layer_outputs.append(current)
    return RunResult(output=current, layer_outputs=layer_outputs)


def _parse_input_values(values: list[str]) -> list[int]:
    try:
        return [int(value, 0) for value in values]
    except ValueError as exc:
        raise IndraError("All --input values must be integers.") from exc


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an Indra v0 brain program in software.")
    parser.add_argument("source", help="Path to a .indra file.")
    parser.add_argument("--input", nargs="+", required=True, help="Input vector as int8 values.")
    parser.add_argument("--show-layers", action="store_true", help="Print every layer output.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        program = parse_indra_file(Path(args.source))
        inputs = _parse_input_values(args.input)
        result = run_program(program, inputs)
    except IndraError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Input:  " + " ".join(str(value) for value in inputs))
    if args.show_layers:
        for index, values in enumerate(result.layer_outputs):
            print(f"Layer {index}: " + " ".join(str(value) for value in values))
    print("Output: " + " ".join(str(value) for value in result.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
