from __future__ import annotations

import pytest

from tools.indra_asm import DEFAULT_SHIFT, IndraError, parse_text


def test_parse_valid_brain_with_explicit_shift() -> None:
    source = """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU SHIFT=7
  END

.data

w0:
  .i8 1, 2, 3, 4

b0:
  .i32 0, 0
"""

    assembly = parse_text(source)

    assert assembly.brain.name == "brain_test"
    assert len(assembly.brain.layers) == 1
    assert assembly.brain.layers[0].input_count == 2
    assert assembly.brain.layers[0].output_count == 2
    assert assembly.brain.layers[0].activation == "RELU"
    assert assembly.brain.layers[0].shift == 7


def test_default_shift_is_7() -> None:
    source = """
brain_test:
  DENSE 2 1 W=w0 B=b0 ACT=CLAMP
  END

.data

w0:
  .i8 1, 2

b0:
  .i32 0
"""

    assembly = parse_text(source)

    assert assembly.brain.layers[0].shift == DEFAULT_SHIFT


def test_rejects_wrong_weight_count() -> None:
    source = """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU
  END

.data

w0:
  .i8 1, 2, 3

b0:
  .i32 0, 0
"""

    with pytest.raises(IndraError, match="weight label"):
        parse_text(source)


def test_rejects_wrong_bias_count() -> None:
    source = """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=RELU
  END

.data

w0:
  .i8 1, 2, 3, 4

b0:
  .i32 0
"""

    with pytest.raises(IndraError, match="bias label"):
        parse_text(source)


def test_rejects_unknown_activation() -> None:
    source = """
brain_test:
  DENSE 2 1 W=w0 B=b0 ACT=BOUNCE
  END

.data

w0:
  .i8 1, 2

b0:
  .i32 0
"""

    with pytest.raises(IndraError, match="unknown activation"):
        parse_text(source)
