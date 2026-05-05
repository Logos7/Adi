from __future__ import annotations

import json
import struct

from indra_asm import parse_indra_source
from indra_pack import OP_DENSE, OP_END, pack_program, write_packed


SOURCE = """
brain_bug:
  DENSE 3 2 W=w0 B=b0 ACT=RELU
  DENSE 2 1 W=w1 B=b1 ACT=CLAMP
  END

.data

w0:
  .i8 1, -2, 3, 4, -5, 6

b0:
  .i32 7, -8

w1:
  .i8 9, -10

b1:
  .i32 11
"""


def unpack_record(data: bytes, index: int) -> tuple[int, int, int, int, int, int, int]:
    start = index * 16
    return struct.unpack("<BBBBIII", data[start : start + 16])


def test_pack_program_records() -> None:
    packed = pack_program(parse_indra_source(SOURCE))

    assert len(packed.program_bin) == 48
    assert unpack_record(packed.program_bin, 0) == (OP_DENSE, 1, 3, 2, 0, 0, 0)
    assert unpack_record(packed.program_bin, 1) == (OP_DENSE, 2, 2, 1, 6, 8, 0)
    assert unpack_record(packed.program_bin, 2) == (OP_END, 0, 0, 0, 0, 0, 0)


def test_pack_data_images() -> None:
    packed = pack_program(parse_indra_source(SOURCE))

    assert packed.weights_bin == bytes([1, 254, 3, 4, 251, 6, 9, 246])
    assert packed.biases_bin == struct.pack("<i", 7) + struct.pack("<i", -8) + struct.pack("<i", 11)


def test_manifest() -> None:
    packed = pack_program(parse_indra_source(SOURCE))

    assert packed.manifest["format"] == "indra-v0"
    assert packed.manifest["brain"] == "brain_bug"
    assert packed.manifest["program_bytes"] == 48
    assert packed.manifest["weights_bytes"] == 8
    assert packed.manifest["biases_bytes"] == 12
    assert packed.manifest["layers"][1]["weight_offset"] == 6
    assert packed.manifest["layers"][1]["bias_offset"] == 8


def test_write_packed(tmp_path) -> None:
    source_path = tmp_path / "brain_bug.indra"
    source_path.write_text(SOURCE, encoding="utf-8")
    packed = pack_program(parse_indra_source(SOURCE))

    paths = write_packed(tmp_path / "out", source_path, packed)

    assert paths["program_bin"].read_bytes() == packed.program_bin
    assert paths["weights_bin"].read_bytes() == packed.weights_bin
    assert paths["biases_bin"].read_bytes() == packed.biases_bin
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["brain"] == "brain_bug"
    assert paths["program_hex"].read_text(encoding="utf-8").startswith("01 01 03 02")
