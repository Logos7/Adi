from __future__ import annotations

from tools.indra_asm import parse_text
from tools.indra_run import activate, run, saturate_i8


def test_saturate_i8() -> None:
    assert saturate_i8(-200) == -128
    assert saturate_i8(-128) == -128
    assert saturate_i8(0) == 0
    assert saturate_i8(127) == 127
    assert saturate_i8(200) == 127


def test_activations() -> None:
    assert activate(-10, "NONE") == -10
    assert activate(200, "NONE") == 127
    assert activate(-10, "RELU") == 0
    assert activate(10, "RELU") == 10
    assert activate(-200, "CLAMP") == -128
    assert activate(200, "CLAMP") == 127
    assert activate(-1, "SIGN") == -127
    assert activate(0, "SIGN") == 127


def test_run_q07_identity_like_layer() -> None:
    source = """
brain_test:
  DENSE 2 2 W=w0 B=b0 ACT=CLAMP SHIFT=7
  END

.data

w0:
  .i8 127, 0
  .i8 0, 127

b0:
  .i32 0, 0
"""

    assembly = parse_text(source)
    outputs, layers = run(assembly, [64, -64])

    assert outputs == [63, -64]
    assert layers == [[63, -64]]
