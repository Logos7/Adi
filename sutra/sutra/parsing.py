"""Sutra token, literal, register, predicate, and memory operand parsing."""

import math
import re

from .constants import *
from .errors import AssemblerError


def to_u32(value: int) -> int:
    return value & MASK32


def fixed_literal_to_q(value: str) -> int:
    return int(round(float(value) * Q))


def parse_plain_int(raw: str) -> int:
    base = 10
    if raw.lower().startswith(("0x", "-0x", "+0x")):
        base = 16
    elif raw.lower().startswith(("0b", "-0b", "+0b")):
        base = 2
    return int(raw, base)


def parse_address_value(token: str) -> int:
    raw = token.strip()
    if raw.startswith("&"):
        raw = raw[1:]

    u = raw.upper()
    if u in MMIO_SYMBOLS:
        return MMIO_SYMBOLS[u]
    if u in GPIO_ALIASES:
        return GPIO_ALIASES[u]
    if u in DATA_SYMBOLS:
        return DATA_SYMBOLS[u]

    l = raw.lower()
    if l.startswith("pin"):
        n = int(l[3:])
        if not 0 <= n <= GPIO_PIN_MAX:
            raise AssemblerError(f"pin{n} is out of range 0..{GPIO_PIN_MAX}")
        return n
    if l.startswith("inpin"):
        n = int(l[5:])
        if not 0 <= n <= 63:
            raise AssemblerError(f"inpin{n} is out of range 0..63")
        return GPIO_INPIN_BASE + n

    return parse_plain_int(raw)


def parse_sqrt_literal(raw: str):
    x = raw.strip()
    lower = x.lower()

    if x.startswith("√"):
        body = x[1:]
    elif lower.startswith("sqrt(") and x.endswith(")"):
        body = x[5:-1]
    elif lower.startswith("sqrt") and len(x) > 4:
        body = x[4:]
    else:
        return None

    if not body:
        raise AssemblerError(f"Empty square-root literal: {raw}")

    body_s = body.strip()
    if (
        re.fullmatch(r"[-+]?\d+", body_s)
        or re.fullmatch(r"[-+]?0[xX][0-9a-fA-F]+", body_s)
        or re.fullmatch(r"[-+]?0[bB][01]+", body_s)
    ):
        real = float(int(body_s, 0))
    else:
        value = parse_immediate_raw(body_s)
        signed = value if value < 0x80000000 else value - 0x100000000
        real = signed / Q

    if real < 0:
        raise AssemblerError(f"Square root of a negative value: {raw}")

    return to_u32(q(math.sqrt(real)))


def parse_immediate_raw(token: str) -> int:
    raw = token.strip()

    if raw.startswith("#"):
        raise AssemblerError("Sutra v1.4 does not use # for immediates; write e.g. move r0, π or move r0, 123")
    if raw.startswith("@"):
        raise AssemblerError("@ means memory/IO; use & for an address value, e.g. move r0, &uart_tx")
    if raw.startswith("&"):
        return to_u32(parse_address_value(raw))

    sqrt_value = parse_sqrt_literal(raw)
    if sqrt_value is not None:
        return sqrt_value

    key = raw.upper()
    if key in SCALAR_CONSTANTS:
        return to_u32(SCALAR_CONSTANTS[key])
    if raw in SCALAR_CONSTANTS:
        return to_u32(SCALAR_CONSTANTS[raw])
    if key in DATA_SYMBOLS:
        return to_u32(DATA_SYMBOLS[key])

    if re.fullmatch(r"[-+]?\d+\.\d+", raw):
        return to_u32(fixed_literal_to_q(raw))

    try:
        return to_u32(parse_plain_int(raw))
    except ValueError:
        raise AssemblerError(f"Unknown immediate value: {raw}")


def parse_immediate(token: str) -> int:
    token = token.strip()
    if not token:
        raise AssemblerError("Empty immediate")
    return parse_immediate_raw(token)


def parse_small_int(token: str) -> int:
    raw = token.strip()
    if raw.startswith("#"):
        raise AssemblerError("Sutra v1.4 does not use #; write e.g. shl r0, r1, 3")
    return parse_plain_int(raw)


def parse_register(token: str) -> int:
    raw = token.strip()
    u = raw.upper()

    if u in T_REGS:
        return T_REGS[u]

    if not u.startswith("R"):
        raise AssemblerError(f"Expected register r0..r31 or t0..t7, got: {raw}")

    try:
        n = int(u[1:])
    except ValueError:
        raise AssemblerError(f"Invalid register number: {raw}")

    if not 0 <= n <= 31:
        raise AssemblerError(f"r{n} is out of range 0..31")

    return n


def parse_complex_register(token: str) -> int:
    raw = token.strip().upper()

    if not raw.startswith("Z"):
        raise AssemblerError(f"Expected complex register z0..z15, got: {token}")

    try:
        n = int(raw[1:])
    except ValueError:
        raise AssemblerError(f"Invalid complex register number: {token}")

    if not 0 <= n <= 15:
        raise AssemblerError(f"z{n} is out of range 0..15")

    return n


def parse_bool_register(token: str) -> int:
    raw = token.strip()
    u = raw.upper()

    if u in BOOL_CONSTANTS:
        return BOOL_CONSTANTS[u]

    if not u.startswith("B"):
        raise AssemblerError(f"Expected bool b0..b7 or true/false/high/low, got: {raw}")

    try:
        n = int(u[1:])
    except ValueError:
        raise AssemblerError(f"Invalid bool register number: {raw}")

    if not 0 <= n <= 7:
        raise AssemblerError(f"b{n} is out of range 0..7")

    return n


def parse_predicate_register(token: str) -> int:
    raw = token.strip().upper()

    if not raw.startswith("B"):
        raise AssemblerError(f"Predicate uses only b0..b7, got: {token}")

    n = int(raw[1:])
    if not 0 <= n <= 7:
        raise AssemblerError(f"Predicate b{n} is out of range 0..7")

    return n


def parse_memory_operand(token: str):
    raw = token.strip()

    if raw.startswith("[") or raw.endswith("]"):
        raise AssemblerError("Sutra v1.4 does not use [address]; use @address, e.g. move r0, @10 / move @r1, r0 / move r0, @r1+4")

    if not raw.startswith("@"):
        raise AssemblerError(f"Memory/IO address must start with @, got: {raw}")

    body = raw[1:].strip()
    if not body:
        raise AssemblerError("Empty @ memory operand")

    reg_offset = re.fullmatch(r"([rRtT]\d+)\s*([+-])\s*(.+)", body)
    if reg_offset:
        reg = parse_register(reg_offset.group(1))
        off = parse_small_int(reg_offset.group(3))
        if reg_offset.group(2) == "-":
            off = -off
        return "reg", reg, None, off

    try:
        return "reg", parse_register(body), None, 0
    except AssemblerError:
        pass

    u = body.upper()
    if u in MMIO_SYMBOLS:
        domain = "bool" if u in ("UART_READY", "UART_TX_READY", "UART_RX_READY") else "word"
        return "imm", MMIO_SYMBOLS[u], domain, 0

    if u in GPIO_ALIASES:
        return "imm", GPIO_ALIASES[u], "bool", 0

    l = body.lower()
    if l.startswith("pin"):
        n = int(l[3:])
        if not 0 <= n <= GPIO_PIN_MAX:
            raise AssemblerError(f"pin{n} is out of range 0..{GPIO_PIN_MAX}")
        return "imm", n, "bool", 0

    if l.startswith("inpin"):
        n = int(l[5:])
        if not 0 <= n <= 63:
            raise AssemblerError(f"inpin{n} is out of range 0..63")
        return "imm", GPIO_INPIN_BASE + n, "bool", 0

    if u in DATA_SYMBOLS:
        return "imm", DATA_SYMBOLS[u], None, 0

    return "imm", parse_small_int(body), None, 0


def encode_predicate(bool_idx: int, negated: bool = False) -> int:
    pred = (0b1000 if negated else 0) | (bool_idx & 0b111)
    if pred == PRED_ALWAYS:
        raise AssemblerError("Predicate (!b7) collides with the always predicate encoding; use a different bool or invert the logic")
    return pred


def parse_predicate_prefix(line: str):
    match = re.match(r"^\(\s*(!?)\s*(B[0-7])\s*\)\s*(.*)$", line, flags=re.IGNORECASE)
    if not match:
        return PRED_ALWAYS, line

    negated = bool(match.group(1))
    bool_idx = parse_predicate_register(match.group(2))
    rest = match.group(3).strip()
    if not rest:
        raise AssemblerError("Predicate without an instruction")

    return encode_predicate(bool_idx, negated), rest
