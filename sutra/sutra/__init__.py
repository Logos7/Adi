"""
Sutra — asembler dla procesora Brahma-Bija.

Brahma-Bija v1.3:
- oficjalny styl lowercase, parser case-insensitive,
- wartości natychmiastowe są bez prefiksu: 123, 1.0, π, √500, true, high,
- pamięć / MMIO / GPIO zawsze przez @: @10, @uart_tx, @led0, @r1,
- adres jako zwykła liczba przez &: &uart_tx, &led0, &pin15,
- r0..r31 jako prawdziwe GPR; t0..t7 aliasy r24..r31 (scratch/volatile),
- move dst, src wspólne dla word i bool,
- cadd/csub/cmul/cabs2 jako makra assemblera na parach z0..z11.
"""

from dataclasses import dataclass
import re
import math

OPCODE_NOP        = 0x00
OPCODE_ALU_R      = 0x01
OPCODE_CMP_R      = 0x02
OPCODE_LOAD_I     = 0x10
OPCODE_LOAD_L     = 0x11
OPCODE_LOAD_M     = 0x12   # indirect: load rd, @rs
OPCODE_SAVE_M     = 0x13   # indirect: save @rs, rd
OPCODE_LOAD_MD    = 0x14   # direct: load rd, @addr
OPCODE_SAVE_MD    = 0x15   # direct: save @addr, rd
OPCODE_SAVE_BI    = 0x20
OPCODE_LOAD_BI    = 0x21
OPCODE_BOOL_R     = 0x22
OPCODE_LOAD_BR    = 0x23
OPCODE_SAVE_BR    = 0x24
OPCODE_WAIT       = 0x30
OPCODE_JUMP       = 0x38
OPCODE_HALT       = 0x3F

FUNCT_IADD = 0x00
FUNCT_ISUB = 0x01
FUNCT_IAND = 0x02
FUNCT_IOR  = 0x03
FUNCT_IXOR = 0x04
FUNCT_SHL  = 0x05
FUNCT_SHR  = 0x06
FUNCT_SAR  = 0x07
FUNCT_IMUL = 0x08
FUNCT_FMUL = 0x09
FUNCT_ITOF = 0x0A
FUNCT_FTOI = 0x0B
FUNCT_INOT = 0x0C
FUNCT_FADD = 0x0D
FUNCT_FSUB = 0x0E
FUNCT_FABS = 0x0F
FUNCT_MOV  = 0x10

FUNCT_BAND = 0x00
FUNCT_BOR  = 0x01
FUNCT_BXOR = 0x02
FUNCT_BNOT = 0x03
FUNCT_BMOV = 0x04

FUNCT_CMP_EQ = 0x00
FUNCT_CMP_NE = 0x01
FUNCT_CMP_LT = 0x02
FUNCT_CMP_LE = 0x03
FUNCT_CMP_GT = 0x04
FUNCT_CMP_GE = 0x05

ALU_R_FUNCTS = {
    "IADD": FUNCT_IADD, "FADD": FUNCT_FADD,
    "ISUB": FUNCT_ISUB, "FSUB": FUNCT_FSUB,
    "IAND": FUNCT_IAND, "IOR": FUNCT_IOR, "IXOR": FUNCT_IXOR,
    "IMUL": FUNCT_IMUL, "FMUL": FUNCT_FMUL,
}

ALU_UNARY_FUNCTS = {"ITOF": FUNCT_ITOF, "FTOI": FUNCT_FTOI, "INOT": FUNCT_INOT, "FABS": FUNCT_FABS}
SHIFT_FUNCTS = {"SHL": FUNCT_SHL, "SHR": FUNCT_SHR, "SAR": FUNCT_SAR}
BOOL_R_FUNCTS = {"BAND": FUNCT_BAND, "BOR": FUNCT_BOR, "BXOR": FUNCT_BXOR}
BOOL_UNARY_FUNCTS = {"BNOT": FUNCT_BNOT}
CMP_FUNCTS = {"CMP.EQ": FUNCT_CMP_EQ, "CMP.NE": FUNCT_CMP_NE, "CMP.LT": FUNCT_CMP_LT, "CMP.LE": FUNCT_CMP_LE, "CMP.GT": FUNCT_CMP_GT, "CMP.GE": FUNCT_CMP_GE}

SHIFT_OPCODE = 26
SHIFT_RD     = 21
SHIFT_RS     = 16
SHIFT_RT     = 11
SHIFT_FUNCT  = 4
SHIFT_PRED   = 0
SHIFT_I_IMM  = 4
SHIFT_BD     = 22
SHIFT_BS     = 18
SHIFT_IB_IMM = 4
SHIFT_J_OFFSET = 4
PRED_ALWAYS = 0b1111
MASK32 = 0xFFFFFFFF
Q = 1 << 25

T_REGS = {f"T{i}": 24 + i for i in range(8)}
COMPLEX_SCRATCH = (24, 25, 26, 27)   # t0..t3
IMM_TEMPS = (31, 30, 29, 28)         # t7..t4

def q(value: float) -> int:
    return int(round(value * Q))


def golden_ratio() -> float:
    return (1 + math.sqrt(5)) / 2


SCALAR_CONSTANTS = {
    "ZERO": 0, "ONE": 1, "NEG_ONE": -1, "MINUS_ONE": -1,
    "FZERO": 0, "F_ZERO": 0, "FONE": Q, "F_ONE": Q,
    "FNEG_ONE": -Q, "F_NEG_ONE": -Q,
    "HALF": Q // 2, "½": Q // 2, "TWO": 2 * Q,

    "PI": q(math.pi), "π": q(math.pi),
    "HALF_PI": q(math.pi / 2), "PI/2": q(math.pi / 2), "π/2": q(math.pi / 2),
    "QUARTER_PI": q(math.pi / 4), "PI/4": q(math.pi / 4), "π/4": q(math.pi / 4),
    "TAU": q(2 * math.pi), "τ": q(2 * math.pi), "2PI": q(2 * math.pi), "2π": q(2 * math.pi), "2*PI": q(2 * math.pi), "2*π": q(2 * math.pi),
    "INV_PI": q(1 / math.pi), "1/PI": q(1 / math.pi), "1/π": q(1 / math.pi),
    "INV_TAU": q(1 / (2 * math.pi)), "1/TAU": q(1 / (2 * math.pi)), "1/τ": q(1 / (2 * math.pi)),

    "E": q(math.e), "e": q(math.e),
    "INV_E": q(1 / math.e), "1/E": q(1 / math.e), "1/e": q(1 / math.e),
    "LN2": q(math.log(2)), "LN_2": q(math.log(2)),
    "LN10": q(math.log(10)), "LN_10": q(math.log(10)),
    "LOG2E": q(math.log2(math.e)), "LOG2_E": q(math.log2(math.e)),
    "LOG10E": q(math.log10(math.e)), "LOG10_E": q(math.log10(math.e)),

    "SQRT2": q(math.sqrt(2)), "SQRT_2": q(math.sqrt(2)), "√2": q(math.sqrt(2)),
    "SQRT3": q(math.sqrt(3)), "SQRT_3": q(math.sqrt(3)), "√3": q(math.sqrt(3)),
    "SQRT5": q(math.sqrt(5)), "SQRT_5": q(math.sqrt(5)), "√5": q(math.sqrt(5)),
    "INV_SQRT2": q(1 / math.sqrt(2)), "1/SQRT2": q(1 / math.sqrt(2)), "1/√2": q(1 / math.sqrt(2)),

    "PHI": q(golden_ratio()), "φ": q(golden_ratio()), "GOLDEN": q(golden_ratio()), "GOLDEN_RATIO": q(golden_ratio()),
    "SILVER": q(1 + math.sqrt(2)), "SILVER_RATIO": q(1 + math.sqrt(2)),
}

BOOL_CONSTANTS = {"FALSE": 8, "LOW": 8, "TRUE": 9, "HIGH": 9}

MMIO_SYMBOLS = {"UART_TX": 0xF0, "UART_READY": 0x80, "UART_TX_READY": 0x80}
GPIO_ALIASES = {"LED0": 15, "LED1": 16, "LED2": 17, "LED3": 18, "LED4": 19, "LED5": 20}
GPIO_PIN_MAX = 127
GPIO_INPIN_BASE = 64

INSTRUCTION_SUMMARY = [
    "move rd, value                ; rd = value, np. move r0, π / move r1, 1.0 / move r2, √500",
    "move rd, @addr                ; rd = data_mem/MMIO[addr]",
    "move rd, @ra                  ; rd = data_mem[ra]",
    "move @addr, rs|value          ; data_mem/MMIO[addr] = rs albo value przez temp",
    "move @ra, rs|value            ; data_mem[ra] = rs albo value przez temp",
    "move bd, @bool_addr           ; bd = bool/GPIO/MMIO[addr]",
    "move bd, @ra                  ; bd = bool_mem[ra]",
    "move bd, true|false|high|low|bs",
    "move @bool_addr, bs|true|false|high|low",
    "move @ra, bs|true|false|high|low",
    "iadd/isub/imul rd, rs|value, rt|value",
    "fadd/fsub/fmul rd, rs|value, rt|value",
    "iand/ior/ixor rd, rs|value, rt|value",
    "inot/itof/ftoi/fabs rd, rs|value",
    "shl/shr/sar rd, rs|value, amount",
    "band/bor/bxor bd, bs|bool, bt|bool",
    "bnot bd, bs|bool",
    "cmp.eq/cmp.ne/cmp.lt/cmp.le/cmp.gt/cmp.ge bd, rs|value, rt|value",
    "cmp.feq bd, rs|value, rt|value, eps|value   ; macro: abs(rs-rt) <= eps",
    "cadd/csub/cmul zd, zs, zt     ; macro complex fixed-point",
    "cabs2 rd, zs                  ; macro, |z|²",
    "wait rs|cycles",
    "jump label|offset, nop, halt",
]

CONSTANT_SUMMARY = [
    "Values: 123, -7, 0xFF, 0b1010",
    "Fixed decimals: 1.0, -1.5, 0.09375, 4.0",
    "Math symbols: π, τ, φ, e, ½, √2, √3, √5, √500, √0.5",
    "ASCII aliases are still accepted, but examples prefer mathematical symbols",
    "Logs/ratios: ln2, ln10, log2e, log10e, 1/π, 1/τ, 1/√2, silver",
    "Bool values: false/low and true/high. Surowe 0/1 są liczbami word, nie boolami.",
    "Memory/IO: @uart_tx, @uart_ready, @led0, @pin15, @100, @r1",
    "Address-as-value: &uart_tx, &led0, &pin15, &100",
    "Registers: r0..r31; aliases t0..t7 = r24..r31",
    "Complex pairs: z0=r0:r1 ... z11=r22:r23; z12..z15 overlap t0..t7 and are not macro-safe",
]

class AssemblerError(Exception):
    pass


def _norm(token: str) -> str:
    return token.strip().upper()


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
    l = raw.lower()
    if l.startswith("pin"):
        n = int(l[3:])
        if not 0 <= n <= GPIO_PIN_MAX:
            raise AssemblerError(f"pin{n} poza zakresem 0..{GPIO_PIN_MAX}")
        return n
    if l.startswith("inpin"):
        n = int(l[5:])
        if not 0 <= n <= 63:
            raise AssemblerError(f"inpin{n} poza zakresem 0..63")
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
        raise AssemblerError(f"Pusty pierwiastek: {raw}")
    body_s = body.strip()
    if re.fullmatch(r"[-+]?\d+", body_s) or re.fullmatch(r"[-+]?0[xX][0-9a-fA-F]+", body_s) or re.fullmatch(r"[-+]?0[bB][01]+", body_s):
        real = float(int(body_s, 0))
    else:
        value = parse_immediate_raw(body_s)
        signed = value if value < 0x80000000 else value - 0x100000000
        real = signed / Q
    if real < 0:
        raise AssemblerError(f"Pierwiastek z liczby ujemnej: {raw}")
    return to_u32(q(math.sqrt(real)))


def parse_immediate_raw(token: str) -> int:
    raw = token.strip()
    if raw.startswith("#"):
        raise AssemblerError("Sutra v1.3 nie używa # dla immediate; pisz np. move r0, π albo move r0, 123")
    if raw.startswith("@"):
        raise AssemblerError("@ oznacza pamięć/IO; jako wartość adresu użyj &, np. move r0, &uart_tx")
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
    if re.fullmatch(r"[-+]?\d+\.\d+", raw):
        return to_u32(fixed_literal_to_q(raw))
    try:
        return to_u32(parse_plain_int(raw))
    except ValueError:
        raise AssemblerError(f"Nieznana wartość immediate: {raw}")


def parse_immediate(token: str) -> int:
    token = token.strip()
    if not token:
        raise AssemblerError("Puste immediate")
    return parse_immediate_raw(token)


def parse_small_int(token: str) -> int:
    raw = token.strip()
    if raw.startswith("#"):
        raise AssemblerError("Sutra v1.3 nie używa #; pisz np. shl r0, r1, 3")
    return parse_plain_int(raw)


def parse_register(token: str) -> int:
    raw = token.strip()
    u = raw.upper()
    if u in T_REGS:
        return T_REGS[u]
    if not u.startswith("R"):
        raise AssemblerError(f"Oczekiwano rejestru r0..r31 albo t0..t7, dostałem: {raw}")
    try:
        n = int(u[1:])
    except ValueError:
        raise AssemblerError(f"Niepoprawny numer rejestru: {raw}")
    if not 0 <= n <= 31:
        raise AssemblerError(f"r{n} poza zakresem 0..31")
    return n


def parse_complex_register(token: str) -> int:
    raw = token.strip().upper()
    if not raw.startswith("Z"):
        raise AssemblerError(f"Oczekiwano rejestru complex z0..z15, dostałem: {token}")
    try:
        n = int(raw[1:])
    except ValueError:
        raise AssemblerError(f"Niepoprawny numer complex: {token}")
    if not 0 <= n <= 15:
        raise AssemblerError(f"z{n} poza zakresem 0..15")
    return n


def parse_bool_register(token: str) -> int:
    raw = token.strip()
    u = raw.upper()
    if u in BOOL_CONSTANTS:
        return BOOL_CONSTANTS[u]
    if not u.startswith("B"):
        raise AssemblerError(f"Oczekiwano bool b0..b7 albo true/false/high/low, dostałem: {raw}")
    try:
        n = int(u[1:])
    except ValueError:
        raise AssemblerError(f"Niepoprawny numer bool: {raw}")
    if not 0 <= n <= 7:
        raise AssemblerError(f"b{n} poza zakresem 0..7")
    return n


def parse_predicate_register(token: str) -> int:
    raw = token.strip().upper()
    if not raw.startswith("B"):
        raise AssemblerError(f"Predykat używa tylko b0..b7, dostałem: {token}")
    n = int(raw[1:])
    if not 0 <= n <= 7:
        raise AssemblerError(f"Predykat b{n} poza zakresem 0..7")
    return n


def parse_memory_operand(token: str):
    raw = token.strip()
    if raw.startswith("[") or raw.endswith("]"):
        raise AssemblerError("Sutra v1.3 nie używa [adres]; użyj @adres, np. move r0, @10 / move @r1, r0")
    if not raw.startswith("@"):
        raise AssemblerError(f"Adres pamięci/IO musi zaczynać się od @, dostałem: {raw}")
    body = raw[1:].strip()
    if not body:
        raise AssemblerError("Puste @")
    try:
        return ("reg", parse_register(body), None)
    except AssemblerError:
        pass
    u = body.upper()
    if u in MMIO_SYMBOLS:
        domain = "bool" if u in ("UART_READY", "UART_TX_READY") else "word"
        return ("imm", MMIO_SYMBOLS[u], domain)
    if u in GPIO_ALIASES:
        return ("imm", GPIO_ALIASES[u], "bool")
    l = body.lower()
    if l.startswith("pin"):
        n = int(l[3:])
        if not 0 <= n <= GPIO_PIN_MAX:
            raise AssemblerError(f"pin{n} poza zakresem 0..{GPIO_PIN_MAX}")
        return ("imm", n, "bool")
    if l.startswith("inpin"):
        n = int(l[5:])
        if not 0 <= n <= 63:
            raise AssemblerError(f"inpin{n} poza zakresem 0..63")
        return ("imm", GPIO_INPIN_BASE + n, "bool")
    return ("imm", parse_small_int(body), None)



def validate_static_bool_access(addr: int, op: str):
    # Aktualny RTL implementuje bool_mem[0..127]. Adres 128 jest tylko odczytowym UART_READY.
    if op == "load" and addr == MMIO_SYMBOLS["UART_READY"]:
        return
    if 0 <= addr <= GPIO_PIN_MAX:
        return
    raise AssemblerError(
        f"Adres bool @{addr} nie jest zaimplementowany w aktualnym RTL; dostępne są @pin0..@pin127/@led0..@led5"
        + (" oraz odczyt @uart_ready" if op == "load" else "")
    )

def encode_predicate(bool_idx: int, negated: bool = False) -> int:
    pred = (0b1000 if negated else 0) | (bool_idx & 0b111)
    if pred == PRED_ALWAYS:
        raise AssemblerError("Predykat (!b7) koliduje z kodem always; użyj innego b albo odwróć logikę")
    return pred


def parse_predicate_prefix(line: str):
    match = re.match(r"^\(\s*(!?)\s*(B[0-7])\s*\)\s*(.*)$", line, flags=re.IGNORECASE)
    if not match:
        return PRED_ALWAYS, line
    negated = bool(match.group(1))
    bool_idx = parse_predicate_register(match.group(2))
    rest = match.group(3).strip()
    if not rest:
        raise AssemblerError("Predykat bez instrukcji")
    return encode_predicate(bool_idx, negated), rest


def encode_r_format(opcode, rd=0, rs=0, rt=0, funct=0, pred=PRED_ALWAYS):
    return ((opcode & 0x3F) << SHIFT_OPCODE | (rd & 0x1F) << SHIFT_RD | (rs & 0x1F) << SHIFT_RS | (rt & 0x1F) << SHIFT_RT | (funct & 0x7F) << SHIFT_FUNCT | (pred & 0xF))


def encode_i_format(opcode, rd, rs, imm, pred=PRED_ALWAYS):
    signed = imm if imm < 0x80000000 else imm - 0x100000000
    if not -2048 <= signed <= 2047:
        raise AssemblerError(f"Imm {signed} poza zakresem 12-bit signed")
    return ((opcode & 0x3F) << SHIFT_OPCODE | (rd & 0x1F) << SHIFT_RD | (rs & 0x1F) << SHIFT_RS | (signed & 0xFFF) << SHIFT_I_IMM | (pred & 0xF))


def encode_m_format(opcode, rd, rs, pred=PRED_ALWAYS):
    return ((opcode & 0x3F) << SHIFT_OPCODE | (rd & 0x1F) << SHIFT_RD | (rs & 0x1F) << SHIFT_RS | (pred & 0xF))


def encode_md_format(opcode, rd, addr, pred=PRED_ALWAYS):
    if not 0 <= addr <= 0x1FFFF:
        raise AssemblerError(f"Adres {addr} poza zakresem 17-bit direct")
    return ((opcode & 0x3F) << SHIFT_OPCODE | (rd & 0x1F) << SHIFT_RD | (addr & 0x1FFFF) << SHIFT_FUNCT | (pred & 0xF))


def encode_ib_format(opcode, bd, bs, imm14, pred=PRED_ALWAYS):
    if not 0 <= imm14 <= 0x3FFF:
        raise AssemblerError(f"Adres bool {imm14} poza zakresem 0..16383")
    return ((opcode & 0x3F) << SHIFT_OPCODE | (bd & 0xF) << SHIFT_BD | (bs & 0xF) << SHIFT_BS | (imm14 & 0x3FFF) << SHIFT_IB_IMM | (pred & 0xF))


def encode_j_format(opcode, offset, pred=PRED_ALWAYS):
    if not -(1 << 21) <= offset <= (1 << 21) - 1:
        raise AssemblerError(f"Offset {offset} poza zakresem 22-bit signed")
    return ((opcode & 0x3F) << SHIFT_OPCODE | (offset & 0x3FFFFF) << SHIFT_J_OFFSET | (pred & 0xF))


def encode_load_immediate(rd: int, value: int, pred=PRED_ALWAYS):
    signed = value if value < 0x80000000 else value - 0x100000000
    if -2048 <= signed <= 2047:
        return [encode_i_format(OPCODE_LOAD_I, rd, 0, value, pred)]
    first = ((OPCODE_LOAD_L & 0x3F) << SHIFT_OPCODE | (rd & 0x1F) << SHIFT_RD | (pred & 0xF))
    return [first, value & MASK32]


def choose_temp(avoid: set[int]) -> int:
    for t in IMM_TEMPS:
        if t not in avoid:
            return t
    raise AssemblerError("Brak wolnego tymczasowego rejestru t4..t7 dla immediate-makra")


def operand_to_reg(token: str, pre: list[int], avoid: set[int], pred: int) -> int:
    raw = token.strip()
    try:
        return parse_register(raw)
    except AssemblerError:
        pass
    temp = choose_temp(avoid)
    avoid.add(temp)
    pre.extend(encode_load_immediate(temp, parse_immediate(raw), pred))
    return temp


def z_re(z: int) -> int:
    return z * 2


def z_im(z: int) -> int:
    return z * 2 + 1


def ensure_z_macro_safe(z: int, opname: str, operand_name: str):
    if z > 11:
        raise AssemblerError(f"{opname} używa t0..t3 jako scratch, więc {operand_name}=z{z} nie jest bezpieczny; użyj z0..z11")


def ensure_rd_not_scratch(rd: int, opname: str):
    if rd in COMPLEX_SCRATCH:
        raise AssemblerError(f"{opname} używa t0..t3 jako scratch, więc rd nie może być {reg_name(rd)}")


def encode_scalar_alu(m: str, rd: int, rs: int, rt: int, pred: int) -> int:
    return encode_r_format(OPCODE_ALU_R, rd, rs, rt, ALU_R_FUNCTS[m], pred)


def encode_complex_macro(m: str, operands: list[str], pred: int) -> list[int]:
    if m in ("CADD", "CSUB"):
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} wymaga 3 operandów: {m.lower()} zd, zs, zt")
        zd, zs, zt = [parse_complex_register(x) for x in operands]
        for z, name in ((zd, "zd"), (zs, "zs"), (zt, "zt")):
            ensure_z_macro_safe(z, m, name)
        op = "FADD" if m == "CADD" else "FSUB"
        return [encode_scalar_alu(op, z_re(zd), z_re(zs), z_re(zt), pred), encode_scalar_alu(op, z_im(zd), z_im(zs), z_im(zt), pred)]
    if m == "CMUL":
        if len(operands) != 3:
            raise AssemblerError("cmul wymaga 3 operandów: cmul zd, zs, zt")
        zd, zs, zt = [parse_complex_register(x) for x in operands]
        for z, name in ((zd, "zd"), (zs, "zs"), (zt, "zt")):
            ensure_z_macro_safe(z, m, name)
        t0, t1, t2, t3 = COMPLEX_SCRATCH
        return [
            encode_scalar_alu("FMUL", t0, z_re(zs), z_re(zt), pred),
            encode_scalar_alu("FMUL", t1, z_im(zs), z_im(zt), pred),
            encode_scalar_alu("FMUL", t2, z_re(zs), z_im(zt), pred),
            encode_scalar_alu("FMUL", t3, z_im(zs), z_re(zt), pred),
            encode_scalar_alu("FSUB", z_re(zd), t0, t1, pred),
            encode_scalar_alu("FADD", z_im(zd), t2, t3, pred),
        ]
    if m == "CABS2":
        if len(operands) != 2:
            raise AssemblerError("cabs2 wymaga 2 operandów: cabs2 rd, zs")
        rd = parse_register(operands[0])
        zs = parse_complex_register(operands[1])
        ensure_z_macro_safe(zs, m, "zs")
        ensure_rd_not_scratch(rd, m)
        t0, t1 = COMPLEX_SCRATCH[0], COMPLEX_SCRATCH[1]
        return [
            encode_scalar_alu("FMUL", t0, z_re(zs), z_re(zs), pred),
            encode_scalar_alu("FMUL", t1, z_im(zs), z_im(zs), pred),
            encode_scalar_alu("FADD", rd, t0, t1, pred),
        ]
    raise AssemblerError(f"Nieznane macro complex: {m}")


@dataclass
class AssembledLine:
    address: int
    words: list[int]
    source: str
    @property
    def length_words(self):
        return len(self.words)


def assemble_instruction(mnemonic: str, operands: list[str], pred: int = PRED_ALWAYS) -> list[int]:
    m = mnemonic.upper()
    if m == "NOP":
        return [encode_r_format(OPCODE_NOP, pred=pred)]
    if m == "HALT":
        return [encode_r_format(OPCODE_HALT, pred=pred)]
    if m in ("CADD", "CSUB", "CMUL", "CABS2"):
        return encode_complex_macro(m, operands, pred)
    if m in ALU_R_FUNCTS:
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} wymaga 3 operandów")
        rd = parse_register(operands[0])
        pre: list[int] = []
        avoid = {rd}
        rs = operand_to_reg(operands[1], pre, avoid, pred)
        avoid.add(rs)
        rt = operand_to_reg(operands[2], pre, avoid, pred)
        return pre + [encode_r_format(OPCODE_ALU_R, rd, rs, rt, ALU_R_FUNCTS[m], pred)]
    if m in ALU_UNARY_FUNCTS:
        if len(operands) != 2:
            raise AssemblerError(f"{m.lower()} wymaga 2 operandów")
        rd = parse_register(operands[0])
        pre: list[int] = []
        rs = operand_to_reg(operands[1], pre, {rd}, pred)
        return pre + [encode_r_format(OPCODE_ALU_R, rd, rs, 0, ALU_UNARY_FUNCTS[m], pred)]
    if m in SHIFT_FUNCTS:
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} wymaga 3 operandów")
        rd = parse_register(operands[0])
        pre: list[int] = []
        rs = operand_to_reg(operands[1], pre, {rd}, pred)
        shamt = parse_small_int(operands[2])
        if not 0 <= shamt <= 31:
            raise AssemblerError(f"shift amount {shamt} poza zakresem 0..31")
        return pre + [encode_r_format(OPCODE_ALU_R, rd, rs, shamt, SHIFT_FUNCTS[m], pred)]
    if m == "CMP.FEQ":
        if len(operands) != 4:
            raise AssemblerError("cmp.feq wymaga 4 operandów: cmp.feq bd, rs, rt, eps")
        bd = parse_bool_register(operands[0])
        if bd >= 8:
            raise AssemblerError("cmp.feq musi pisać do b0..b7")
        pre: list[int] = []
        avoid: set[int] = set()
        rs = operand_to_reg(operands[1], pre, avoid, pred)
        avoid.add(rs)
        rt = operand_to_reg(operands[2], pre, avoid, pred)
        avoid.add(rt)
        eps = operand_to_reg(operands[3], pre, avoid, pred)
        avoid.add(eps)
        tmp = choose_temp(avoid)
        pre.append(encode_scalar_alu("FSUB", tmp, rs, rt, pred))
        pre.append(encode_r_format(OPCODE_ALU_R, tmp, tmp, 0, FUNCT_FABS, pred))
        pre.append(encode_r_format(OPCODE_CMP_R, bd, tmp, eps, FUNCT_CMP_LE, pred))
        return pre
    if m in CMP_FUNCTS:
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} wymaga 3 operandów")
        bd = parse_bool_register(operands[0])
        if bd >= 8:
            raise AssemblerError("cmp musi pisać do b0..b7")
        pre: list[int] = []
        rs = operand_to_reg(operands[1], pre, set(), pred)
        rt = operand_to_reg(operands[2], pre, {rs}, pred)
        return pre + [encode_r_format(OPCODE_CMP_R, bd, rs, rt, CMP_FUNCTS[m], pred)]
    if m == "MOVE":
        if len(operands) != 2:
            raise AssemblerError("move wymaga 2 operandów: move dst, src")
        dst_raw, src_raw = operands[0].strip(), operands[1].strip()

        # Store: move @addr|@r, source
        if dst_raw.startswith("@"):
            kind, val, domain = parse_memory_operand(dst_raw)
            src_u = src_raw.upper()
            bool_like = src_u.startswith("B") or src_u in BOOL_CONSTANTS
            if bool_like or domain == "bool":
                bs = parse_bool_register(src_raw)
                if kind == "imm":
                    validate_static_bool_access(val, "save")
                    return [encode_ib_format(OPCODE_SAVE_BI, 0, bs, val, pred)]
                return [encode_r_format(OPCODE_SAVE_BR, bs, val, 0, 0, pred)]
            if domain == "bool":
                raise AssemblerError("Do bool/GPIO zapisuj tylko b0..b7 albo true/false/high/low; 0 i 1 są wartościami word")
            pre: list[int] = []
            try:
                rs = parse_register(src_raw)
            except AssemblerError:
                rs = operand_to_reg(src_raw, pre, set(), pred)
            if kind == "imm":
                return pre + [encode_md_format(OPCODE_SAVE_MD, rs, val, pred)]
            return pre + [encode_m_format(OPCODE_SAVE_M, rs, val, pred)]

        # Bool destination: move b0, @addr / move b0, true / move b0, b1
        if dst_raw.upper().startswith("B"):
            bd = parse_bool_register(dst_raw)
            if bd >= 8:
                raise AssemblerError("move do bool musi pisać do b0..b7")
            if src_raw.startswith("@"):
                kind, val, _domain = parse_memory_operand(src_raw)
                if kind == "imm":
                    validate_static_bool_access(val, "load")
                    return [encode_ib_format(OPCODE_LOAD_BI, bd, 0, val, pred)]
                return [encode_r_format(OPCODE_LOAD_BR, bd, val, 0, 0, pred)]
            bs = parse_bool_register(src_raw)
            return [encode_r_format(OPCODE_BOOL_R, bd, bs, 0, FUNCT_BMOV, pred)]

        # Word destination: move r0, @addr / move r0, value / move r0, r1
        rd = parse_register(dst_raw)
        if src_raw.startswith("@"):
            kind, val, _domain = parse_memory_operand(src_raw)
            if kind == "imm":
                return [encode_md_format(OPCODE_LOAD_MD, rd, val, pred)]
            return [encode_m_format(OPCODE_LOAD_M, rd, val, pred)]
        try:
            rs = parse_register(src_raw)
            return [encode_r_format(OPCODE_ALU_R, rd, rs, 0, FUNCT_MOV, pred)]
        except AssemblerError:
            return encode_load_immediate(rd, parse_immediate(src_raw), pred)

    if m in ("LOAD", "SAVE", "BLOAD", "BSAVE"):
        raise AssemblerError(f"{m.lower()} nie istnieje w Sutra v1.3; użyj move dst, src")
    if m in BOOL_R_FUNCTS:
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} wymaga 3 operandów")
        bd = parse_bool_register(operands[0])
        bs = parse_bool_register(operands[1])
        bt = parse_bool_register(operands[2])
        if bd >= 8:
            raise AssemblerError("bool op musi pisać do b0..b7")
        return [encode_r_format(OPCODE_BOOL_R, bd, bs, bt, BOOL_R_FUNCTS[m], pred)]
    if m in BOOL_UNARY_FUNCTS:
        if len(operands) != 2:
            raise AssemblerError(f"{m.lower()} wymaga 2 operandów")
        bd = parse_bool_register(operands[0])
        bs = parse_bool_register(operands[1])
        if bd >= 8:
            raise AssemblerError("bnot musi pisać do b0..b7")
        return [encode_r_format(OPCODE_BOOL_R, bd, bs, 0, BOOL_UNARY_FUNCTS[m], pred)]
    if m == "WAIT":
        if len(operands) != 1:
            raise AssemblerError("wait wymaga 1 operandu")
        pre: list[int] = []
        rs = operand_to_reg(operands[0], pre, set(), pred)
        return pre + [encode_r_format(OPCODE_WAIT, 0, rs, 0, pred=pred)]
    if m in ("JUMP", "JMP"):
        if len(operands) != 1:
            raise AssemblerError("jump wymaga 1 operandu")
        try:
            return [encode_j_format(OPCODE_JUMP, parse_small_int(operands[0]), pred)]
        except Exception:
            raise _LabelReference(OPCODE_JUMP, operands[0], pred)
    raise AssemblerError(f"Nieznany mnemonik: {mnemonic}")


class _LabelReference(Exception):
    def __init__(self, opcode, label, pred=PRED_ALWAYS):
        self.opcode = opcode
        self.label = label
        self.pred = pred


def split_instruction(line: str):
    return line.replace(",", " ").split()


def assemble(source: str) -> list[AssembledLine]:
    raw_lines = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if ";" in line:
            line = line.split(";", 1)[0]
        line = line.strip()
        if line:
            raw_lines.append((lineno, line))
    labels = {}
    pending = []
    address = 0
    for lineno, line in raw_lines:
        if line.endswith(":"):
            label = line[:-1].strip()
            key = label.lower()
            if key in labels:
                raise AssemblerError(f"Linia {lineno}: duplikat etykiety {label}")
            labels[key] = address
            continue
        try:
            pred, instruction_line = parse_predicate_prefix(line)
            parts = split_instruction(instruction_line)
            mnemonic, operands = parts[0], parts[1:]
            try:
                words = assemble_instruction(mnemonic, operands, pred)
                length = len(words)
            except _LabelReference:
                length = 1
            pending.append((address, mnemonic, operands, pred, lineno, line))
            address += length
        except AssemblerError as e:
            raise AssemblerError(f"Linia {lineno}: {e}")
    result = []
    for addr, mnemonic, operands, pred, lineno, line in pending:
        try:
            words = assemble_instruction(mnemonic, operands, pred)
        except _LabelReference as ref:
            key = ref.label.lower()
            if key not in labels:
                raise AssemblerError(f"Linia {lineno}: nieznana etykieta {ref.label}")
            target = labels[key]
            words = [encode_j_format(ref.opcode, target - addr - 1, ref.pred)]
        except AssemblerError as e:
            raise AssemblerError(f"Linia {lineno}: {e}")
        result.append(AssembledLine(address=addr, words=words, source=line))
    return result


def flatten_program(lines: list[AssembledLine]) -> list[int]:
    flat = []
    for line in lines:
        flat.extend(line.words)
    return flat


def reg_name(num: int) -> str:
    if 24 <= num <= 31:
        return f"t{num - 24}"
    return f"r{num}"
