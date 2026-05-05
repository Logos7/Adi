from __future__ import annotations

import pytest

from indra_asm import IndraAsmError, parse_indra_source
from indra_run import apply_activation, format_result, run_program


SOURCE = """
brain_bug:
  DENSE 3 2 W=w0 B=b0 ACT=CLAMP
  DENSE 2 1 W=w1 B=b1 ACT=RELU
  END

.data

w0:
  .i8 1, 2, 3
  .i8 -1, 1, 0

b0:
  .i32 0, 10

w1:
  .i8 4, -5

b1:
  .i32 -3
"""


def test_run_program() -> None:
    program = parse_indra_source(SOURCE)

    result = run_program(program, [10, -2, 3])

    assert result.brain_name == "brain_bug"
    assert result.layer_outputs[0] == (15, -2)
    assert result.output_vector == (67,)


def test_format_result() -> None:
    program = parse_indra_source(SOURCE)
    result = run_program(program, [10, -2, 3])

    text = format_result(result, show_layers=True)

    assert "Brain: brain_bug" in text
    assert "Input:  10 -2 3" in text
    assert "Layer 0: 15 -2" in text
    assert "Output: 67" in text


def test_relu_saturates_to_int8() -> None:
    assert apply_activation(200, "RELU") == 127
    assert apply_activation(-50, "RELU") == 0


def test_clamp_saturates_to_int8() -> None:
    assert apply_activation(200, "CLAMP") == 127
    assert apply_activation(-200, "CLAMP") == -128


def test_sign_activation() -> None:
    assert apply_activation(5, "SIGN") == 127
    assert apply_activation(0, "SIGN") == 127
    assert apply_activation(-5, "SIGN") == -127


def test_rejects_wrong_input_count() -> None:
    program = parse_indra_source(SOURCE)

    with pytest.raises(IndraAsmError, match="expects 3 inputs"):
        run_program(program, [1, 2])


def test_rejects_input_outside_int8_range() -> None:
    program = parse_indra_source(SOURCE)

    with pytest.raises(IndraAsmError, match="outside int8 range"):
        run_program(program, [1, 2, 128])
