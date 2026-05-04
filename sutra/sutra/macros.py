"""Source-level Sutra macro expansion."""

import re

from .errors import AssemblerError
from .parsing import parse_predicate_register


BRANCH_MACROS = {
    "BEQ": "CMP.EQ",
    "BNE": "CMP.NE",
    "BLT": "CMP.LT",
    "BLE": "CMP.LE",
    "BGT": "CMP.GT",
    "BGE": "CMP.GE",
}


def _split_predicate_text(line: str):
    m = re.match(r"^(\s*\(\s*!?\s*B[0-7]\s*\)\s*)(.*)$", line, flags=re.IGNORECASE)
    if not m:
        return "", line
    return m.group(1), m.group(2).strip()


def _unique_label(prefix: str, counter: int) -> str:
    return f".__{prefix}_{counter}"


def expand_macro_line(line: str, counter: int):
    if line.endswith(":"):
        return [line], counter

    pred_text, body = _split_predicate_text(line)
    parts = body.replace(",", " ").split()
    if not parts:
        return [line], counter

    m = parts[0].upper()
    ops = parts[1:]

    def p(x: str) -> str:
        return pred_text + x if pred_text else x

    if m == "INC":
        if len(ops) != 1:
            raise AssemblerError("inc requires 1 operand: inc r0")
        return [p(f"iadd {ops[0]}, {ops[0]}, 1")], counter

    if m == "DEC":
        if len(ops) != 1:
            raise AssemblerError("dec requires 1 operand: dec r0")
        return [p(f"isub {ops[0]}, {ops[0]}, 1")], counter

    if m == "NEG":
        if len(ops) != 2:
            raise AssemblerError("neg requires 2 operands: neg rd, rs")
        return [p(f"isub {ops[0]}, 0, {ops[1]}")], counter

    if m == "FNEG":
        if len(ops) != 2:
            raise AssemblerError("fneg requires 2 operands: fneg rd, rs")
        return [p(f"fsub {ops[0]}, 0.0, {ops[1]}")], counter

    if m == "JUMP_IF":
        if pred_text:
            raise AssemblerError("jump_if cannot be used with an external predicate")
        if len(ops) != 2:
            raise AssemblerError("jump_if requires: jump_if b0, label")
        b = parse_predicate_register(ops[0])
        return [f"(b{b}) jump {ops[1]}"], counter

    if m == "JUMP_IF_NOT":
        if pred_text:
            raise AssemblerError("jump_if_not cannot be used with an external predicate")
        if len(ops) != 2:
            raise AssemblerError("jump_if_not requires: jump_if_not b0, label")
        b = parse_predicate_register(ops[0])
        if b == 7:
            return ["bnot b6, b7", f"(b6) jump {ops[1]}"], counter
        return [f"(!b{b}) jump {ops[1]}"], counter

    if m in BRANCH_MACROS:
        if pred_text:
            raise AssemblerError(f"{m.lower()} cannot be used with an external predicate")
        if len(ops) != 3:
            raise AssemblerError(f"{m.lower()} requires: {m.lower()} rs, rt, label")
        return [f"{BRANCH_MACROS[m]} b7, {ops[0]}, {ops[1]}", f"(b7) jump {ops[2]}"], counter

    if m == "WAIT_RX":
        if pred_text:
            raise AssemblerError("wait_rx cannot be used with an external predicate")
        if len(ops) != 0:
            raise AssemblerError("wait_rx does not take operands")
        label = _unique_label("wait_rx", counter)
        done = label + "_done"
        counter += 1
        return [label + ":", "move b7, @uart_rx_ready", f"(b7) jump {done}", f"jump {label}", done + ":"], counter

    if m == "READ_RX":
        if pred_text:
            raise AssemblerError("read_rx cannot be used with an external predicate")
        if len(ops) != 1:
            raise AssemblerError("read_rx requires: read_rx rd")
        label = _unique_label("read_rx", counter)
        done = label + "_done"
        counter += 1
        return [label + ":", "move b7, @uart_rx_ready", f"(b7) jump {done}", f"jump {label}", done + ":", f"move {ops[0]}, @uart_rx"], counter

    if m == "WAIT_UART":
        if pred_text:
            raise AssemblerError("wait_uart cannot be used with an external predicate")
        if len(ops) != 0:
            raise AssemblerError("wait_uart does not take operands")
        label = _unique_label("wait_uart", counter)
        done = label + "_done"
        counter += 1
        return [label + ":", "move b7, @uart_ready", f"(b7) jump {done}", f"jump {label}", done + ":"], counter

    if m == "WRITE_TX":
        if pred_text:
            raise AssemblerError("write_tx cannot be used with an external predicate")
        if len(ops) != 1:
            raise AssemblerError("write_tx requires: write_tx rs")
        label = _unique_label("write_tx", counter)
        done = label + "_done"
        counter += 1
        return [label + ":", "move b7, @uart_ready", f"(b7) jump {done}", f"jump {label}", done + ":", f"move @uart_tx, {ops[0]}"], counter

    return [line], counter
