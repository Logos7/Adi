from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from indra_asm import IndraError, parse_indra_source


def test_parse_valid_brain_with_shift() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU SHIFT=3
  DENSE 2 1 W=w1 B=b1 ACT=CLAMP
  END

.data
w0:
  .i8 1, 2, 3, 4
b0:
  .i32 0, 0
w1:
  .i8 5, 6
b1:
  .i32 0
"""
    )

    assert program.name == "brain_test"
    assert len(program.layers) == 2
    assert program.layers[0].shift == 3
    assert program.layers[1].shift == 0


def test_rejects_wrong_weight_count() -> None:
    with pytest.raises(IndraError, match="weights 'w0' have 3 values, expected 4"):
        parse_indra_source(
            """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU
  END

.data
w0:
  .i8 1, 2, 3
b0:
  .i32 0, 0
"""
        )


def test_rejects_wrong_bias_count() -> None:
    with pytest.raises(IndraError, match="biases 'b0' have 1 values, expected 2"):
        parse_indra_source(
            """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU
  END

.data
w0:
  .i8 1, 2, 3, 4
b0:
  .i32 0
"""
        )


def test_rejects_layer_size_mismatch() -> None:
    with pytest.raises(IndraError, match="does not match previous output"):
        parse_indra_source(
            """
brain_test:
  DENSE 2 3 W=w0 B=b0 ACT=RELU
  DENSE 2 1 W=w1 B=b1 ACT=CLAMP
  END

.data
w0:
  .i8 1, 2, 3, 4, 5, 6
b0:
  .i32 0, 0, 0
w1:
  .i8 1, 2
b1:
  .i32 0
"""
        )


def test_rejects_invalid_shift() -> None:
    with pytest.raises(IndraError, match="SHIFT=32"):
        parse_indra_source(
            """
brain_test:
  DENSE 2 1 W=w0 B=b0 ACT=CLAMP SHIFT=32
  END

.data
w0:
  .i8 1, 2
b0:
  .i32 0
"""
        )


def test_rejects_i8_range() -> None:
    with pytest.raises(IndraError, match="outside -128..127"):
        parse_indra_source(
            """
brain_test:
  DENSE 1 1 W=w0 B=b0 ACT=CLAMP
  END

.data
w0:
  .i8 200
b0:
  .i32 0
"""
        )
