#!/usr/bin/env python3
"""
Indra v0 software executor.

Reference implementation for dense integer inference.

Numeric convention:
- int8 activations and weights are normalized fixed-point values.
- real = raw / 128.
- int8 * int8 accumulates into int32 with scale 1 / 16384.
- default layer SHIFT is 7.
"""

from __future__ import annotations

import argparse
from typing import Iterable

try:
    from .indra_asm import Assembly, IndraError, parse_file
except ImportError:
    from indra_asm import Assembly, IndraError, parse_file

def saturate_i8(value: int) -> int:
    if value < -128:
        return -128
    if value > 127:
        return 127
    return value


def arithmetic_shift_right(value: int, shift: int) -> int:
    if shift <= 0:
        return value
    return value >> shift


def activate(value: int, activation: str) -> int:
    activation = activation.upper()

    if activation == "NONE":
        return saturate_i8(value)
    if activation == "RELU":
        return saturate_i8(max(0, value))
    if activation == "CLAMP":
        return saturate_i8(value)
    if activation == "SIGN":
        return 127 if value >= 0 else -127

    raise IndraError(f"Unknown activation: {activation}")


def run(assembly: Assembly, inputs: list[int]) -> tuple[list[int], list[list[int]]]:
    if not assembly.brain.layers:
        raise IndraError("Brain has no layers")

    expected_inputs = assembly.brain.layers[0].input_count
    if len(inputs) != expected_inputs:
        raise IndraError(f"Expected {expected_inputs} input values, got {len(inputs)}")

    for index, value in enumerate(inputs):
        if value < -128 or value > 127:
            raise IndraError(f"Input {index} out of int8 range: {value}")

    current = list(inputs)
    layer_outputs: list[list[int]] = []

    for layer in assembly.brain.layers:
        weights = assembly.data.i8[layer.weight_label]
        biases = assembly.data.i32[layer.bias_label]
        output: list[int] = []

        for output_index in range(layer.output_count):
            acc = biases[output_index]
            row_base = output_index * layer.input_count

            for input_index in range(layer.input_count):
                acc += current[input_index] * weights[row_base + input_index]

            scaled = arithmetic_shift_right(acc, layer.shift)
            output.append(activate(scaled, layer.activation))

        current = output
        layer_outputs.append(output)

    return current, layer_outputs


def _parse_inputs(values: Iterable[str]) -> list[int]:
    result: list[int] = []
    for raw in values:
        value = int(raw, 0)
        if value < -128 or value > 127:
            raise argparse.ArgumentTypeError(f"Input value out of int8 range: {value}")
        result.append(value)
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an Indra v0 brain in software.")
    parser.add_argument("source", help="Path to .indra source file.")
    parser.add_argument("--input", nargs="+", required=True, help="Input int8 vector.")
    parser.add_argument("--show-layers", action="store_true", help="Print per-layer outputs.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        assembly = parse_file(args.source)
        inputs = _parse_inputs(args.input)
        outputs, layer_outputs = run(assembly, inputs)
    except (IndraError, ValueError, argparse.ArgumentTypeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Input: ", " ".join(str(value) for value in inputs))

    if args.show_layers:
        for index, layer_output in enumerate(layer_outputs):
            print(f"Layer {index}:", " ".join(str(value) for value in layer_output))

    print("Output:", " ".join(str(value) for value in outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
