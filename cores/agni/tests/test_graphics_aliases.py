from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "sutra"))

from sutra import assemble, flatten_program


def words(source: str) -> list[int]:
    return flatten_program(assemble(source))


def test_hdmi_aliases_match_legacy_framebuffer_opcodes():
    assert words("hdmi.size 320, 200") == words("fbsize 320, 200")
    assert words("hdmi.clear r20") == words("fbclear r20")
    assert words("hdmi.plot r20, r1, r2") == words("fbplot r20, r1, r2")
    assert words("hdmi.erase r20, r1, r2") == words("fberase r20, r1, r2")


def test_uart_present_aliases_match_legacy_framebuffer_opcodes():
    assert words("uart.present0 r20") == words("fbpresent r20")
    assert words("uart.present1 r20") == words("fbpresent1 r20")


def test_graphics_aliases_keep_predicate_prefix():
    assert words("(b0) hdmi.plot r20, r1, r2") == words("(b0) fbplot r20, r1, r2")
