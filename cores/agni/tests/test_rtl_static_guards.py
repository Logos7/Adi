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


def test_hdmi_and_uart_frame_paths_are_named_separately():
    text = read_core()

    assert "S_HDMI_CLEAR" in text
    assert "S_UART_PRESENT_HEADER" in text
    assert "uart_frame_header_byte" in text
    assert "uart_frame_pack_byte" in text
    assert "S_FB_PRESENT_HEADER" not in text
    assert "fb_header_byte" not in text
    assert "fb_pack_byte" not in text


def test_uart_present_uses_extended_adi2_adi3_header():
    text = read_core()

    assert "UART_FRAME_MAX_SIZE = 11'd1024" in text
    assert "input [10:0] width;" in text
    assert "input [10:0] height;" in text
    assert "packed_format ? 8'd51 : 8'd50" in text
    assert "width[10:8]" in text
    assert "height[10:8]" in text
    assert "if (uart_header_index == 3'd7)" in text


def test_uart_present_still_guards_data_memory_capacity():
    text = read_core()

    assert "DATA_MEM_LAST_WORD" in text
    assert "fb_last_word_index > DATA_MEM_LAST_WORD" in text
    assert "{5'd0, rd_value[10:0]} + fb_last_word_index > DATA_MEM_LAST_WORD" in text
