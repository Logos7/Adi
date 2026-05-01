"""Brahma-Bija v1.4 — prosty symulator CPU."""

from dataclasses import dataclass, field

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

ALU_FUNCT_NAMES = {
    FUNCT_IADD: "iadd",
    FUNCT_FADD: "fadd",
    FUNCT_ISUB: "isub",
    FUNCT_FSUB: "fsub",
    FUNCT_IAND: "iand",
    FUNCT_IOR: "ior",
    FUNCT_IXOR: "ixor",
    FUNCT_INOT: "inot",
    FUNCT_IMUL: "imul",
    FUNCT_FMUL: "fmul",
    FUNCT_FDIV: "fdiv",
    FUNCT_ITOF: "itof",
    FUNCT_FTOI: "ftoi",
    FUNCT_SHL: "shl",
    FUNCT_SHR: "shr",
    FUNCT_SAR: "sar",
    FUNCT_FABS: "fabs",
    FUNCT_MOV: "move",
}

CMP_FUNCT_NAMES = {
    FUNCT_CMP_EQ: "cmp.eq",
    FUNCT_CMP_NE: "cmp.ne",
    FUNCT_CMP_LT: "cmp.lt",
    FUNCT_CMP_LE: "cmp.le",
    FUNCT_CMP_GT: "cmp.gt",
    FUNCT_CMP_GE: "cmp.ge",
}

BOOL_FUNCT_NAMES = {
    FUNCT_BAND: "band",
    FUNCT_BOR: "bor",
    FUNCT_BXOR: "bxor",
    FUNCT_BNOT: "bnot",
    FUNCT_BMOV: "move",
}

MASK32 = 0xFFFFFFFF
DATA_MEM_SIZE = 512
UART_TX_ADDR = 0xF0
UART_RX_ADDR = 0xF1
UART_READY_BOOL_ADDR = 0x80
UART_RX_READY_BOOL_ADDR = 0x81
BOOL_GPIO_PIN_BASE = 0
BOOL_GPIO_PIN_COUNT = 128
RETURN_STACK_DEPTH = 16


def field_opcode(word):
    return (word >> 26) & 0x3F


def field_pred(word):
    return word & 0xF


def field_rd(word):
    return (word >> 21) & 0x1F


def field_rs(word):
    return (word >> 16) & 0x1F


def field_rt(word):
    return (word >> 11) & 0x1F


def field_funct(word):
    return (word >> 4) & 0x7F


def field_md_imm(word):
    return (word >> 4) & 0x1FFFF


def field_i_imm(word):
    raw = (word >> 4) & 0xFFF
    if raw & 0x800:
        raw -= 0x1000
    return raw


def field_ib_bd(word):
    return (word >> 22) & 0xF


def field_ib_bs(word):
    return (word >> 18) & 0xF


def field_ib_imm(word):
    return (word >> 4) & 0x3FFF


def field_j_offset(word):
    raw = (word >> 4) & 0x3FFFFF
    if raw & 0x200000:
        raw -= 0x400000
    return raw


def to_signed32(value: int) -> int:
    value &= MASK32
    if value & 0x80000000:
        value -= 0x100000000
    return value


def fmul_q7_25(a: int, b: int) -> int:
    return (to_signed32(a) * to_signed32(b)) >> 25


def fdiv_q7_25(a: int, b: int) -> int:
    sa = to_signed32(a)
    sb = to_signed32(b)
    if sb == 0:
        raise ZeroDivisionError("fdiv by zero")
    q = (abs(sa) << 25) // abs(sb)
    if (sa < 0) ^ (sb < 0):
        if q > 0x80000000:
            raise OverflowError("fdiv overflow")
        return (-q) & MASK32
    if q > 0x7FFFFFFF:
        raise OverflowError("fdiv overflow")
    return q & MASK32


def reg_name(num: int) -> str:
    if 24 <= num <= 31:
        return f"t{num - 24}"
    return f"r{num}"


def bool_name(num: int) -> str:
    if num == 8:
        return "false"
    if num == 9:
        return "true"
    return f"b{num}"


def format_predicate(pred: int) -> str:
    if pred == 0b1111:
        return ""
    idx = pred & 0b111
    neg = (pred >> 3) & 1
    return f"(!b{idx}) " if neg else f"(b{idx}) "


@dataclass
class CPU:
    gpr: list[int] = field(default_factory=lambda: [0] * 32)
    bool_regs: list[int] = field(default_factory=lambda: [0] * 8)
    pc: int = 0
    imem: list[int] = field(default_factory=list)
    data_mem: list[int] = field(default_factory=lambda: [0] * DATA_MEM_SIZE)
    bool_mem: list[int] = field(default_factory=lambda: [0] * 128)
    halted: bool = False
    cycle_count: int = 0
    wait_remaining: int = 0
    gpio_listeners: list = field(default_factory=list)
    uart_tx_bytes: list[int] = field(default_factory=list)
    uart_tx_ready: int = 1
    uart_rx_bytes: list[int] = field(default_factory=list)
    uart_rx_ready: int = 0
    uart_rx_data: int = 0
    return_stack: list[int] = field(default_factory=lambda: [0] * RETURN_STACK_DEPTH)
    return_sp: int = 0

    def read_register(self, num: int) -> int:
        if 0 <= num <= 31:
            return self.gpr[num]
        raise RuntimeError(f"Niepoprawny numer rejestru: {num}")

    def write_register(self, num: int, value: int):
        if 0 <= num <= 31:
            self.gpr[num] = value & MASK32
            return
        raise RuntimeError(f"Niepoprawny numer rejestru do zapisu: {num}")

    def read_bool(self, num: int) -> int:
        if 0 <= num <= 7:
            return self.bool_regs[num]
        if num == 8:
            return 0
        if num == 9:
            return 1
        raise RuntimeError(f"Niepoprawny numer bool: {num}")

    def write_bool(self, num: int, value: int):
        if 0 <= num <= 7:
            self.bool_regs[num] = value & 1
            return
        raise RuntimeError(f"Niepoprawny numer bool do zapisu: {num}")

    def read_data_mem(self, addr: int) -> int:
        addr8 = addr & 0x1FF
        if addr8 == UART_RX_ADDR:
            value = self.uart_rx_data & 0xFF
            self.uart_rx_ready = 0
            return value
        return self.data_mem[addr8]

    def write_data_mem(self, addr: int, value: int):
        addr8 = addr & 0x1FF
        if addr8 == UART_TX_ADDR:
            self.uart_tx_bytes.append(value & 0xFF)
            return
        self.data_mem[addr8] = value & MASK32

    def read_bool_mem(self, addr: int) -> int:
        if addr == UART_READY_BOOL_ADDR:
            return self.uart_tx_ready & 1
        if addr == UART_RX_READY_BOOL_ADDR:
            return self.uart_rx_ready & 1
        if not 0 <= addr < len(self.bool_mem):
            raise RuntimeError(f"Adres bool poza zakresem: {addr}")
        return self.bool_mem[addr]

    def write_bool_mem(self, addr: int, value: int):
        if not 0 <= addr < len(self.bool_mem):
            raise RuntimeError(f"Adres bool poza zakresem: {addr}")

        old = self.bool_mem[addr]
        new = value & 1
        self.bool_mem[addr] = new

        if BOOL_GPIO_PIN_BASE <= addr < BOOL_GPIO_PIN_BASE + BOOL_GPIO_PIN_COUNT and old != new:
            for listener in self.gpio_listeners:
                listener(addr - BOOL_GPIO_PIN_BASE, new, self.cycle_count)

    def push_uart_rx(self, value: int):
        self.uart_rx_data = value & 0xFF
        self.uart_rx_ready = 1
        self.uart_rx_bytes.append(value & 0xFF)

    def load_program(self, words: list[int], start: int = 0):
        end = start + len(words)
        if len(self.imem) < end:
            self.imem.extend([0] * (end - len(self.imem)))

        for i, w in enumerate(words):
            self.imem[start + i] = w & MASK32

        self.pc = start
        self.halted = False
        self.wait_remaining = 0
        self.return_sp = 0
        self.return_stack = [0] * RETURN_STACK_DEPTH

    def check_predicate(self, pred: int) -> bool:
        if pred == 0b1111:
            return True
        idx = pred & 0b111
        neg = (pred >> 3) & 1
        return self.bool_regs[idx] == (0 if neg else 1)

    def step(self):
        if self.halted:
            return

        if self.wait_remaining > 0:
            self.wait_remaining -= 1
            self.cycle_count += 1
            return

        if self.pc >= len(self.imem):
            self.halted = True
            return

        word = self.imem[self.pc]
        opcode = field_opcode(word)
        pred = field_pred(word)

        if not self.check_predicate(pred):
            self.pc += 2 if opcode == OPCODE_LOAD_L else 1
            self.cycle_count += 1
            return

        if opcode == OPCODE_NOP:
            self.pc += 1
        elif opcode == OPCODE_HALT:
            self.halted = True
        elif opcode == OPCODE_ALU_R:
            self._exec_alu_r(word)
            self.pc += 1
        elif opcode == OPCODE_CMP_R:
            self._exec_cmp_r(word)
            self.pc += 1
        elif opcode == OPCODE_LOAD_I:
            self.write_register(field_rd(word), field_i_imm(word))
            self.pc += 1
        elif opcode == OPCODE_LOAD_L:
            self.write_register(field_rd(word), self.imem[self.pc + 1])
            self.pc += 2
        elif opcode == OPCODE_LOAD_M:
            self.write_register(field_rd(word), self.read_data_mem(self.read_register(field_rs(word)) + field_i_imm(word)))
            self.pc += 1
        elif opcode == OPCODE_SAVE_M:
            addr = self.read_register(field_rs(word)) + field_i_imm(word)
            if (addr & 0x1FF) == UART_TX_ADDR and not self.uart_tx_ready:
                self.cycle_count += 1
                return
            self.write_data_mem(addr, self.read_register(field_rd(word)))
            self.pc += 1
        elif opcode == OPCODE_LOAD_MD:
            self.write_register(field_rd(word), self.read_data_mem(field_md_imm(word)))
            self.pc += 1
        elif opcode == OPCODE_SAVE_MD:
            addr = field_md_imm(word)
            if (addr & 0x1FF) == UART_TX_ADDR and not self.uart_tx_ready:
                self.cycle_count += 1
                return
            self.write_data_mem(addr, self.read_register(field_rd(word)))
            self.pc += 1
        elif opcode == OPCODE_LOAD_BI:
            self.write_bool(field_ib_bd(word), self.read_bool_mem(field_ib_imm(word)))
            self.pc += 1
        elif opcode == OPCODE_SAVE_BI:
            self.write_bool_mem(field_ib_imm(word), self.read_bool(field_ib_bs(word)))
            self.pc += 1
        elif opcode == OPCODE_LOAD_BR:
            self.write_bool(field_rd(word), self.read_bool_mem(self.read_register(field_rs(word)) & 0x3FFF))
            self.pc += 1
        elif opcode == OPCODE_SAVE_BR:
            self.write_bool_mem(self.read_register(field_rs(word)) & 0x3FFF, self.read_bool(field_rd(word) & 0xF))
            self.pc += 1
        elif opcode == OPCODE_BOOL_R:
            self._exec_bool_r(word)
            self.pc += 1
        elif opcode == OPCODE_WAIT:
            self.wait_remaining = self.read_register(field_rs(word))
            self.pc += 1
        elif opcode == OPCODE_FBCLEAR:
            base = self.read_register(field_rd(word)) & 0x1FF
            for i in range(128):
                self.data_mem[(base + i) & 0x1FF] = 0
            self.pc += 1
        elif opcode == OPCODE_FBPLOT or opcode == OPCODE_FBERASE:
            base = self.read_register(field_rd(word)) & 0x1FF
            x = self.read_register(field_rs(word))
            y = self.read_register(field_rt(word))
            if 0 <= x < 64 and 0 <= y < 64:
                pixel = (y << 6) + x
                addr = (base + (pixel >> 5)) & 0x1FF
                mask = 1 << (pixel & 31)
                if opcode == OPCODE_FBPLOT:
                    self.data_mem[addr] = (self.data_mem[addr] | mask) & MASK32
                else:
                    self.data_mem[addr] = (self.data_mem[addr] & ~mask) & MASK32
            self.pc += 1
        elif opcode == OPCODE_FBPRESENT:
            base = self.read_register(field_rd(word)) & 0x1FF
            self.uart_tx_bytes.extend([65, 68, 73, 48, 64, 64])
            for word_index in range(128):
                w = self.data_mem[(base + word_index) & 0x1FF]
                for bit in range(32):
                    self.uart_tx_bytes.append(48 if (w >> bit) & 1 else 0)
            self.pc += 1
        elif opcode == OPCODE_JUMP:
            self.pc += 1 + field_j_offset(word)
        elif opcode == OPCODE_CALL:
            if self.return_sp >= RETURN_STACK_DEPTH:
                self.halted = True
            else:
                self.return_stack[self.return_sp] = self.pc + 1
                self.return_sp += 1
                self.pc += 1 + field_j_offset(word)
        elif opcode == OPCODE_RETURN:
            if self.return_sp <= 0:
                self.halted = True
            else:
                self.return_sp -= 1
                self.pc = self.return_stack[self.return_sp]
        else:
            raise RuntimeError(f"Nieznany opcode {opcode:#x} przy pc={self.pc}")

        self.cycle_count += 1

    def _exec_alu_r(self, word):
        funct, rd, rs, rt = field_funct(word), field_rd(word), field_rs(word), field_rt(word)
        a, b = self.read_register(rs), self.read_register(rt)
        sh = rt & 0x1F

        if funct == FUNCT_IADD or funct == FUNCT_FADD:
            result = a + b
        elif funct == FUNCT_ISUB or funct == FUNCT_FSUB:
            result = a - b
        elif funct == FUNCT_IAND:
            result = a & b
        elif funct == FUNCT_IOR:
            result = a | b
        elif funct == FUNCT_IXOR:
            result = a ^ b
        elif funct == FUNCT_INOT:
            result = ~a
        elif funct == FUNCT_IMUL:
            result = to_signed32(a) * to_signed32(b)
        elif funct == FUNCT_FMUL:
            result = fmul_q7_25(a, b)
        elif funct == FUNCT_FDIV:
            result = fdiv_q7_25(a, b)
        elif funct == FUNCT_ITOF:
            result = to_signed32(a) << 25
        elif funct == FUNCT_FTOI:
            result = to_signed32(a) >> 25
        elif funct == FUNCT_FABS:
            result = -to_signed32(a) if to_signed32(a) < 0 else to_signed32(a)
        elif funct == FUNCT_MOV:
            result = a
        elif funct == FUNCT_SHL:
            result = a << sh
        elif funct == FUNCT_SHR:
            result = a >> sh
        elif funct == FUNCT_SAR:
            result = to_signed32(a) >> sh
        else:
            raise RuntimeError(f"Nieznany funct {funct:#x} dla ALU")

        self.write_register(rd, result)

    def _exec_bool_r(self, word):
        funct, bd, bs, bt = field_funct(word), field_rd(word), field_rs(word), field_rt(word)
        a, b = self.read_bool(bs), self.read_bool(bt)

        if funct == FUNCT_BAND:
            result = a & b
        elif funct == FUNCT_BOR:
            result = a | b
        elif funct == FUNCT_BXOR:
            result = a ^ b
        elif funct == FUNCT_BNOT:
            result = 1 - a
        elif funct == FUNCT_BMOV:
            result = a
        else:
            raise RuntimeError(f"Nieznany funct {funct:#x} dla BOOL")

        self.write_bool(bd, result)

    def _exec_cmp_r(self, word):
        funct, bd, rs, rt = field_funct(word), field_rd(word), field_rs(word), field_rt(word)
        a, b = self.read_register(rs), self.read_register(rt)
        sa, sb = to_signed32(a), to_signed32(b)

        if funct == FUNCT_CMP_EQ:
            result = a == b
        elif funct == FUNCT_CMP_NE:
            result = a != b
        elif funct == FUNCT_CMP_LT:
            result = sa < sb
        elif funct == FUNCT_CMP_LE:
            result = sa <= sb
        elif funct == FUNCT_CMP_GT:
            result = sa > sb
        elif funct == FUNCT_CMP_GE:
            result = sa >= sb
        else:
            raise RuntimeError(f"Nieznany funct {funct:#x} dla CMP")

        self.write_bool(bd, 1 if result else 0)

    def run(self, max_cycles: int = 1_000_000):
        for _ in range(max_cycles):
            if self.halted:
                break
            self.step()

    def dump_state(self):
        lines = [f"PC = {self.pc} (cycle = {self.cycle_count}, return_sp = {self.return_sp})"]
        for i, v in enumerate(self.gpr):
            lines.append(f"{reg_name(i):<3} = 0x{v:08x} ({v})")
        lines.append("Bool: " + " ".join(f"b{i}={v}" for i, v in enumerate(self.bool_regs)))
        return "\n".join(lines)


def disassemble(word: int, second_word: int = None) -> str:
    opcode = field_opcode(word)
    pred = format_predicate(field_pred(word))

    if opcode == OPCODE_NOP:
        return pred + "nop"
    if opcode == OPCODE_HALT:
        return pred + "halt"

    if opcode == OPCODE_ALU_R:
        name = ALU_FUNCT_NAMES.get(field_funct(word), f"alu.{field_funct(word):x}")
        if name in ("shl", "shr", "sar"):
            return f"{pred}{name} {reg_name(field_rd(word))}, {reg_name(field_rs(word))}, {field_rt(word)}"
        if name == "move":
            return f"{pred}move {reg_name(field_rd(word))}, {reg_name(field_rs(word))}"
        if name in ("itof", "ftoi", "inot", "fabs"):
            return f"{pred}{name} {reg_name(field_rd(word))}, {reg_name(field_rs(word))}"
        return f"{pred}{name} {reg_name(field_rd(word))}, {reg_name(field_rs(word))}, {reg_name(field_rt(word))}"

    if opcode == OPCODE_CMP_R:
        name = CMP_FUNCT_NAMES.get(field_funct(word), f"cmp.{field_funct(word):x}")
        return f"{pred}{name} b{field_rd(word)}, {reg_name(field_rs(word))}, {reg_name(field_rt(word))}"

    if opcode == OPCODE_LOAD_I:
        return f"{pred}move {reg_name(field_rd(word))}, {field_i_imm(word)}"

    if opcode == OPCODE_LOAD_L:
        if second_word is None:
            return f"{pred}move {reg_name(field_rd(word))}, <literal>"
        return f"{pred}move {reg_name(field_rd(word))}, 0x{second_word:08x}"

    if opcode == OPCODE_LOAD_M:
        off = field_i_imm(word)
        suffix = "" if off == 0 else (f"+{off}" if off > 0 else str(off))
        return f"{pred}move {reg_name(field_rd(word))}, @{reg_name(field_rs(word))}{suffix}"

    if opcode == OPCODE_SAVE_M:
        off = field_i_imm(word)
        suffix = "" if off == 0 else (f"+{off}" if off > 0 else str(off))
        return f"{pred}move @{reg_name(field_rs(word))}{suffix}, {reg_name(field_rd(word))}"

    if opcode == OPCODE_LOAD_MD:
        return f"{pred}move {reg_name(field_rd(word))}, @{field_md_imm(word)}"

    if opcode == OPCODE_SAVE_MD:
        return f"{pred}move @{field_md_imm(word)}, {reg_name(field_rd(word))}"

    if opcode == OPCODE_LOAD_BI:
        return f"{pred}move b{field_ib_bd(word)}, @{field_ib_imm(word)}"

    if opcode == OPCODE_SAVE_BI:
        return f"{pred}move @{field_ib_imm(word)}, {bool_name(field_ib_bs(word))}"

    if opcode == OPCODE_LOAD_BR:
        return f"{pred}move b{field_rd(word)}, @{reg_name(field_rs(word))}"

    if opcode == OPCODE_SAVE_BR:
        return f"{pred}move @{reg_name(field_rs(word))}, {bool_name(field_rd(word) & 0xF)}"

    if opcode == OPCODE_BOOL_R:
        name = BOOL_FUNCT_NAMES.get(field_funct(word), f"bool.{field_funct(word):x}")
        if name == "bnot":
            return f"{pred}bnot {bool_name(field_rd(word))}, {bool_name(field_rs(word))}"
        if name == "move":
            return f"{pred}move {bool_name(field_rd(word))}, {bool_name(field_rs(word))}"
        return f"{pred}{name} {bool_name(field_rd(word))}, {bool_name(field_rs(word))}, {bool_name(field_rt(word))}"

    if opcode == OPCODE_WAIT:
        return f"{pred}wait {reg_name(field_rs(word))}"

    if opcode == OPCODE_FBCLEAR:
        return f"{pred}fbclear {reg_name(field_rd(word))}"

    if opcode == OPCODE_FBPLOT:
        return f"{pred}fbplot {reg_name(field_rd(word))}, {reg_name(field_rs(word))}, {reg_name(field_rt(word))}"

    if opcode == OPCODE_FBERASE:
        return f"{pred}fberase {reg_name(field_rd(word))}, {reg_name(field_rs(word))}, {reg_name(field_rt(word))}"

    if opcode == OPCODE_FBPRESENT:
        return f"{pred}fbpresent {reg_name(field_rd(word))}"

    if opcode == OPCODE_JUMP:
        return f"{pred}jump {field_j_offset(word):+d}"

    if opcode == OPCODE_CALL:
        return f"{pred}call {field_j_offset(word):+d}"

    if opcode == OPCODE_RETURN:
        return f"{pred}return"

    return f"{pred}.word 0x{word:08x}"
