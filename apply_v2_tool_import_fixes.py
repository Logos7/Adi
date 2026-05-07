#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
if not (ROOT / "tools").exists():
    ROOT = Path.cwd()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old in text:
        p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
        print(f"updated: {path}")
    elif new in text:
        print(f"already ok: {path}")
    else:
        print(f"warning: pattern not found in {path}")


def replace_all(path: str, replacements: list[tuple[str, str]]) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != original:
        p.write_text(text, encoding="utf-8", newline="\n")
        print(f"updated: {path}")
    else:
        print(f"already ok or unchanged: {path}")


# tools/sutra/sutra_expand.py moved from tools/ to tools/sutra/.
# Its repository root moved from parents[1] to parents[2].
replace_all(
    "tools/sutra/sutra_expand.py",
    [
        (
            "ROOT = Path(__file__).resolve().parents[1]",
            "ROOT = Path(__file__).resolve().parents[2]",
        ),
    ],
)

# tools/sutra/sutra2hex.py moved from tools/ to tools/sutra/.
# Fix repo root and import sutra_expand from the local package module.
replace_all(
    "tools/sutra/sutra2hex.py",
    [
        (
            'ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))',
            'ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))',
        ),
        (
            "from sutra_expand import IncludeError, expand_file",
            "try:\n    from .sutra_expand import IncludeError, expand_file\nexcept ImportError:\n    from sutra_expand import IncludeError, expand_file",
        ),
    ],
)

# tools/agni/upload_sutra.py moved from tools/ to tools/agni/.
# Fix repo root and import Sutra include expander from tools.sutra.
replace_all(
    "tools/agni/upload_sutra.py",
    [
        (
            'ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))',
            'ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))',
        ),
        (
            "try:\n    from sutra_expand import IncludeError, expand_file\nexcept Exception:\n    IncludeError = Exception\n    expand_file = None",
            "try:\n    from tools.sutra.sutra_expand import IncludeError, expand_file\nexcept ModuleNotFoundError:\n    sys.path.insert(0, ROOT)\n    from tools.sutra.sutra_expand import IncludeError, expand_file\nexcept Exception:\n    IncludeError = Exception\n    expand_file = None",
        ),
        (
            "try:\n from sutra_expand import IncludeError, expand_file\n\nexcept Exception:\n\n IncludeError = Exception\n\n expand_file = None",
            "try:\n from tools.sutra.sutra_expand import IncludeError, expand_file\n\nexcept ModuleNotFoundError:\n\n sys.path.insert(0, ROOT)\n\n from tools.sutra.sutra_expand import IncludeError, expand_file\n\nexcept Exception:\n\n IncludeError = Exception\n\n expand_file = None",
        ),
    ],
)

# tools/agni helpers now need to import the moved uploader.
replace_all(
    "tools/agni/program_upload.py",
    [
        (
            "from sutra_upload import assemble_file, upload_words",
            "try:\n    from tools.agni.upload_sutra import assemble_file, upload_words\nexcept ModuleNotFoundError:\n    from upload_sutra import assemble_file, upload_words",
        ),
    ],
)

replace_all(
    "tools/agni/uart_terminal_core.py",
    [
        (
            "from sutra_upload import ACK_ERR, ACK_OK, ACK_READY",
            "try:\n    from tools.agni.upload_sutra import ACK_ERR, ACK_OK, ACK_READY\nexcept ModuleNotFoundError:\n    from upload_sutra import ACK_ERR, ACK_OK, ACK_READY",
        ),
    ],
)

# Indra tools moved from root tools/*.py to tools/indra/*.py.
replace_all(
    "tools/indra/pack.py",
    [
        ("from .indra_asm import ACTIVATIONS, Assembly, parse_file", "from .parse import ACTIVATIONS, Assembly, parse_file"),
        ("from indra_asm import ACTIVATIONS, Assembly, parse_file", "from parse import ACTIVATIONS, Assembly, parse_file"),
    ],
)

replace_all(
    "tools/indra/run.py",
    [
        ("from .indra_asm import Assembly, IndraError, parse_file", "from .parse import Assembly, IndraError, parse_file"),
        ("from indra_asm import Assembly, IndraError, parse_file", "from parse import Assembly, IndraError, parse_file"),
    ],
)

# Tests should import the new package locations.
for path in [
    "tests/indra/test_indra_asm.py",
    "tests/indra/test_indra_parse.py",
]:
    if (ROOT / path).exists():
        replace_all(
            path,
            [
                ("from tools.indra_asm import", "from tools.indra.parse import"),
            ],
        )

replace_all(
    "tests/indra/test_indra_pack.py",
    [
        ("from tools.indra_pack import", "from tools.indra.pack import"),
    ],
)

replace_all(
    "tests/indra/test_indra_run.py",
    [
        ("from tools.indra_asm import", "from tools.indra.parse import"),
        ("from tools.indra_run import", "from tools.indra.run import"),
    ],
)

# Agni example compile test should import the moved include expander.
replace_all(
    "cores/agni/tests/test_examples_compile.py",
    [
        ("from sutra_expand import IncludeError, expand_file", "from tools.sutra.sutra_expand import IncludeError, expand_file"),
    ],
)

print("done")
