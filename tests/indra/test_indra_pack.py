from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from indra_asm import parse_indra_source
from indra_pack import OP_DENSE, OP_END, RECORD_SIZE, pack_program


def test_pack_program_records_include_shift() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU SHIFT=5
  END

.data
w0:
  .i8 1, -2, 3, -4
b0:
  .i32 10, -20
"""
    )

    packed = pack_program(program)

    assert len(packed.program) == RECORD_SIZE * 2
    dense = packed.program[:RECORD_SIZE]
    end = packed.program[RECORD_SIZE:]

    opcode, input_count, output_count, activation_id, weight_offset, bias_offset, shift, r0, r1, r2 = struct.unpack(
        "<BBBBIIBBBB", dense
    )

    assert opcode == OP_DENSE
    assert input_count == 2
    assert output_count == 2
    assert activation_id == 1
    assert weight_offset == 0
    assert bias_offset == 0
    assert shift == 5
    assert (r0, r1, r2) == (0, 0, 0)
    assert end[0] == OP_END
    assert end[1:] == bytes(15)


def test_pack_signed_data() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 2 1 W=w0 B=b0 ACT=CLAMP
  END

.data
w0:
  .i8 -1, 127
b0:
  .i32 -123456
"""
    )

    packed = pack_program(program)

    assert packed.weights == bytes([0xFF, 0x7F])
    assert packed.biases == struct.pack("<i", -123456)


def test_manifest_contains_shift() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 1 1 W=w0 B=b0 ACT=NONE SHIFT=7
  END

.data
w0:
  .i8 3
b0:
  .i32 4
"""
    )

    packed = pack_program(program)

    assert packed.manifest["layers"][0]["shift"] == 7
    assert packed.manifest["layers"][0]["activation"] == "NONE"
