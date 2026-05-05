from __future__ import annotations

import json

from tools.indra_pack import OP_DENSE, OP_END, pack_to_directory


def test_pack_writes_expected_files(tmp_path) -> None:
    source = tmp_path / "brain_test.indra"
    source.write_text(
        """
brain_test:
  DENSE 2 1 W=w0 B=b0 ACT=CLAMP SHIFT=7
  END

.data

w0:
  .i8 64, -64

b0:
  .i32 0
""",
        encoding="utf-8",
    )

    paths = pack_to_directory(source, tmp_path / "out")

    assert set(paths) == {
        "program_bin",
        "weights_bin",
        "biases_bin",
        "program_hex",
        "weights_hex",
        "biases_hex",
        "manifest",
    }

    program = (tmp_path / "out" / "brain_test.program.bin").read_bytes()
    weights = (tmp_path / "out" / "brain_test.weights.bin").read_bytes()
    biases = (tmp_path / "out" / "brain_test.biases.bin").read_bytes()
    manifest = json.loads((tmp_path / "out" / "brain_test.manifest.json").read_text(encoding="utf-8"))

    assert program[0] == OP_DENSE
    assert program[1] == 2
    assert program[2] == 1
    assert program[3] == 2
    assert program[4] == 7
    assert program[-1] == OP_END
    assert weights == bytes([64, 192])
    assert biases == bytes([0, 0, 0, 0])
    assert manifest["numeric"]["int8_scale"] == "1/128"
    assert manifest["numeric"]["accumulator_scale"] == "1/16384"
    assert manifest["numeric"]["default_shift"] == 7
