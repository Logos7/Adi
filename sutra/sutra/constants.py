"""Sutra constants for the Agni assembler."""

import math

OPCODE_NOP = 0x00
OPCODE_ALU_R = 0x01
OPCODE_CMP_R = 0x02
OPCODE_LOAD_I = 0x10
OPCODE_LOAD_L = 0x11
OPCODE_LOAD_M = 0x12
OPCODE_SAVE_M = 0x13
OPCODE_LOAD_MD = 0x14
OPCODE_SAVE_MD = 0x15
OPCODE_SAVE_BI = 0x20
OPCODE_LOAD_BI = 0x21
OPCODE_BOOL_R = 0x22
OPCODE_LOAD_BR = 0x23
OPCODE_SAVE_BR = 0x24
OPCODE_WAIT = 0x30
OPCODE_FBCLEAR = 0x31
OPCODE_FBPLOT = 0x32
OPCODE_FBERASE = 0x33
OPCODE_FBPRESENT = 0x34
OPCODE_FBPRESENT1 = 0x35
OPCODE_FBSIZE = 0x36
OPCODE_FBSWAP = 0x37
OPCODE_JUMP = 0x38
OPCODE_CALL = 0x39
OPCODE_RETURN = 0x3A
OPCODE_HALT = 0x3F

FUNCT_IADD = 0x00
FUNCT_ISUB = 0x01
FUNCT_IAND = 0x02
FUNCT_IOR = 0x03
FUNCT_IXOR = 0x04
FUNCT_SHL = 0x05
FUNCT_SHR = 0x06
FUNCT_SAR = 0x07
FUNCT_IMUL = 0x08
FUNCT_FMUL = 0x09
FUNCT_ITOF = 0x0A
FUNCT_FTOI = 0x0B
FUNCT_INOT = 0x0C
FUNCT_FADD = 0x0D
FUNCT_FSUB = 0x0E
FUNCT_FABS = 0x0F
FUNCT_MOV = 0x10
FUNCT_FDIV = 0x11

FUNCT_BAND = 0x00
FUNCT_BOR = 0x01
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
    "IADD": FUNCT_IADD,
    "FADD": FUNCT_FADD,
    "ISUB": FUNCT_ISUB,
    "FSUB": FUNCT_FSUB,
    "IAND": FUNCT_IAND,
    "IOR": FUNCT_IOR,
    "IXOR": FUNCT_IXOR,
    "IMUL": FUNCT_IMUL,
    "FMUL": FUNCT_FMUL,
    "FDIV": FUNCT_FDIV,
}

ALU_UNARY_FUNCTS = {
    "ITOF": FUNCT_ITOF,
    "FTOI": FUNCT_FTOI,
    "INOT": FUNCT_INOT,
    "FABS": FUNCT_FABS,
}

SHIFT_FUNCTS = {
    "SHL": FUNCT_SHL,
    "SHR": FUNCT_SHR,
    "SAR": FUNCT_SAR,
}

BOOL_R_FUNCTS = {
    "BAND": FUNCT_BAND,
    "BOR": FUNCT_BOR,
    "BXOR": FUNCT_BXOR,
}

BOOL_UNARY_FUNCTS = {
    "BNOT": FUNCT_BNOT,
}

CMP_FUNCTS = {
    "CMP.EQ": FUNCT_CMP_EQ,
    "CMP.NE": FUNCT_CMP_NE,
    "CMP.LT": FUNCT_CMP_LT,
    "CMP.LE": FUNCT_CMP_LE,
    "CMP.GT": FUNCT_CMP_GT,
    "CMP.GE": FUNCT_CMP_GE,
}

SHIFT_OPCODE = 26
SHIFT_RD = 21
SHIFT_RS = 16
SHIFT_RT = 11
SHIFT_FUNCT = 4
SHIFT_PRED = 0
SHIFT_I_IMM = 4
SHIFT_BD = 22
SHIFT_BS = 18
SHIFT_IB_IMM = 4
SHIFT_J_OFFSET = 4

PRED_ALWAYS = 0b1111
MASK32 = 0xFFFFFFFF
Q = 1 << 25

DATA_MEM_WORDS = 16384

T_REGS = {f"T{i}": 24 + i for i in range(8)}
COMPLEX_SCRATCH = (24, 25, 26, 27)
IMM_TEMPS = (31, 30, 29, 28)


def q(value: float) -> int:
    return int(round(value * Q))


def golden_ratio() -> float:
    return (1 + math.sqrt(5)) / 2


SCALAR_CONSTANTS = {
    "ZERO": 0,
    "ONE": 1,
    "NEG_ONE": -1,
    "MINUS_ONE": -1,
    "FZERO": 0,
    "F_ZERO": 0,
    "FONE": Q,
    "F_ONE": Q,
    "FNEG_ONE": -Q,
    "F_NEG_ONE": -Q,
    "HALF": Q // 2,
    "½": Q // 2,
    "TWO": 2 * Q,
    "PI": q(math.pi),
    "π": q(math.pi),
    "HALF_PI": q(math.pi / 2),
    "PI/2": q(math.pi / 2),
    "π/2": q(math.pi / 2),
    "QUARTER_PI": q(math.pi / 4),
    "PI/4": q(math.pi / 4),
    "π/4": q(math.pi / 4),
    "TAU": q(2 * math.pi),
    "τ": q(2 * math.pi),
    "2PI": q(2 * math.pi),
    "2π": q(2 * math.pi),
    "2*PI": q(2 * math.pi),
    "2*π": q(2 * math.pi),
    "INV_PI": q(1 / math.pi),
    "1/PI": q(1 / math.pi),
    "1/π": q(1 / math.pi),
    "INV_TAU": q(1 / (2 * math.pi)),
    "1/TAU": q(1 / (2 * math.pi)),
    "1/τ": q(1 / (2 * math.pi)),
    "E": q(math.e),
    "e": q(math.e),
    "INV_E": q(1 / math.e),
    "1/E": q(1 / math.e),
    "1/e": q(1 / math.e),
    "LN2": q(math.log(2)),
    "LN_2": q(math.log(2)),
    "LN10": q(math.log(10)),
    "LN_10": q(math.log(10)),
    "LOG2E": q(math.log2(math.e)),
    "LOG2_E": q(math.log2(math.e)),
    "LOG10E": q(math.log10(math.e)),
    "LOG10_E": q(math.log10(math.e)),
    "SQRT2": q(math.sqrt(2)),
    "SQRT_2": q(math.sqrt(2)),
    "√2": q(math.sqrt(2)),
    "SQRT3": q(math.sqrt(3)),
    "SQRT_3": q(math.sqrt(3)),
    "√3": q(math.sqrt(3)),
    "SQRT5": q(math.sqrt(5)),
    "SQRT_5": q(math.sqrt(5)),
    "√5": q(math.sqrt(5)),
    "INV_SQRT2": q(1 / math.sqrt(2)),
    "1/SQRT2": q(1 / math.sqrt(2)),
    "1/√2": q(1 / math.sqrt(2)),
    "PHI": q(golden_ratio()),
    "φ": q(golden_ratio()),
    "GOLDEN": q(golden_ratio()),
    "GOLDEN_RATIO": q(golden_ratio()),
    "SILVER": q(1 + math.sqrt(2)),
    "SILVER_RATIO": q(1 + math.sqrt(2)),
}

BOOL_CONSTANTS = {
    "FALSE": 8,
    "LOW": 8,
    "TRUE": 9,
    "HIGH": 9,
}

MMIO_SYMBOLS = {
    "UART_TX": 0xF0,
    "UART_RX": 0xF1,
    "UART_READY": 0x80,
    "UART_TX_READY": 0x80,
    "UART_RX_READY": 0x81,

    # HDMI double-buffer control/status bool MMIO.
    # Preferred Sutra spelling uses dotted names, e.g. @hdmi.draw_bank.
    "HDMI.FRAME_TOGGLE": 0x7C,
    "HDMI_FRAME_TOGGLE": 0x7C,

    "HDMI.ACTIVE_BANK": 0x7D,
    "HDMI.FRONT_BANK": 0x7D,
    "HDMI_ACTIVE_BANK": 0x7D,
    "HDMI_FRONT_BANK": 0x7D,

    "HDMI.DRAW_BANK": 0x7E,
    "HDMI_DRAW_BANK": 0x7E,

    "HDMI.REQUEST_BANK": 0x7F,
    "HDMI.REQUEST_FRONT_BANK": 0x7F,
    "HDMI_REQUEST_BANK": 0x7F,
    "HDMI_REQUEST_FRONT_BANK": 0x7F,
}

BOOL_MMIO_SYMBOLS = {
    "UART_READY",
    "UART_TX_READY",
    "UART_RX_READY",
    "HDMI.FRAME_TOGGLE",
    "HDMI_FRAME_TOGGLE",
    "HDMI.ACTIVE_BANK",
    "HDMI.FRONT_BANK",
    "HDMI_ACTIVE_BANK",
    "HDMI_FRONT_BANK",
    "HDMI.DRAW_BANK",
    "HDMI_DRAW_BANK",
    "HDMI.REQUEST_BANK",
    "HDMI.REQUEST_FRONT_BANK",
    "HDMI_REQUEST_BANK",
    "HDMI_REQUEST_FRONT_BANK",
}

GPIO_ALIASES = {
    "LED0": 15,
    "LED1": 16,
    "LED2": 17,
    "LED3": 18,
    "LED4": 19,
    "LED5": 20,
}

GPIO_PIN_MAX = 127
GPIO_INPIN_BASE = 64

DATA_SYMBOLS: dict[str, int] = {}

INSTRUCTION_SUMMARY = [
    "move rd, value ; rd = value, e.g. move r0, π / move r1, 1.0 / move r2, √500",
    "move rd, @addr ; rd = data_mem/MMIO[addr]",
    "move rd, @ra ; rd = data_mem[ra]",
    "move @addr, rs|value ; data_mem/MMIO[addr] = rs or value through a temporary register",
    "move @ra, rs|value ; data_mem[ra] = rs or value through a temporary register",
    "move rd, @ra+offset ; rd = data_mem[ra + offset]",
    "move @ra+offset, rs|value ; data_mem[ra + offset] = rs/value",
    "move bd, @bool_addr ; bd = bool/GPIO/MMIO[addr]",
    "move bd, @ra ; bd = bool_mem[ra]",
    "move bd, true|false|high|low|bs",
    "move @bool_addr, bs|true|false|high|low",
    "move @ra, bs|true|false|high|low",
    "iadd/isub/imul rd, rs|value, rt|value",
    "fadd/fsub/fmul rd, rs|value, rt|value",
    "iand/ior/ixor rd, rs|value, rt|value",
    "inot/itof/ftoi/fabs rd, rs|value",
    "shl/shr/sar rd, rs|value, amount",
    "band/bor/bxor bd, bs|bool, bt|bool",
    "bnot bd, bs",
    "cmp.eq/cmp.ne/cmp.lt/cmp.le/cmp.gt/cmp.ge bd, rs|value, rt|value",
    "cmp.feq bd, rs|value, rt|value, eps|value ; macro: abs(rs-rt) <= eps",
    "cadd/csub/cmul zd, zs, zt ; macro complex fixed-point",
    "cabs2 rd, zs ; macro, |z|²",
    "fbsize width, height ; configure framebuffer width/height for fbclear/fbplot/fbpresent/fbswap",
    "fbclear rBase / fbplot rBase, rX, rY / fberase rBase, rX, rY / fbpresent1 rBase / fbswap",
    "jump_if b0, label / jump_if_not b0, label",
    "beq/bne/blt/ble/bgt/bge rs, rt, label ; macro uses b7",
    "inc/dec/neg/fneg and imin/imax/fmin/fmax",
    "wait_rx / read_rx rd / wait_uart / write_tx rs",
    "wait rs|cycles",
    "jump label|offset, call label|offset, return, nop, halt",
]

CONSTANT_SUMMARY = [
    "Values: 123, -7, 0xFF, 0b1010",
    "Fixed decimals: 1.0, -1.5, 0.09375, 4.0",
    "Math symbols: π, τ, φ, e, ½, √2, √3, √5, √500, √0.5",
    "ASCII aliases are still accepted, but examples prefer mathematical symbols",
    "Logs/ratios: ln2, ln10, log2e, log10e, 1/π, 1/τ, 1/√2, silver",
    "Bool values: false/low and true/high. Raw 0/1 are word numbers, not bool values.",
    "Memory/IO: @uart_tx, @uart_rx, @uart_ready, @hdmi.active_bank, @hdmi.draw_bank, @hdmi.request_bank, @led0, @pin15, @100, @r1, @r1+4",
    "Address-as-value: &uart_tx, &hdmi.draw_bank, &led0, &pin15, &100",
    "Registers: r0..r31; aliases t0..t7 = r24..r31",
    "Complex pairs: z0=r0:r1 ... z11=r22:r23; z12..z15 overlap t0..t7 and are not macro-safe",
]
