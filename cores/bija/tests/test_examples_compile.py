from pathlib import Path

import pytest

from sutra import assemble, flatten_program


ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "examples" / "bija"


def sutra_examples():
    return sorted(
        path
        for path in EXAMPLES.rglob("*.sutra")
        if path.is_file()
    )


EXAMPLE_FILES = sutra_examples()


def example_id(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=example_id)
def test_sutra_example_assembles(path: Path):
    words = flatten_program(assemble(read(path)))

    assert words


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=example_id)
def test_sutra_example_does_not_write_uart_tx_directly(path: Path):
    offenders = []

    for line_no, line in enumerate(read(path).splitlines(), start=1):
        code = line.split(";", 1)[0].strip().lower()

        if code.startswith("move @uart_tx"):
            offenders.append(f"{line_no}: {line.strip()}")

    assert offenders == [], "\n".join(offenders)


def test_sutra_examples_exist():
    assert EXAMPLE_FILES
