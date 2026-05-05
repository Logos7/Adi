#!/usr/bin/env python3
"""Indra v0 brain assembler parser and validator.

This tool parses the text .indra format used by the Indra neural processor.
It validates layer descriptors, data labels, weight counts, bias counts, and
basic v0 hardware limits.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

MAX_INPUTS = 32
MAX_LAYER_WIDTH = 32
MAX_LAYERS = 4
MAX_OUTPUTS = 16
MAX_SHIFT = 31

ACTIVATIONS: dict[str, int] = {
    "NONE": 0,
    "RELU": 1,
    "CLAMP": 2,
    "SIGN": 3,
}

_DENSE_RE = re.compile(
    r"^DENSE\s+"
    r"(?P<in>\d+)\s+"
    r"(?P<out>\d+)\s+"
    r"W=(?P<w>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"B=(?P<b>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"ACT=(?P<act>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+SHIFT=(?P<shift>\d+))?"
    r"\s*$"
)

_LABEL_RE = re.compile(r"^(?P<label>[A-Za-z_][A-Za-z0-9_]*):\s*$")


class IndraError(ValueError):
    """Raised when an Indra source file is invalid."""


@dataclass(frozen=True)
class DenseLayer:
    """A DENSE layer descriptor."""

    input_count: int
    output_count: int
    weight_label: str
    bias_label: str
    activation: str
    shift: int = 0
    line_no: int = 0

    @property
    def weight_count(self) -> int:
        return self.input_count * self.output_count

    @property
    def bias_count(self) -> int:
        return self.output_count


@dataclass
class DataSection:
    """A named data section."""

    label: str
    kind: str
    values: list[int] = field(default_factory=list)
    line_no: int = 0


@dataclass
class BrainProgram:
    """A parsed Indra brain program."""

    name: str
    layers: list[DenseLayer]
    data: dict[str, DataSection]
    data_order: list[str]
    source_path: Path | None = None

    def validate(self) -> None:
        if not self.name:
            raise IndraError("Missing brain label.")
        if not self.layers:
            raise IndraError(f"Brain '{self.name}' has no layers.")
        if len(self.layers) > MAX_LAYERS:
            raise IndraError(
                f"Brain '{self.name}' has {len(self.layers)} layers, max is {MAX_LAYERS}."
            )

        previous_output: int | None = None
        for index, layer in enumerate(self.layers):
            if layer.input_count <= 0 or layer.output_count <= 0:
                raise IndraError(f"Layer {index}: counts must be positive.")
            if layer.input_count > MAX_INPUTS and index == 0:
                raise IndraError(
                    f"Layer {index}: input count {layer.input_count} exceeds {MAX_INPUTS}."
                )
            if layer.input_count > MAX_LAYER_WIDTH and index > 0:
                raise IndraError(
                    f"Layer {index}: input width {layer.input_count} exceeds {MAX_LAYER_WIDTH}."
                )
            if layer.output_count > MAX_LAYER_WIDTH and index < len(self.layers) - 1:
                raise IndraError(
                    f"Layer {index}: output width {layer.output_count} exceeds {MAX_LAYER_WIDTH}."
                )
            if layer.output_count > MAX_OUTPUTS and index == len(self.layers) - 1:
                raise IndraError(
                    f"Layer {index}: output count {layer.output_count} exceeds {MAX_OUTPUTS}."
                )
            if previous_output is not None and layer.input_count != previous_output:
                raise IndraError(
                    f"Layer {index}: input count {layer.input_count} does not match "
                    f"previous output count {previous_output}."
                )
            previous_output = layer.output_count

            if layer.activation not in ACTIVATIONS:
                allowed = ", ".join(ACTIVATIONS)
                raise IndraError(
                    f"Layer {index}: unsupported activation '{layer.activation}'. Allowed: {allowed}."
                )
            if layer.shift < 0 or layer.shift > MAX_SHIFT:
                raise IndraError(
                    f"Layer {index}: SHIFT={layer.shift} is outside 0..{MAX_SHIFT}."
                )

            weight_data = self.data.get(layer.weight_label)
            if weight_data is None:
                raise IndraError(f"Layer {index}: missing weight label '{layer.weight_label}'.")
            if weight_data.kind != ".i8":
                raise IndraError(
                    f"Layer {index}: weights '{layer.weight_label}' must use .i8, got {weight_data.kind}."
                )
            if len(weight_data.values) != layer.weight_count:
                raise IndraError(
                    f"Layer {index}: weights '{layer.weight_label}' have {len(weight_data.values)} "
                    f"values, expected {layer.weight_count}."
                )

            bias_data = self.data.get(layer.bias_label)
            if bias_data is None:
                raise IndraError(f"Layer {index}: missing bias label '{layer.bias_label}'.")
            if bias_data.kind != ".i32":
                raise IndraError(
                    f"Layer {index}: biases '{layer.bias_label}' must use .i32, got {bias_data.kind}."
                )
            if len(bias_data.values) != layer.bias_count:
                raise IndraError(
                    f"Layer {index}: biases '{layer.bias_label}' have {len(bias_data.values)} "
                    f"values, expected {layer.bias_count}."
                )


def _strip_comment(line: str) -> str:
    cut = len(line)
    for marker in (";", "#"):
        index = line.find(marker)
        if index != -1:
            cut = min(cut, index)
    return line[:cut].strip()


def _parse_values(text: str, kind: str, line_no: int) -> list[int]:
    raw_values = [part for part in re.split(r"[\s,]+", text.strip()) if part]
    values: list[int] = []
    for raw in raw_values:
        try:
            value = int(raw, 0)
        except ValueError as exc:
            raise IndraError(f"Line {line_no}: invalid integer '{raw}'.") from exc

        if kind == ".i8" and not -128 <= value <= 127:
            raise IndraError(f"Line {line_no}: .i8 value {value} is outside -128..127.")
        if kind == ".i32" and not -(2**31) <= value <= 2**31 - 1:
            raise IndraError(f"Line {line_no}: .i32 value {value} is outside int32 range.")
        values.append(value)
    return values


def parse_indra_source(text: str, source_path: Path | None = None) -> BrainProgram:
    """Parse an Indra source string and return a validated brain program."""

    brain_name = ""
    layers: list[DenseLayer] = []
    data: dict[str, DataSection] = {}
    data_order: list[str] = []
    in_data = False
    current_data_label: str | None = None
    end_seen = False

    for line_no, original_line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(original_line)
        if not line:
            continue

        if line == ".data":
            in_data = True
            current_data_label = None
            continue

        label_match = _LABEL_RE.match(line)
        if label_match:
            label = label_match.group("label")
            if in_data:
                if label in data:
                    raise IndraError(f"Line {line_no}: duplicate data label '{label}'.")
                data[label] = DataSection(label=label, kind="", line_no=line_no)
                data_order.append(label)
                current_data_label = label
            else:
                if brain_name:
                    raise IndraError(f"Line {line_no}: multiple brain labels are not supported in v0.")
                brain_name = label
            continue

        if in_data:
            if current_data_label is None:
                raise IndraError(f"Line {line_no}: data values must follow a label.")
            if line.startswith(".i8"):
                kind = ".i8"
                payload = line[3:].strip()
            elif line.startswith(".i32"):
                kind = ".i32"
                payload = line[4:].strip()
            else:
                raise IndraError(f"Line {line_no}: expected .i8 or .i32 data directive.")

            section = data[current_data_label]
            if section.kind and section.kind != kind:
                raise IndraError(
                    f"Line {line_no}: data label '{current_data_label}' mixes {section.kind} and {kind}."
                )
            section.kind = kind
            section.values.extend(_parse_values(payload, kind, line_no))
            continue

        if end_seen:
            raise IndraError(f"Line {line_no}: unexpected instruction after END.")

        dense_match = _DENSE_RE.match(line)
        if dense_match:
            activation = dense_match.group("act").upper()
            shift_text = dense_match.group("shift")
            layers.append(
                DenseLayer(
                    input_count=int(dense_match.group("in")),
                    output_count=int(dense_match.group("out")),
                    weight_label=dense_match.group("w"),
                    bias_label=dense_match.group("b"),
                    activation=activation,
                    shift=int(shift_text) if shift_text is not None else 0,
                    line_no=line_no,
                )
            )
            continue

        if line == "END":
            end_seen = True
            continue

        raise IndraError(f"Line {line_no}: cannot parse '{line}'.")

    if not end_seen:
        raise IndraError("Missing END instruction.")

    for section in data.values():
        if not section.kind:
            raise IndraError(f"Data label '{section.label}' has no data directive.")

    program = BrainProgram(
        name=brain_name,
        layers=layers,
        data=data,
        data_order=data_order,
        source_path=source_path,
    )
    program.validate()
    return program


def parse_indra_file(path: str | Path) -> BrainProgram:
    source_path = Path(path)
    return parse_indra_source(source_path.read_text(encoding="utf-8"), source_path=source_path)


def build_report(program: BrainProgram) -> str:
    lines = [f"Brain: {program.name}"]
    for index, layer in enumerate(program.layers):
        weights = program.data[layer.weight_label]
        biases = program.data[layer.bias_label]
        lines.append(
            f"Layer {index}: DENSE {layer.input_count} -> {layer.output_count}, "
            f"weights={len(weights.values)}/{layer.weight_count}, "
            f"biases={len(biases.values)}/{layer.bias_count}, "
            f"act={layer.activation}, shift={layer.shift}"
        )
    lines.append("OK")
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse and validate an Indra v0 brain file.")
    parser.add_argument("source", help="Path to a .indra file.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        program = parse_indra_file(args.source)
    except IndraError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(build_report(program))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
