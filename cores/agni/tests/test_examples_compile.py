from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sutra import assemble_image
from sutra_expand import IncludeError, expand_file

EXAMPLES = ROOT / "examples"


def test_all_examples_compile():
    files = sorted(EXAMPLES.rglob("*.sutra"))
    assert files

    for path in files:
        try:
            src = expand_file(path)
        except IncludeError as e:
            raise AssertionError(f"{path}: {e}") from e

        image = assemble_image(src)
        assert image.code_words, str(path)


def test_examples_use_safe_uart_tx_macro():
    offenders = []

    for path in sorted(EXAMPLES.rglob("*.sutra")):
        text = path.read_text(encoding="utf-8")
        for no, line in enumerate(text.splitlines(), start=1):
            code = line.split(";", 1)[0].strip().lower()
            if code.startswith("move @uart_tx"):
                offenders.append(f"{path.relative_to(ROOT)}:{no}: {line.strip()}")

    assert offenders == []
