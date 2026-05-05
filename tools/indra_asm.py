#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MAX_INPUTS = 32
MAX_LAYER_WIDTH = 32
MAX_LAYERS = 4
MAX_OUTPUTS = 16

ACTIVATIONS = {"NONE", "RELU", "CLAMP", "SIGN"}

DENSE_RE = re.compile(
    r"^DENSE\s+"
    r"(?P<inputs>\d+)\s+"
    r"(?P<outputs>\d+)\s+"
    r"W=(?P<weights>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"B=(?P<biases>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"ACT=(?P<activation>[A-Za-z_][A-Za-z0-9_]*)$"
)

LABEL_RE = re.compile(r"^(?P<label>[A-Za-z_][A-Za-z0-9_]*):$")
DATA_RE = re.compile(r"^\.(?P<kind>i8|i32)\s+(?P<values>.+)$")


@dataclass(frozen=True)
class SourceLine:
    number: int
    text: str


@dataclass(frozen=True)
class DenseLayer:
    input_count: int
    output_count: int
    weight_label: str
    bias_label: str
    activation: str
    line: int


@dataclass(frozen=True)
class BrainProgram:
    name: str
    layers: list[DenseLayer]
    end_line: int


@dataclass(frozen=True)
class DataBlock:
    name: str
    kind: str
    values: list[int]
    line: int


@dataclass(frozen=True)
class IndraFile:
    brain: BrainProgram
    data: dict[str, DataBlock]


class IndraAsmError(Exception):
    pass


def strip_comment(line: str) -> str:
    cut = len(line)
    for marker in (";", "#"):
        index = line.find(marker)
        if index >= 0:
            cut = min(cut, index)
    return line[:cut].strip()


def source_lines(text: str) -> list[SourceLine]:
    result = []
    for index, line in enumerate(text.splitlines(), start=1):
        clean = strip_comment(line)
        if clean:
            result.append(SourceLine(index, clean))
    return result


def parse_int_list(raw: str, line: int) -> list[int]:
    values = []
    for token in raw.split(","):
        item = token.strip()
        if not item:
            continue
        try:
            values.append(int(item, 0))
        except ValueError as error:
            raise IndraAsmError(f"line {line}: invalid integer '{item}'") from error
    if not values:
        raise IndraAsmError(f"line {line}: empty data directive")
    return values


def validate_i8(value: int, line: int) -> None:
    if value < -128 or value > 127:
        raise IndraAsmError(f"line {line}: .i8 value out of range: {value}")


def validate_i32(value: int, line: int) -> None:
    if value < -2_147_483_648 or value > 2_147_483_647:
        raise IndraAsmError(f"line {line}: .i32 value out of range: {value}")


def parse_text(text: str) -> IndraFile:
    lines = source_lines(text)
    if not lines:
        raise IndraAsmError("empty Indra file")

    brain_name: str | None = None
    layers: list[DenseLayer] = []
    end_line: int | None = None
    data_mode = False
    data: dict[str, DataBlock] = {}
    current_data_label: str | None = None
    current_data_kind: str | None = None
    current_data_line: int | None = None
    current_data_values: list[int] = []

    def flush_data() -> None:
        nonlocal current_data_label, current_data_kind, current_data_line, current_data_values
        if current_data_label is None:
            return
        if current_data_kind is None:
            raise IndraAsmError(f"line {current_data_line}: data label '{current_data_label}' has no data")
        if current_data_label in data:
            raise IndraAsmError(f"line {current_data_line}: duplicate data label '{current_data_label}'")
        data[current_data_label] = DataBlock(
            name=current_data_label,
            kind=current_data_kind,
            values=current_data_values,
            line=current_data_line or 0,
        )
        current_data_label = None
        current_data_kind = None
        current_data_line = None
        current_data_values = []

    for src in lines:
        line = src.text

        if line == ".data":
            if brain_name is None:
                raise IndraAsmError(f"line {src.number}: .data before brain label")
            if end_line is None:
                raise IndraAsmError(f"line {src.number}: .data before END")
            data_mode = True
            continue

        label_match = LABEL_RE.match(line)
        if label_match:
            label = label_match.group("label")
            if not data_mode:
                if brain_name is not None:
                    raise IndraAsmError(f"line {src.number}: only one brain label is supported in v0")
                brain_name = label
            else:
                flush_data()
                current_data_label = label
                current_data_line = src.number
            continue

        if not data_mode:
            if brain_name is None:
                raise IndraAsmError(f"line {src.number}: expected brain label")

            if line == "END":
                if end_line is not None:
                    raise IndraAsmError(f"line {src.number}: duplicate END")
                end_line = src.number
                continue

            if end_line is not None:
                raise IndraAsmError(f"line {src.number}: instruction after END")

            dense_match = DENSE_RE.match(line)
            if not dense_match:
                raise IndraAsmError(f"line {src.number}: unknown instruction '{line}'")

            activation = dense_match.group("activation").upper()
            layers.append(
                DenseLayer(
                    input_count=int(dense_match.group("inputs")),
                    output_count=int(dense_match.group("outputs")),
                    weight_label=dense_match.group("weights"),
                    bias_label=dense_match.group("biases"),
                    activation=activation,
                    line=src.number,
                )
            )
            continue

        data_match = DATA_RE.match(line)
        if not data_match:
            raise IndraAsmError(f"line {src.number}: expected data label or data directive")

        if current_data_label is None:
            raise IndraAsmError(f"line {src.number}: data directive without label")

        kind = data_match.group("kind")
        values = parse_int_list(data_match.group("values"), src.number)

        if current_data_kind is None:
            current_data_kind = kind
        elif current_data_kind != kind:
            raise IndraAsmError(
                f"line {src.number}: mixed data kinds in '{current_data_label}': "
                f".{current_data_kind} and .{kind}"
            )

        if kind == "i8":
            for value in values:
                validate_i8(value, src.number)
        else:
            for value in values:
                validate_i32(value, src.number)

        current_data_values.extend(values)

    flush_data()

    if brain_name is None:
        raise IndraAsmError("missing brain label")
    if not layers:
        raise IndraAsmError("brain has no layers")
    if end_line is None:
        raise IndraAsmError("missing END")

    brain = BrainProgram(brain_name, layers, end_line)
    parsed = IndraFile(brain, data)
    validate(parsed)
    return parsed


def validate(parsed: IndraFile) -> None:
    layers = parsed.brain.layers

    if len(layers) > MAX_LAYERS:
        raise IndraAsmError(f"too many layers: {len(layers)} > {MAX_LAYERS}")

    previous_outputs: int | None = None

    for index, layer in enumerate(layers):
        if layer.input_count < 1:
            raise IndraAsmError(f"line {layer.line}: input count must be positive")
        if layer.output_count < 1:
            raise IndraAsmError(f"line {layer.line}: output count must be positive")
        if layer.input_count > MAX_INPUTS and index == 0:
            raise IndraAsmError(f"line {layer.line}: input count exceeds MAX_INPUTS={MAX_INPUTS}")
        if layer.input_count > MAX_LAYER_WIDTH and index > 0:
            raise IndraAsmError(f"line {layer.line}: layer input width exceeds MAX_LAYER_WIDTH={MAX_LAYER_WIDTH}")
        if layer.output_count > MAX_LAYER_WIDTH and index < len(layers) - 1:
            raise IndraAsmError(f"line {layer.line}: layer width exceeds MAX_LAYER_WIDTH={MAX_LAYER_WIDTH}")
        if layer.output_count > MAX_OUTPUTS and index == len(layers) - 1:
            raise IndraAsmError(f"line {layer.line}: output count exceeds MAX_OUTPUTS={MAX_OUTPUTS}")
        if previous_outputs is not None and layer.input_count != previous_outputs:
            raise IndraAsmError(
                f"line {layer.line}: layer input count {layer.input_count} "
                f"does not match previous output count {previous_outputs}"
            )
        if layer.activation not in ACTIVATIONS:
            raise IndraAsmError(f"line {layer.line}: unsupported activation '{layer.activation}'")

        weight_block = parsed.data.get(layer.weight_label)
        if weight_block is None:
            raise IndraAsmError(f"line {layer.line}: missing weight block '{layer.weight_label}'")
        if weight_block.kind != "i8":
            raise IndraAsmError(f"line {weight_block.line}: weight block '{weight_block.name}' must use .i8")

        bias_block = parsed.data.get(layer.bias_label)
        if bias_block is None:
            raise IndraAsmError(f"line {layer.line}: missing bias block '{layer.bias_label}'")
        if bias_block.kind != "i32":
            raise IndraAsmError(f"line {bias_block.line}: bias block '{bias_block.name}' must use .i32")

        expected_weights = layer.input_count * layer.output_count
        actual_weights = len(weight_block.values)
        if actual_weights != expected_weights:
            raise IndraAsmError(
                f"line {weight_block.line}: weight block '{weight_block.name}' has "
                f"{actual_weights} values, expected {expected_weights}"
            )

        expected_biases = layer.output_count
        actual_biases = len(bias_block.values)
        if actual_biases != expected_biases:
            raise IndraAsmError(
                f"line {bias_block.line}: bias block '{bias_block.name}' has "
                f"{actual_biases} values, expected {expected_biases}"
            )

        previous_outputs = layer.output_count


def load(path: Path) -> IndraFile:
    return parse_text(path.read_text(encoding="utf-8"))


def format_report(parsed: IndraFile) -> str:
    lines = [f"Brain: {parsed.brain.name}"]

    for index, layer in enumerate(parsed.brain.layers):
        weights = parsed.data[layer.weight_label]
        biases = parsed.data[layer.bias_label]
        expected_weights = layer.input_count * layer.output_count
        expected_biases = layer.output_count
        lines.append(
            f"Layer {index}: DENSE {layer.input_count} -> {layer.output_count}, "
            f"W={layer.weight_label} {len(weights.values)}/{expected_weights}, "
            f"B={layer.bias_label} {len(biases.values)}/{expected_biases}, "
            f"ACT={layer.activation}"
        )

    lines.append("OK")
    return "\n".join(lines)


def run(paths: Iterable[Path]) -> int:
    ok = True

    for path in paths:
        try:
            parsed = load(path)
            print(format_report(parsed))
        except IndraAsmError as error:
            ok = False
            print(f"{path}: ERROR: {error}", file=sys.stderr)

    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Indra v0 brain files.")
    parser.add_argument("paths", nargs="+", type=Path, help="Indra brain files to validate.")
    args = parser.parse_args(argv)
    return run(args.paths)


if __name__ == "__main__":
    raise SystemExit(main())
