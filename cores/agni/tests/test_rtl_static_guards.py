from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "cores" / "agni" / "rtl" / "src" / "agni_core.v"


def read_core() -> str:
    return CORE.read_text(encoding="utf-8")


def test_legacy_framebuffer_rmw_path_is_removed():
    text = read_core()

    removed_tokens = [
        "S_FB_RMW_WAIT",
        "S_FB_RMW_WRITE",
        "fb_bit_mask",
        "fb_set_bit",
        "fb_ext_word_index",
        "fb_word_offset_work",
        "fb_addr13_work",
    ]

    for token in removed_tokens:
        assert token not in text


def test_load_l_does_not_wrap_program_memory():
    text = read_core()

    assert "if (pc[10:0] == 11'd2047)" in text
    assert "instr2 <= imem[pc[10:0] + 11'd1];" in text


def test_uart_frame_present_rejects_9_bit_dimensions():
    text = read_core()

    assert "fb_width[8]" in text
    assert "fb_height[8]" in text
    assert "fb_header_byte" in text
    assert "width[7:0]" in text
    assert "height[7:0]" in text
