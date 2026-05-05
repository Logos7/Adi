#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ACTIVATIONS = {
    "NONE": 0,
    "RELU": 1,
    "CLAMP": 2,
    "SIGN": 3,
}

DENSE_RE = re.compile(
    r"^DENSE\s+(?P<inputs>\d+)\s+(?P<outputs>\d+)\s+W=(?P<weights>[A-Za-z_][A-Za-z0-9_]*)\s+B=(?P<biases>[A-Za-z_][A-Za-z0-9_]*)\s+ACT=(?P<activation>[A-Za-z_][A-Za-z0-9_]*)$"
)

LABEL_RE = re.compile(r"^(?P<label>[A-Za-z_][A-Za-z0-9_]*):$")
DATA_RE = re.compile(r"^\.(?P<kind>i8|i32)\s+(?P<values>.+)$")


class IndraAsmError(Exception):
    pass


@dataclass(frozen=True)
class DenseLayer:
    input_count: int
    output_count: int
    weight_label: str
    bias_label: str
    activation: str
    line_no: int

    @property
    def weight_count(self) -> int:
        return self.input_count * self.output_count

    @property
    def bias_count(self) -> int:
        return self.output_count


@dataclass(frozen=True)
class DataBlock:
    label: str
    kind: str
    values: tuple[int, ...]
    line_no: int


@dataclass(frozen=True)
class BrainProgram:
    name: str
    layers: tuple[DenseLayer, ...]
    data: dict[str, DataBlock]


def strip_comment(line: str) -> str:
    line = line.split(";", 1)[0]
    line = line.split("#", 1)[0]
    return line.strip()


def parse_values(text: str, line_no: int) -> tuple[int, ...]:
    values: list[int] = []
    for raw in text.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            values.append(int(item, 0))
        except ValueError as ex:
            raise IndraAsmError(f"line {line_no}: invalid integer value: {item}") from ex
    if not values:
        raise IndraAsmError(f"line {line_no}: data directive has no values")
    return tuple(values)


def parse_indra_source(text: str) -> BrainProgram:
    brain_name: str | None = None
    layers: list[DenseLayer] = []
    data: dict[str, DataBlock] = {}
    section = "program"
    current_label: str | None = None
    current_kind: str | None = None
    current_values: list[int] = []
    current_line = 0
    ended = False

    def flush_data() -> None:
        nonlocal current_label, current_kind, current_values, current_line
        if current_label is None:
            return
        if current_kind is None:
            raise IndraAsmError(f"line {current_line}: data label '{current_label}' has no data directive")
        if current_label in data:
            raise IndraAsmError(f"line {current_line}: duplicate data label: {current_label}")
        data[current_label] = DataBlock(current_label, current_kind, tuple(current_values), current_line)
        current_label = None
        current_kind = None
        current_values = []
        current_line = 0

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = strip_comment(raw_line)
        if not line:
            continue

        if line == ".data":
            if brain_name is None:
                raise IndraAsmError(f"line {line_no}: .data appears before brain label")
            if not ended:
                raise IndraAsmError(f"line {line_no}: .data appears before END")
            section = "data"
            continue

        label_match = LABEL_RE.match(line)
        if label_match:
            label = label_match.group("label")
            if section == "program":
                if brain_name is not None:
                    raise IndraAsmError(f"line {line_no}: unexpected program label: {label}")
                brain_name = label
            else:
                flush_data()
                current_label = label
                current_line = line_no
            continue

        if section == "program":
            if brain_name is None:
                raise IndraAsmError(f"line {line_no}: expected brain label")
            if line == "END":
                ended = True
                continue
            if ended:
                raise IndraAsmError(f"line {line_no}: instruction after END")
            dense_match = DENSE_RE.match(line)
            if not dense_match:
                raise IndraAsmError(f"line {line_no}: invalid instruction: {line}")
            activation = dense_match.group("activation").upper()
            if activation not in ACTIVATIONS:
                raise IndraAsmError(f"line {line_no}: unsupported activation: {activation}")
            layers.append(
                DenseLayer(
                    input_count=int(dense_match.group("inputs")),
                    output_count=int(dense_match.group("outputs")),
                    weight_label=dense_match.group("weights"),
                    bias_label=dense_match.group("biases"),
                    activation=activation,
                    line_no=line_no,
                )
            )
            continue

        data_match = DATA_RE.match(line)
        if not data_match:
            raise IndraAsmError(f"line {line_no}: invalid data line: {line}")
        if current_label is None:
            raise IndraAsmError(f"line {line_no}: data directive without label")
        kind = data_match.group("kind")
        values = parse_values(data_match.group("values"), line_no)
        if current_kind is None:
            current_kind = kind
        elif current_kind != kind:
            raise IndraAsmError(f"line {line_no}: mixed data kinds under label '{current_label}'")
        current_values.extend(values)

    flush_data()

    if brain_name is None:
        raise IndraAsmError("missing brain label")
    if not layers:
        raise IndraAsmError("brain has no layers")
    if not ended:
        raise IndraAsmError("missing END")

    program = BrainProgram(brain_name, tuple(layers), data)
    validate_program(program)
    return program


def read_indra_file(path: Path) -> BrainProgram:
    return parse_indra_source(path.read_text(encoding="utf-8"))


def validate_int_range(block: DataBlock) -> None:
    if block.kind == "i8":
        lo, hi = -128, 127
    elif block.kind == "i32":
        lo, hi = -(2**31), 2**31 - 1
    else:
        raise IndraAsmError(f"line {block.line_no}: unsupported data kind: {block.kind}")
    for value in block.values:
        if value < lo or value > hi:
            raise IndraAsmError(
                f"line {block.line_no}: value {value} outside {block.kind} range [{lo}, {hi}]"
            )


def validate_program(program: BrainProgram) -> None:
    for layer in program.layers:
        if layer.input_count <= 0 or layer.output_count <= 0:
            raise IndraAsmError(f"line {layer.line_no}: layer dimensions must be positive")
        if layer.weight_label not in program.data:
            raise IndraAsmError(f"line {layer.line_no}: missing weight block: {layer.weight_label}")
        if layer.bias_label not in program.data:
            raise IndraAsmError(f"line {layer.line_no}: missing bias block: {layer.bias_label}")
        weights = program.data[layer.weight_label]
        biases = program.data[layer.bias_label]
        if weights.kind != "i8":
            raise IndraAsmError(f"line {weights.line_no}: weight block '{weights.label}' must use .i8")
        if biases.kind != "i32":
            raise IndraAsmError(f"line {biases.line_no}: bias block '{biases.label}' must use .i32")
        validate_int_range(weights)
        validate_int_range(biases)
        if len(weights.values) != layer.weight_count:
            raise IndraAsmError(
                f"line {layer.line_no}: layer expects {layer.weight_count} weights in '{weights.label}', got {len(weights.values)}"
            )
        if len(biases.values) != layer.bias_count:
            raise IndraAsmError(
                f"line {layer.line_no}: layer expects {layer.bias_count} biases in '{biases.label}', got {len(biases.values)}"
            )


def format_report(program: BrainProgram) -> str:
    lines = [f"Brain: {program.name}"]
    for index, layer in enumerate(program.layers):
        weights = program.data[layer.weight_label]
        biases = program.data[layer.bias_label]
        lines.append(
            f"Layer {index}: DENSE {layer.input_count} -> {layer.output_count}, "
            f"weights={len(weights.values)}/{layer.weight_count}, "
            f"biases={len(biases.values)}/{layer.bias_count}, "
            f"activation={layer.activation}"
        )
    lines.append("OK")
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an Indra v0 brain source file.")
    parser.add_argument("source", type=Path)
    args = parser.parse_args(argv)
    try:
        program = read_indra_file(args.source)
    except IndraAsmError as ex:
        print(f"ERROR: {ex}")
        return 1
    print(format_report(program))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
