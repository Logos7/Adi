from __future__ import annotations

import pytest

from indra_asm import IndraAsmError, format_report, parse_indra_source


BUG_SOURCE = """
brain_bug:
  DENSE 3 2 W=bug_w0 B=bug_b0 ACT=RELU
  DENSE 2 1 W=bug_w1 B=bug_b1 ACT=CLAMP
  END

.data

bug_w0:
  .i8 1, 2, 3
  .i8 4, 5, 6

bug_b0:
  .i32 0, 1

bug_w1:
  .i8 7, 8

bug_b1:
  .i32 -1
"""


def test_parse_valid_brain() -> None:
    program = parse_indra_source(BUG_SOURCE)

    assert program.name == "brain_bug"
    assert len(program.layers) == 2
    assert program.layers[0].input_count == 3
    assert program.layers[0].output_count == 2
    assert program.layers[0].activation == "RELU"
    assert program.data["bug_w0"].values == (1, 2, 3, 4, 5, 6)
    assert program.data["bug_b1"].values == (-1,)


def test_format_report() -> None:
    program = parse_indra_source(BUG_SOURCE)
    report = format_report(program)

    assert "Brain: brain_bug" in report
    assert "Layer 0: DENSE 3 -> 2" in report
    assert "weights=6/6" in report
    assert report.endswith("OK")


def test_rejects_missing_end() -> None:
    source = """
brain_bug:
  DENSE 3 2 W=w B=b ACT=RELU
.data
w:
  .i8 1, 2, 3, 4, 5, 6
b:
  .i32 0, 0
"""
    with pytest.raises(IndraAsmError, match="before END"):
        parse_indra_source(source)


def test_rejects_missing_weight_block() -> None:
    source = """
brain_bug:
  DENSE 3 2 W=w B=b ACT=RELU
  END
.data
b:
  .i32 0, 0
"""
    with pytest.raises(IndraAsmError, match="missing weight block"):
        parse_indra_source(source)


def test_rejects_wrong_weight_count() -> None:
    source = """
brain_bug:
  DENSE 3 2 W=w B=b ACT=RELU
  END
.data
w:
  .i8 1, 2, 3
b:
  .i32 0, 0
"""
    with pytest.raises(IndraAsmError, match="expects 6 weights"):
        parse_indra_source(source)


def test_rejects_wrong_bias_count() -> None:
    source = """
brain_bug:
  DENSE 3 2 W=w B=b ACT=RELU
  END
.data
w:
  .i8 1, 2, 3, 4, 5, 6
b:
  .i32 0
"""
    with pytest.raises(IndraAsmError, match="expects 2 biases"):
        parse_indra_source(source)


def test_rejects_i8_overflow() -> None:
    source = """
brain_bug:
  DENSE 1 1 W=w B=b ACT=RELU
  END
.data
w:
  .i8 128
b:
  .i32 0
"""
    with pytest.raises(IndraAsmError, match="outside i8 range"):
        parse_indra_source(source)


def test_rejects_unknown_activation() -> None:
    source = """
brain_bug:
  DENSE 1 1 W=w B=b ACT=GELU
  END
.data
w:
  .i8 1
b:
  .i32 0
"""
    with pytest.raises(IndraAsmError, match="unsupported activation"):
        parse_indra_source(source)
