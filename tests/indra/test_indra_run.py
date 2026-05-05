from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from indra_asm import IndraError, parse_indra_source
from indra_run import run_program


def test_run_dense_with_shift_and_clamp() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU SHIFT=1
  DENSE 2 1 W=w1 B=b1 ACT=CLAMP SHIFT=2
  END

.data
w0:
  .i8 4, -2, 3, 1
b0:
  .i32 0, 0
w1:
  .i8 2, -4
b1:
  .i32 0
"""
    )

    result = run_program(program, [10, 6])

    assert result.layer_outputs[0] == [14, 18]
    assert result.layer_outputs[1] == [-11]
    assert result.output == [-11]


def test_run_sign_activation() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=SIGN SHIFT=0
  END

.data
w0:
  .i8 1, 1, -1, -1
b0:
  .i32 0, 0
"""
    )

    result = run_program(program, [10, -2])
    assert result.output == [127, -127]


def test_rejects_wrong_input_count() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 2 1 W=w0 B=b0 ACT=CLAMP
  END

.data
w0:
  .i8 1, 2
b0:
  .i32 0
"""
    )

    with pytest.raises(IndraError, match="expects 2 inputs"):
        run_program(program, [1])


def test_rejects_input_outside_i8() -> None:
    program = parse_indra_source(
        """
brain_test:
  DENSE 1 1 W=w0 B=b0 ACT=CLAMP
  END

.data
w0:
  .i8 1
b0:
  .i32 0
"""
    )

    with pytest.raises(IndraError, match="outside -128..127"):
        run_program(program, [200])
