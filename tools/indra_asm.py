#!/usr/bin/env python3
"""
Indra v0 brain assembler/parser.

Numeric convention:
- int8 activations and weights are normalized fixed-point values.
- real = raw / 128.
- int8 * int8 accumulates into int32 with accumulator scale 1 / 16384.
- default layer SHIFT is 7.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


DEFAULT_SHIFT = 7

ACTIVATIONS: dict[str, int] = {
    "NONE": 0,
    "RELU": 1,
    "CLAMP": 2,
    "SIGN": 3,
}


class IndraError(ValueError):
    pass


@dataclass(frozen=True)
class DenseLayer:
    input_count: int
    output_count: int
    weight_label: str
    bias_label: str
    activation: str
    shift: int = DEFAULT_SHIFT

    @property
    def expected_weight_count(self) -> int:
        return self.input_count * self.output_count

    @property
    def expected_bias_count(self) -> int:
        return self.output_count


@dataclass(frozen=True)
class Brain:
    name: str
    layers: tuple[DenseLayer, ...]


@dataclass(frozen=True)
class DataSection:
    i8: dict[str, tuple[int, ...]]
    i32: dict[str, tuple[int, ...]]


@dataclass(frozen=True)
class Assembly:
    brain: Brain
    data: DataSection


_DENSE_RE = re.compile(
    r"^DENSE\s+"
    r"(?P<input>\d+)\s+"
    r"(?P<output>\d+)\s+"
    r"W=(?P<weight>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"B=(?P<bias>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"ACT=(?P<activation>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+SHIFT=(?P<shift>-?\d+))?"
    r"$"
)

_LABEL_RE = re.compile(r"^(?P<label>[A-Za-z_][A-Za-z0-9_]*):$")


def _strip_comment(line: str) -> str:
    for marker in (";", "#"):
        if marker in line:
            line = line.split(marker, 1)[0]
    return line.strip()


def _parse_int(value: str, line_no: int) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise IndraError(f"Line {line_no}: invalid integer: {value!r}") from exc


def _parse_values(text: str, line_no: int, min_value: int, max_value: int) -> tuple[int, ...]:
    if not text.strip():
        raise IndraError(f"Line {line_no}: expected at least one value")

    values: list[int] = []
    for raw in text.split(","):
        value = _parse_int(raw.strip(), line_no)
        if value < min_value or value > max_value:
            raise IndraError(
                f"Line {line_no}: value {value} out of range {min_value}..{max_value}"
            )
        values.append(value)
    return tuple(values)


def parse_text(source: str) -> Assembly:
    brain_name: str | None = None
    layers: list[DenseLayer] = []

    i8_data: dict[str, list[int]] = {}
    i32_data: dict[str, list[int]] = {}

    current_label: str | None = None
    current_kind: str | None = None
    in_data = False
    ended = False

    for line_no, original_line in enumerate(source.splitlines(), start=1):
        line = _strip_comment(original_line)
        if not line:
            continue

        if line == ".data":
            in_data = True
            current_label = None
            current_kind = None
            continue

        label_match = _LABEL_RE.match(line)
        if label_match:
            label = label_match.group("label")
            if in_data:
                current_label = label
                current_kind = None
            else:
                if brain_name is not None:
                    raise IndraError(f"Line {line_no}: multiple brain labels are not supported")
                brain_name = label
            continue

        if in_data:
            if current_label is None:
                raise IndraError(f"Line {line_no}: data directive without label")

            if line.startswith(".i8 "):
                values = _parse_values(line[4:].strip(), line_no, -128, 127)
                if current_kind not in (None, "i8"):
                    raise IndraError(f"Line {line_no}: label {current_label!r} mixes data kinds")
                current_kind = "i8"
                i8_data.setdefault(current_label, []).extend(values)
                continue

            if line.startswith(".i32 "):
                values = _parse_values(line[5:].strip(), line_no, -(2**31), 2**31 - 1)
                if current_kind not in (None, "i32"):
                    raise IndraError(f"Line {line_no}: label {current_label!r} mixes data kinds")
                current_kind = "i32"
                i32_data.setdefault(current_label, []).extend(values)
                continue

            raise IndraError(f"Line {line_no}: unknown data directive: {line!r}")

        if brain_name is None:
            raise IndraError(f"Line {line_no}: expected brain label before instructions")

        if ended:
            raise IndraError(f"Line {line_no}: instruction after END")

        if line == "END":
            ended = True
            continue

        dense_match = _DENSE_RE.match(line)
        if dense_match:
            activation = dense_match.group("activation").upper()
            if activation not in ACTIVATIONS:
                raise IndraError(f"Line {line_no}: unknown activation {activation!r}")

            input_count = _parse_int(dense_match.group("input"), line_no)
            output_count = _parse_int(dense_match.group("output"), line_no)
            shift_text = dense_match.group("shift")
            shift = DEFAULT_SHIFT if shift_text is None else _parse_int(shift_text, line_no)

            if input_count <= 0:
                raise IndraError(f"Line {line_no}: input count must be positive")
            if output_count <= 0:
                raise IndraError(f"Line {line_no}: output count must be positive")
            if shift < 0 or shift > 31:
                raise IndraError(f"Line {line_no}: SHIFT must be in range 0..31")

            layers.append(
                DenseLayer(
                    input_count=input_count,
                    output_count=output_count,
                    weight_label=dense_match.group("weight"),
                    bias_label=dense_match.group("bias"),
                    activation=activation,
                    shift=shift,
                )
            )
            continue

        raise IndraError(f"Line {line_no}: unknown instruction: {line!r}")

    if brain_name is None:
        raise IndraError("Missing brain label")
    if not ended:
        raise IndraError("Missing END")
    if not layers:
        raise IndraError("Brain must contain at least one layer")

    assembly = Assembly(
        brain=Brain(name=brain_name, layers=tuple(layers)),
        data=DataSection(
            i8={key: tuple(value) for key, value in i8_data.items()},
            i32={key: tuple(value) for key, value in i32_data.items()},
        ),
    )

    validate(assembly)
    return assembly


def parse_file(path: str | Path) -> Assembly:
    return parse_text(Path(path).read_text(encoding="utf-8"))


def validate(assembly: Assembly) -> None:
    previous_output: int | None = None

    for index, layer in enumerate(assembly.brain.layers):
        if previous_output is not None and layer.input_count != previous_output:
            raise IndraError(
                f"Layer {index}: input count {layer.input_count} does not match "
                f"previous output count {previous_output}"
            )

        weights = assembly.data.i8.get(layer.weight_label)
        if weights is None:
            raise IndraError(f"Layer {index}: missing weight label {layer.weight_label!r}")
        if len(weights) != layer.expected_weight_count:
            raise IndraError(
                f"Layer {index}: weight label {layer.weight_label!r} has {len(weights)} values, "
                f"expected {layer.expected_weight_count}"
            )

        biases = assembly.data.i32.get(layer.bias_label)
        if biases is None:
            raise IndraError(f"Layer {index}: missing bias label {layer.bias_label!r}")
        if len(biases) != layer.expected_bias_count:
            raise IndraError(
                f"Layer {index}: bias label {layer.bias_label!r} has {len(biases)} values, "
                f"expected {layer.expected_bias_count}"
            )

        previous_output = layer.output_count


def to_dict(assembly: Assembly) -> dict:
    return asdict(assembly)


def report(assembly: Assembly) -> str:
    lines = [f"Brain: {assembly.brain.name}"]

    for index, layer in enumerate(assembly.brain.layers):
        weights = assembly.data.i8[layer.weight_label]
        biases = assembly.data.i32[layer.bias_label]
        lines.append(
            "Layer "
            f"{index}: DENSE {layer.input_count} -> {layer.output_count}, "
            f"W={layer.weight_label} {len(weights)}/{layer.expected_weight_count}, "
            f"B={layer.bias_label} {len(biases)}/{layer.expected_bias_count}, "
            f"ACT={layer.activation}, SHIFT={layer.shift}"
        )

    lines.append("OK")
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse and validate an Indra v0 brain file.")
    parser.add_argument("source", help="Path to .indra source file.")
    parser.add_argument("--json", action="store_true", help="Print parsed assembly as JSON.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        assembly = parse_file(args.source)
    except IndraError as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.json:
        print(json.dumps(to_dict(assembly), indent=2))
    else:
        print(report(assembly))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
