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


def test_hdmi_clear_path_is_named_separately_from_uart_present():
    text = read_core()

    assert "S_HDMI_CLEAR" in text
    assert "S_FB_CLEAR" not in text
    assert "S_UART_PRESENT_HEADER" in text
    assert "S_FB_PRESENT_HEADER" not in text
    assert "uart_header_byte" in text
    assert "uart_pack_byte" in text
    assert "packed_format ? 8'd49 : 8'd48" in text
    assert "width[7:0]" in text
    assert "height[7:0]" in text


def test_uart_frame_present_rejects_dimensions_not_supported_by_legacy_header():
    text = read_core()

    assert "fb_width[8]" in text
    assert "fb_height[8]" in text


def test_uart_present_guards_framebuffer_base_plus_payload_words():
    text = read_core()

    assert "({2'b00, rd_value[10:0]} + fb_last_word_index) > 13'd2047" in text


def test_load_l_fetch2_pc_increment_is_not_duplicated():
    text = read_core()

    assert "pc <= pc + 32'd2;\n                pc <= pc + 32'd2;" not in text
