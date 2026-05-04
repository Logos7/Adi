"""Sutra image assembler with separate code and data memories."""

from dataclasses import dataclass
import math
import re

from .constants import DATA_MEM_WORDS, DATA_SYMBOLS, q
from .errors import AssemblerError
from .parsing import parse_immediate_raw, to_u32
from .assembler import AssembledLine, _strip_comment, assemble, flatten_program


@dataclass
class SutraImage:
    """Assembled Sutra image with separate instruction memory and data memory."""

    code_words: list[int]
    data_words: list[int]
    lines: list[AssembledLine]
    data_symbols: dict[str, int]

    @property
    def words(self) -> list[int]:
        """Backward-friendly alias for the program/code words."""
        return self.code_words


def _split_csv_operands(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _parse_data_values(raw: str, directive: str, lineno: int) -> list[int]:
    parts = [part.strip() for part in raw.split(",")]
    if not parts or any(part == "" for part in parts):
        raise AssemblerError(f"Line {lineno}: {directive} requires comma-separated values")
    return [parse_immediate_raw(part) for part in parts]


def _parse_data_count(raw: str) -> int:
    value = parse_immediate_raw(raw)
    signed = value if value < 0x80000000 else value - 0x100000000
    if signed < 0:
        raise AssemblerError(f"Negative data size: {raw}")
    return signed


def _append_data_word(data: list[int], addr: int, word: int) -> None:
    if not 0 <= addr < DATA_MEM_WORDS:
        raise AssemblerError(f"data_mem address {addr} out of range 0..{DATA_MEM_WORDS - 1}")
    while len(data) <= addr:
        data.append(0)
    data[addr] = to_u32(word)


def _parse_data_directive(line: str, data: list[int], data_addr: int, lineno: int) -> int:
    parts = line.split(None, 1)
    directive = parts[0].lower()
    arg_text = parts[1].strip() if len(parts) > 1 else ""

    if directive == ".org":
        if not arg_text:
            raise AssemblerError(f"Line {lineno}: .org requires an address")
        addr = _parse_data_count(arg_text)
        if not 0 <= addr < DATA_MEM_WORDS:
            raise AssemblerError(f"Line {lineno}: .org outside data_mem range 0..{DATA_MEM_WORDS - 1}")
        return addr

    if directive in (".word", ".u32"):
        for value in _parse_data_values(arg_text, directive, lineno):
            _append_data_word(data, data_addr, value)
            data_addr += 1
        return data_addr

    if directive in (".q7_25", ".fixed", ".fix"):
        for value in _parse_data_values(arg_text, directive, lineno):
            _append_data_word(data, data_addr, value)
            data_addr += 1
        return data_addr

    if directive in (".zero", ".zeros", ".space"):
        if not arg_text:
            raise AssemblerError(f"Line {lineno}: {directive} requires a word count")
        count = _parse_data_count(arg_text)
        for _ in range(count):
            _append_data_word(data, data_addr, 0)
            data_addr += 1
        return data_addr

    if directive == ".sin_lut":
        count = 256 if not arg_text else _parse_data_count(arg_text)
        if count <= 0:
            raise AssemblerError(f"Line {lineno}: .sin_lut requires a positive sample count")
        if count & (count - 1):
            raise AssemblerError(f"Line {lineno}: .sin_lut should use a power-of-two sample count; got {count}")
        for i in range(count):
            _append_data_word(data, data_addr, q(math.sin((2.0 * math.pi * i) / count)))
            data_addr += 1
        return data_addr

    raise AssemblerError(f"Line {lineno}: unknown data directive: {directive}")


def _extract_code_and_data(source: str) -> tuple[str, list[int], dict[str, int]]:
    mode = "code"
    code_lines: list[str] = []
    data: list[int] = []
    data_symbols: dict[str, int] = {}
    data_addr = 0

    for lineno, original in enumerate(source.splitlines(), start=1):
        stripped = _strip_comment(original)
        if not stripped:
            if mode == "code":
                code_lines.append(original)
            continue

        lower = stripped.lower()
        if lower == ".code":
            mode = "code"
            continue
        if lower == ".data":
            mode = "data"
            continue

        if mode == "code":
            if stripped.startswith("."):
                raise AssemblerError(f"Line {lineno}: directive {stripped.split()[0]} is only available in .data")
            code_lines.append(original)
            continue

        # .data mode
        line = stripped
        while True:
            label_match = re.match(r"^([A-Za-z_.$][A-Za-z0-9_.$]*)\s*:\s*(.*)$", line)
            if not label_match:
                break
            label = label_match.group(1)
            key = label.upper()
            if key in data_symbols:
                raise AssemblerError(f"Line {lineno}: duplicate data label {label}")
            data_symbols[key] = data_addr
            line = label_match.group(2).strip()
            if not line:
                break

        if line:
            if not line.startswith("."):
                raise AssemblerError(f"Line {lineno}: expected a directive in .data, got: {line}")
            data_addr = _parse_data_directive(line, data, data_addr, lineno)

    return "\n".join(code_lines) + "\n", data, data_symbols


def assemble_image(source: str) -> SutraImage:
    """Assemble a Sutra v1.5 source into separate code and data images."""

    code_source, data_words, data_symbols = _extract_code_and_data(source)

    old_symbols = dict(DATA_SYMBOLS)
    try:
        DATA_SYMBOLS.clear()
        DATA_SYMBOLS.update(data_symbols)
        lines = assemble(code_source)
        if not lines:
            lines = assemble("halt\n")
    finally:
        DATA_SYMBOLS.clear()
        DATA_SYMBOLS.update(old_symbols)

    return SutraImage(
        code_words=flatten_program(lines),
        data_words=data_words,
        lines=lines,
        data_symbols=dict(data_symbols),
    )


def flatten_image(image: SutraImage) -> tuple[list[int], list[int]]:
    return image.code_words, image.data_words

