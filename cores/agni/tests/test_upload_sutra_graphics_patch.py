from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "agni"))

from upload_sutra import patch_sutra_params


SOURCE = """
frame:
 move r0, 65
 write_tx r0
 move r0, 68
 write_tx r0
 move r0, 73
 write_tx r0
 move r0, 48
 write_tx r0
 move r0, 64
 write_tx r0
 move r0, 64
 write_tx r0
 move r5, 0
 move r3, -1.5
row_loop:
 move r4, 0
 move r2, -2.0
col_loop:
 move r11, 0
iter_loop:
 bge r11, 64, pixel_done
 write_tx r11
 fadd r2, r2, 0.046875
 inc r4
 blt r4, 64, col_loop
 fadd r3, r3, 0.046875
 inc r5
 blt r5, 64, row_loop
 jump frame
"""


def test_patch_128_updates_header_steps_and_loop_bounds():
    out = patch_sutra_params(SOURCE, width=128, height=128, max_iter=80, graphics="on")
    assert "move r0, 128" in out
    assert "bge r11, 80, pixel_done" in out
    assert "blt r4, 128, col_loop" in out
    assert "blt r5, 128, row_loop" in out
    assert "fadd r2, r2, 0.0234375" in out
    assert "fadd r3, r3, 0.0234375" in out


def test_patch_1024_switches_to_adi2_header():
    out = patch_sutra_params(SOURCE, width=1024, height=1024, graphics="on")
    assert "move r0, 50" in out
    assert "move r0, 4" in out
    assert "move r0, 0" in out
    assert "blt r4, 1024, col_loop" in out
    assert "blt r5, 1024, row_loop" in out
