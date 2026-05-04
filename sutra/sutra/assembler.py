"""Sutra instruction assembler."""

from dataclasses import dataclass

from .constants import *
from .errors import AssemblerError, _LabelReference
from .parsing import *
from .encoding import *
from .macros import expand_macro_line


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

    if m == "RETURN":
        if len(operands) != 0:
            raise AssemblerError("return does not take operands")
        return [encode_r_format(OPCODE_RETURN, pred=pred)]

    if m == "FBCLEAR":
        if len(operands) != 1:
            raise AssemblerError("fbclear requires 1 operand: fbclear rBase")
        base = parse_register(operands[0])
        return [encode_r_format(OPCODE_FBCLEAR, base, 0, 0, 0, pred)]

    if m in ("FBPRESENT", "FBPRESENT1"):
        if len(operands) != 1:
            raise AssemblerError(f"{m.lower()} requires 1 operand: {m.lower()} rBase")
        base = parse_register(operands[0])
        opcode = OPCODE_FBPRESENT if m == "FBPRESENT" else OPCODE_FBPRESENT1
        return [encode_r_format(opcode, base, 0, 0, 0, pred)]

    if m in ("FBPLOT", "FBERASE"):
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} requires 3 operands: {m.lower()} rBase, rX, rY")
        base = parse_register(operands[0])
        x = parse_register(operands[1])
        y = parse_register(operands[2])
        opcode = OPCODE_FBPLOT if m == "FBPLOT" else OPCODE_FBERASE
        return [encode_r_format(opcode, base, x, y, 0, pred)]

    if m in ("CADD", "CSUB", "CMUL", "CABS2"):
        return encode_complex_macro(m, operands, pred)

    if m in ("IMIN", "IMAX", "FMIN", "FMAX"):
        return encode_minmax_macro(m, operands, pred)

    if m in ALU_R_FUNCTS:
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} requires 3 operands")
        rd = parse_register(operands[0])
        pre: list[int] = []
        avoid = {rd}
        rs = operand_to_reg(operands[1], pre, avoid, pred)
        avoid.add(rs)
        rt = operand_to_reg(operands[2], pre, avoid, pred)
        return pre + [encode_r_format(OPCODE_ALU_R, rd, rs, rt, ALU_R_FUNCTS[m], pred)]

    if m in ALU_UNARY_FUNCTS:
        if len(operands) != 2:
            raise AssemblerError(f"{m.lower()} requires 2 operands")
        rd = parse_register(operands[0])
        pre: list[int] = []
        rs = operand_to_reg(operands[1], pre, {rd}, pred)
        return pre + [encode_r_format(OPCODE_ALU_R, rd, rs, 0, ALU_UNARY_FUNCTS[m], pred)]

    if m in SHIFT_FUNCTS:
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} requires 3 operands")
        rd = parse_register(operands[0])
        pre: list[int] = []
        rs = operand_to_reg(operands[1], pre, {rd}, pred)
        shamt = parse_small_int(operands[2])
        if not 0 <= shamt <= 31:
            raise AssemblerError(f"shift amount {shamt} is out of range 0..31")
        return pre + [encode_r_format(OPCODE_ALU_R, rd, rs, shamt, SHIFT_FUNCTS[m], pred)]

    if m == "CMP.FEQ":
        if len(operands) != 4:
            raise AssemblerError("cmp.feq requires 4 operands: cmp.feq bd, rs, rt, eps")
        bd = parse_bool_register(operands[0])
        if bd >= 8:
            raise AssemblerError("cmp.feq must write to b0..b7")
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
            raise AssemblerError(f"{m.lower()} requires 3 operands")
        bd = parse_bool_register(operands[0])
        if bd >= 8:
            raise AssemblerError("cmp must write to b0..b7")
        pre: list[int] = []
        rs = operand_to_reg(operands[1], pre, set(), pred)
        rt = operand_to_reg(operands[2], pre, {rs}, pred)
        return pre + [encode_r_format(OPCODE_CMP_R, bd, rs, rt, CMP_FUNCTS[m], pred)]

    if m == "MOVE":
        if len(operands) != 2:
            raise AssemblerError("move requires 2 operands: move dst, src")

        dst_raw, src_raw = operands[0].strip(), operands[1].strip()

        if dst_raw.startswith("@"):
            kind, val, domain, offset = parse_memory_operand(dst_raw)
            src_u = src_raw.upper()
            bool_like = src_u.startswith("B") or src_u in BOOL_CONSTANTS

            if bool_like or domain == "bool":
                bs = parse_bool_register(src_raw)
                if kind == "imm":
                    validate_static_bool_access(val, "save")
                    return [encode_ib_format(OPCODE_SAVE_BI, 0, bs, val, pred)]
                if offset != 0:
                    raise AssemblerError("bool @r+offset is not supported yet")
                return [encode_r_format(OPCODE_SAVE_BR, bs, val, 0, 0, pred)]

            if domain == "bool":
                raise AssemblerError("For bool/GPIO writes, use only b0..b7 or true/false/high/low; 0 and 1 are word values")

            pre: list[int] = []
            try:
                rs = parse_register(src_raw)
            except AssemblerError:
                rs = operand_to_reg(src_raw, pre, set(), pred)

            if kind == "imm":
                return pre + [encode_md_format(OPCODE_SAVE_MD, rs, val, pred)]
            return pre + [encode_m_format(OPCODE_SAVE_M, rs, val, offset, pred)]

        if dst_raw.upper().startswith("B"):
            bd = parse_bool_register(dst_raw)
            if bd >= 8:
                raise AssemblerError("move to bool must write to b0..b7")

            if src_raw.startswith("@"):
                kind, val, _domain, offset = parse_memory_operand(src_raw)
                if kind == "imm":
                    validate_static_bool_access(val, "load")
                    return [encode_ib_format(OPCODE_LOAD_BI, bd, 0, val, pred)]
                if offset != 0:
                    raise AssemblerError("bool @r+offset is not supported yet")
                return [encode_r_format(OPCODE_LOAD_BR, bd, val, 0, 0, pred)]

            bs = parse_bool_register(src_raw)
            return [encode_r_format(OPCODE_BOOL_R, bd, bs, 0, FUNCT_BMOV, pred)]

        rd = parse_register(dst_raw)

        if src_raw.startswith("@"):
            kind, val, _domain, offset = parse_memory_operand(src_raw)
            if kind == "imm":
                return [encode_md_format(OPCODE_LOAD_MD, rd, val, pred)]
            return [encode_m_format(OPCODE_LOAD_M, rd, val, offset, pred)]

        try:
            rs = parse_register(src_raw)
            return [encode_r_format(OPCODE_ALU_R, rd, rs, 0, FUNCT_MOV, pred)]
        except AssemblerError:
            return encode_load_immediate(rd, parse_immediate(src_raw), pred)

    if m in ("LOAD", "SAVE", "BLOAD", "BSAVE"):
        raise AssemblerError(f"{m.lower()} does not exist in Sutra v1.6; use move dst, src")

    if m in BOOL_R_FUNCTS:
        if len(operands) != 3:
            raise AssemblerError(f"{m.lower()} requires 3 operands")
        bd = parse_bool_register(operands[0])
        bs = parse_bool_register(operands[1])
        bt = parse_bool_register(operands[2])
        if bd >= 8:
            raise AssemblerError("bool op must write to b0..b7")
        return [encode_r_format(OPCODE_BOOL_R, bd, bs, bt, BOOL_R_FUNCTS[m], pred)]

    if m in BOOL_UNARY_FUNCTS:
        if len(operands) != 2:
            raise AssemblerError(f"{m.lower()} requires 2 operands")
        bd = parse_bool_register(operands[0])
        bs = parse_bool_register(operands[1])
        if bd >= 8:
            raise AssemblerError("bnot must write to b0..b7")
        return [encode_r_format(OPCODE_BOOL_R, bd, bs, 0, BOOL_UNARY_FUNCTS[m], pred)]

    if m == "WAIT":
        if len(operands) != 1:
            raise AssemblerError("wait requires 1 operand")
        pre: list[int] = []
        rs = operand_to_reg(operands[0], pre, set(), pred)
        return pre + [encode_r_format(OPCODE_WAIT, 0, rs, 0, pred=pred)]

    if m in ("JUMP", "JMP"):
        if len(operands) != 1:
            raise AssemblerError("jump requires 1 operand")
        try:
            return [encode_j_format(OPCODE_JUMP, parse_small_int(operands[0]), pred)]
        except Exception:
            raise _LabelReference(OPCODE_JUMP, operands[0], pred)

    if m == "CALL":
        if len(operands) != 1:
            raise AssemblerError("call requires 1 operand")
        try:
            return [encode_j_format(OPCODE_CALL, parse_small_int(operands[0]), pred)]
        except Exception:
            raise _LabelReference(OPCODE_CALL, operands[0], pred)

    raise AssemblerError(f"Unknown mnemonic: {mnemonic}")


def split_instruction(line: str):
    return line.replace(",", " ").split()


def _strip_comment(line: str) -> str:
    if ";" in line:
        line = line.split(";", 1)[0]
    return line.strip()


def _prepare_lines(source: str):
    raw_lines = []
    macro_counter = 0

    for lineno, line in enumerate(source.splitlines(), start=1):
        line = _strip_comment(line)
        if not line:
            continue

        try:
            expanded, macro_counter = expand_macro_line(line, macro_counter)
        except AssemblerError as e:
            raise AssemblerError(f"Line {lineno}: {e}")

        for expanded_line in expanded:
            expanded_line = expanded_line.strip()
            if expanded_line:
                raw_lines.append((lineno, expanded_line))

    return raw_lines


def _instruction_length(mnemonic: str, operands: list[str], pred: int, lineno: int) -> int:
    try:
        return len(assemble_instruction(mnemonic, operands, pred))
    except _LabelReference:
        return 1
    except AssemblerError:
        raise


def _parse_instruction_line(line: str):
    pred, instruction_line = parse_predicate_prefix(line)
    parts = split_instruction(instruction_line)
    if not parts:
        raise AssemblerError("Empty instruction")
    return pred, parts[0], parts[1:]


def assemble(source: str) -> list[AssembledLine]:
    raw_lines = _prepare_lines(source)

    labels: dict[str, int] = {}
    program_lines = []
    address = 0

    for lineno, line in raw_lines:
        if line.endswith(":"):
            label = line[:-1].strip()
            key = label.lower()
            if key in labels:
                raise AssemblerError(f"Line {lineno}: duplicate label {label}")
            labels[key] = address
            continue

        try:
            pred, mnemonic, operands = _parse_instruction_line(line)
            length = _instruction_length(mnemonic, operands, pred, lineno)
        except AssemblerError as e:
            raise AssemblerError(f"Line {lineno}: {e}")

        program_lines.append((address, mnemonic, operands, pred, lineno, line))
        address += length

    result: list[AssembledLine] = []

    for addr, mnemonic, operands, pred, lineno, line in program_lines:
        try:
            words = assemble_instruction(mnemonic, operands, pred)
        except _LabelReference as ref:
            key = ref.label.lower()
            if key not in labels:
                raise AssemblerError(f"Line {lineno}: unknown label {ref.label}")
            target = labels[key]
            words = [encode_j_format(ref.opcode, target - addr - 1, ref.pred)]
        except AssemblerError as e:
            raise AssemblerError(f"Line {lineno}: {e}")

        result.append(AssembledLine(address=addr, words=words, source=line))

    return result


def flatten_program(lines: list[AssembledLine]) -> list[int]:
    flat = []
    for line in lines:
        flat.extend(line.words)
    return flat

