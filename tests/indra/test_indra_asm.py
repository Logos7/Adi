from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import pytest

from indra_asm import IndraAsmError, format_report, parse_text


VALID_BRAIN = """
brain_bug:
  DENSE 4 3 W=bug_w0 B=bug_b0 ACT=RELU
  DENSE 3 2 W=bug_w1 B=bug_b1 ACT=CLAMP
  END

.data

bug_w0:
  .i8 1, 2, 3, 4
  .i8 5, 6, 7, 8
  .i8 9, 10, 11, 12

bug_b0:
  .i32 0, 1, -1

bug_w1:
  .i8 1, 2, 3
  .i8 4, 5, 6

bug_b1:
  .i32 0, 0
"""


def test_parse_valid_brain() -> None:
    parsed = parse_text(VALID_BRAIN)

    assert parsed.brain.name == "brain_bug"
    assert len(parsed.brain.layers) == 2
    assert parsed.brain.layers[0].input_count == 4
    assert parsed.brain.layers[0].output_count == 3
    assert parsed.brain.layers[1].input_count == 3
    assert parsed.brain.layers[1].output_count == 2
    assert len(parsed.data["bug_w0"].values) == 12
    assert len(parsed.data["bug_b0"].values) == 3


def test_report_contains_expected_layer_summary() -> None:
    parsed = parse_text(VALID_BRAIN)
    report = format_report(parsed)

    assert "Brain: brain_bug" in report
    assert "Layer 0: DENSE 4 -> 3" in report
    assert "W=bug_w0 12/12" in report
    assert "B=bug_b0 3/3" in report
    assert report.endswith("OK")


def test_rejects_wrong_weight_count() -> None:
    source = VALID_BRAIN.replace(".i8 9, 10, 11, 12", ".i8 9, 10, 11")

    with pytest.raises(IndraAsmError, match="weight block 'bug_w0' has 11 values, expected 12"):
        parse_text(source)


def test_rejects_wrong_bias_count() -> None:
    source = VALID_BRAIN.replace("bug_b1:\n  .i32 0, 0", "bug_b1:\n  .i32 0")

    with pytest.raises(IndraAsmError, match="bias block 'bug_b1' has 1 values, expected 2"):
        parse_text(source)


def test_rejects_unsupported_activation() -> None:
    source = VALID_BRAIN.replace("ACT=RELU", "ACT=TANH", 1)

    with pytest.raises(IndraAsmError, match="unsupported activation 'TANH'"):
        parse_text(source)


def test_rejects_layer_width_mismatch() -> None:
    source = VALID_BRAIN.replace("DENSE 3 2", "DENSE 4 2")

    with pytest.raises(IndraAsmError, match="does not match previous output count"):
        parse_text(source)


def test_rejects_i8_out_of_range() -> None:
    source = VALID_BRAIN.replace(".i8 1, 2, 3, 4", ".i8 1, 2, 3, 128")

    with pytest.raises(IndraAsmError, match=".i8 value out of range"):
        parse_text(source)


def test_supports_semicolon_and_hash_comments() -> None:
    source = """
# file comment
brain_tiny:
  DENSE 2 1 W=w0 B=b0 ACT=SIGN ; layer comment
  END

.data

w0:
  .i8 1, -1 # data comment

b0:
  .i32 0
"""
    parsed = parse_text(source)

    assert parsed.brain.name == "brain_tiny"
    assert parsed.brain.layers[0].activation == "SIGN"
