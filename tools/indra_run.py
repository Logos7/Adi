#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from indra_asm import BrainProgram, IndraAsmError, read_indra_file


INT8_MIN = -128
INT8_MAX = 127


@dataclass(frozen=True)
class RunResult:
    brain_name: str
    input_vector: tuple[int, ...]
    layer_outputs: tuple[tuple[int, ...], ...]

    @property
    def output_vector(self) -> tuple[int, ...]:
        return self.layer_outputs[-1] if self.layer_outputs else ()


def clamp_int8(value: int) -> int:
    if value < INT8_MIN:
        return INT8_MIN
    if value > INT8_MAX:
        return INT8_MAX
    return value


def apply_activation(value: int, activation: str) -> int:
    activation = activation.upper()

    if activation == "NONE":
        return clamp_int8(value)
    if activation == "CLAMP":
        return clamp_int8(value)
    if activation == "RELU":
        return clamp_int8(max(0, value))
    if activation == "SIGN":
        return 127 if value >= 0 else -127

    raise IndraAsmError(f"unsupported activation at runtime: {activation}")


def validate_input_vector(values: Sequence[int]) -> tuple[int, ...]:
    result = tuple(int(value) for value in values)
    for index, value in enumerate(result):
        if value < INT8_MIN or value > INT8_MAX:
            raise IndraAsmError(f"input[{index}] outside int8 range [{INT8_MIN}, {INT8_MAX}]: {value}")
    return result


def run_dense_layer(
    inputs: Sequence[int],
    weights: Sequence[int],
    biases: Sequence[int],
    input_count: int,
    output_count: int,
    activation: str,
) -> tuple[int, ...]:
    if len(inputs) != input_count:
        raise IndraAsmError(f"layer expected {input_count} inputs, got {len(inputs)}")
    if len(weights) != input_count * output_count:
        raise IndraAsmError(
            f"layer expected {input_count * output_count} weights, got {len(weights)}"
        )
    if len(biases) != output_count:
        raise IndraAsmError(f"layer expected {output_count} biases, got {len(biases)}")

    outputs: list[int] = []
    for output_index in range(output_count):
        acc = int(biases[output_index])
        weight_row = output_index * input_count
        for input_index in range(input_count):
            acc += int(inputs[input_index]) * int(weights[weight_row + input_index])
        outputs.append(apply_activation(acc, activation))

    return tuple(outputs)


def run_program(program: BrainProgram, input_vector: Sequence[int]) -> RunResult:
    current = validate_input_vector(input_vector)

    if not program.layers:
        raise IndraAsmError("brain has no layers")

    first_layer = program.layers[0]
    if len(current) != first_layer.input_count:
        raise IndraAsmError(
            f"brain '{program.name}' expects {first_layer.input_count} inputs, got {len(current)}"
        )

    layer_outputs: list[tuple[int, ...]] = []

    for layer in program.layers:
        weight_block = program.data[layer.weight_label]
        bias_block = program.data[layer.bias_label]
        current = run_dense_layer(
            current,
            weight_block.values,
            bias_block.values,
            layer.input_count,
            layer.output_count,
            layer.activation,
        )
        layer_outputs.append(current)

    return RunResult(program.name, tuple(input_vector), tuple(layer_outputs))


def format_result(result: RunResult, show_layers: bool = False) -> str:
    lines = [f"Brain: {result.brain_name}"]
    lines.append("Input:  " + " ".join(str(value) for value in result.input_vector))

    if show_layers:
        for index, values in enumerate(result.layer_outputs):
            lines.append(f"Layer {index}: " + " ".join(str(value) for value in values))

    lines.append("Output: " + " ".join(str(value) for value in result.output_vector))
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an Indra v0 brain source file in software.")
    parser.add_argument("source", type=Path, help="Indra brain source file.")
    parser.add_argument(
        "--input",
        nargs="+",
        type=int,
        required=True,
        help="Input vector values as signed int8 integers.",
    )
    parser.add_argument(
        "--show-layers",
        action="store_true",
        help="Print intermediate layer outputs.",
    )
    args = parser.parse_args(argv)

    try:
        program = read_indra_file(args.source)
        result = run_program(program, args.input)
    except IndraAsmError as ex:
        print(f"ERROR: {ex}")
        return 1

    print(format_result(result, show_layers=args.show_layers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
