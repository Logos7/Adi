from pathlib import Path

import pytest
from sutra import assemble, assemble_image, flatten_program

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "examples" / "bija"


def sutra_examples() -> list[Path]:
    return sorted(path for path in EXAMPLES.rglob("*.sutra") if path.is_file())


EXAMPLE_FILES = sutra_examples()


def example_id(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=example_id)
def test_sutra_example_assembles_legacy_code_path(path: Path) -> None:
    words = flatten_program(assemble(read(path)))
    assert words


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=example_id)
def test_sutra_example_builds_v15_code_data_image(path: Path) -> None:
    image = assemble_image(read(path))
    assert image.code_words
    assert isinstance(image.code_words, list)
    assert isinstance(image.data_words, list)


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=example_id)
def test_sutra_example_does_not_write_uart_tx_directly(path: Path) -> None:
    offenders: list[str] = []

    for line_no, line in enumerate(read(path).splitlines(), start=1):
        code = line.split(";", 1)[0].strip().lower()
        if code.startswith("move @uart_tx"):
            offenders.append(f"{line_no}: {line.strip()}")

    assert offenders == [], "\n".join(offenders)


def test_sutra_examples_exist() -> None:
    assert EXAMPLE_FILES


def test_v15_org_gap_is_preserved_in_data_image() -> None:
    source = """
.data
    .org 4
marker:
    .word 123

.code
main:
    move r0, marker
"""

    image = assemble_image(source)

    assert image.code_words
    assert len(image.data_words) >= 5
    assert image.data_words[0:4] == [0, 0, 0, 0]
    assert image.data_words[4] == 123


def test_wire_cube_fine_adi1_uses_expected_v15_data_layout() -> None:
    path = EXAMPLES / "graphics_3d" / "wire_cube_fine_adi1.sutra"
    source = read(path)
    image = assemble_image(source)

    code_without_comments = "\n".join(
        line.split(";", 1)[0] for line in source.splitlines()
    )

    assert image.code_words
    assert len(image.data_words) >= 272
    assert any(word != 0 for word in image.data_words[0:256])
    assert image.data_words[256:272] == [0] * 16
    assert ".org 274" in source
    assert "frame_tick:" in source
    assert "@frame_tick" in source
    assert "@274" not in code_without_comments
