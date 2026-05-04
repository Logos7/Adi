"""Instruction encoding helpers and encoded assembler macros."""

from .constants import *
from .errors import AssemblerError
from .parsing import (
    encode_predicate,
    parse_bool_register,
    parse_complex_register,
    parse_immediate,
    parse_register,
)


def validate_static_bool_access(addr: int, op: str):
    if op == "load" and addr in (MMIO_SYMBOLS["UART_READY"], MMIO_SYMBOLS["UART_RX_READY"]):
        return

    if 0 <= addr <= GPIO_PIN_MAX:
        return

    extra = " and reads from @uart_ready/@uart_rx_ready" if op == "load" else ""
    raise AssemblerError(
        f"Bool address @{addr} is not implemented in the current RTL; available addresses are @pin0..@pin127/@led0..@led5{extra}"
    )

def encode_r_format(opcode, rd=0, rs=0, rt=0, funct=0, pred=PRED_ALWAYS):
    return (
        ((opcode & 0x3F) << SHIFT_OPCODE)
        | ((rd & 0x1F) << SHIFT_RD)
        | ((rs & 0x1F) << SHIFT_RS)
        | ((rt & 0x1F) << SHIFT_RT)
        | ((funct & 0x7F) << SHIFT_FUNCT)
        | ((pred & 0xF) << SHIFT_PRED)
    )


def encode_i_format(opcode, rd, rs, imm, pred=PRED_ALWAYS):
    signed = imm if imm < 0x80000000 else imm - 0x100000000
    if not -2048 <= signed <= 2047:
        raise AssemblerError(f"Immediate {signed} is outside the signed 12-bit range")
    return (
        ((opcode & 0x3F) << SHIFT_OPCODE)
        | ((rd & 0x1F) << SHIFT_RD)
        | ((rs & 0x1F) << SHIFT_RS)
        | ((signed & 0xFFF) << SHIFT_I_IMM)
        | (pred & 0xF)
    )


def encode_m_format(opcode, rd, rs, imm=0, pred=PRED_ALWAYS):
    signed = imm if imm < 0x80000000 else imm - 0x100000000
    if not -2048 <= signed <= 2047:
        raise AssemblerError(f"Offset {signed} is outside the signed 12-bit range")
    return (
        ((opcode & 0x3F) << SHIFT_OPCODE)
        | ((rd & 0x1F) << SHIFT_RD)
        | ((rs & 0x1F) << SHIFT_RS)
        | ((signed & 0xFFF) << SHIFT_I_IMM)
        | (pred & 0xF)
    )


def encode_md_format(opcode, rd, addr, pred=PRED_ALWAYS):
    if not 0 <= addr <= 0x1FFFF:
        raise AssemblerError(f"Address {addr} is outside the 17-bit direct range")
    return (
        ((opcode & 0x3F) << SHIFT_OPCODE)
        | ((rd & 0x1F) << SHIFT_RD)
        | ((addr & 0x1FFFF) << SHIFT_FUNCT)
        | (pred & 0xF)
    )


def encode_ib_format(opcode, bd, bs, imm14, pred=PRED_ALWAYS):
    if not 0 <= imm14 <= 0x3FFF:
        raise AssemblerError(f"Bool address {imm14} is outside the 0..16383 range")
    return (
        ((opcode & 0x3F) << SHIFT_OPCODE)
        | ((bd & 0xF) << SHIFT_BD)
        | ((bs & 0xF) << SHIFT_BS)
        | ((imm14 & 0x3FFF) << SHIFT_IB_IMM)
        | (pred & 0xF)
    )


def encode_j_format(opcode, offset, pred=PRED_ALWAYS):
    if not -(1 << 21) <= offset <= (1 << 21) - 1:
        raise AssemblerError(f"Offset {offset} is outside the signed 22-bit range")
    return (
        ((opcode & 0x3F) << SHIFT_OPCODE)
        | ((offset & 0x3FFFFF) << SHIFT_J_OFFSET)
        | (pred & 0xF)
    )


def encode_load_immediate(rd: int, value: int, pred=PRED_ALWAYS):
    signed = value if value < 0x80000000 else value - 0x100000000
    if -2048 <= signed <= 2047:
        return [encode_i_format(OPCODE_LOAD_I, rd, 0, value, pred)]

    first = ((OPCODE_LOAD_L & 0x3F) << SHIFT_OPCODE) | ((rd & 0x1F) << SHIFT_RD) | (pred & 0xF)
    return [first, value & MASK32]


def choose_temp(avoid: set[int]) -> int:
    for t in IMM_TEMPS:
        if t not in avoid:
            return t
    raise AssemblerError("No free temporary register t4..t7 is available for the immediate macro")


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


def reg_name(num: int) -> str:
    if 24 <= num <= 31:
        return f"t{num - 24}"
    return f"r{num}"


def ensure_z_macro_safe(z: int, opname: str, operand_name: str):
    if z > 11:
        raise AssemblerError(f"{opname.lower()} uses t0..t3 as scratch registers, so {operand_name}=z{z} is not safe; use z0..z11")


def ensure_rd_not_scratch(rd: int, opname: str):
    if rd in COMPLEX_SCRATCH:
        raise AssemblerError(f"{opname.lower()} uses t0..t3 as scratch registers, so rd cannot be {reg_name(rd)}")


def encode_scalar_alu(m: str, rd: int, rs: int, rt: int, pred: int) -> int:
    return encode_r_format(OPCODE_ALU_R, rd, rs, rt, ALU_R_FUNCTS[m], pred)


def encode_complex_macro(m: str, operands: list[str], pred: int) -> list[int]:
    if m in ("CADD", "CSUB"):
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} requires 3 operands: {m.lower()} zd, zs, zt")
        zd, zs, zt = [parse_complex_register(x) for x in operands]
        for z, name in ((zd, "zd"), (zs, "zs"), (zt, "zt")):
            ensure_z_macro_safe(z, m, name)
        op = "FADD" if m == "CADD" else "FSUB"
        return [
            encode_scalar_alu(op, z_re(zd), z_re(zs), z_re(zt), pred),
            encode_scalar_alu(op, z_im(zd), z_im(zs), z_im(zt), pred),
        ]

    if m == "CMUL":
        if len(operands) != 3:
            raise AssemblerError("cmul requires 3 operands: cmul zd, zs, zt")
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
            raise AssemblerError("cabs2 requires 2 operands: cabs2 rd, zs")
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

    raise AssemblerError(f"Unknown complex macro: {m}")


def encode_minmax_macro(m: str, operands: list[str], pred: int) -> list[int]:
    if len(operands) != 3:
        raise AssemblerError(f"{m.lower()} requires 3 operands: {m.lower()} rd, a, b")

    rd = parse_register(operands[0])
    pre: list[int] = []
    avoid = {rd}

    a = operand_to_reg(operands[1], pre, avoid, pred)
    avoid.add(a)
    b = operand_to_reg(operands[2], pre, avoid, pred)
    avoid.add(b)

    cmp_b = b
    save_b: list[int] = []
    if rd == b:
        tmp = choose_temp(avoid)
        avoid.add(tmp)
        save_b.append(encode_r_format(OPCODE_ALU_R, tmp, b, 0, FUNCT_MOV, pred))
        cmp_b = tmp

    cmp_fun = FUNCT_CMP_GT if m in ("IMIN", "FMIN") else FUNCT_CMP_LT
    return pre + save_b + [
        encode_r_format(OPCODE_CMP_R, 7, a, cmp_b, cmp_fun, pred),
        encode_r_format(OPCODE_ALU_R, rd, a, 0, FUNCT_MOV, pred),
        encode_r_format(OPCODE_ALU_R, rd, cmp_b, 0, FUNCT_MOV, encode_predicate(7, False)),
    ]

