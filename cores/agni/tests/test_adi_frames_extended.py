from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from agni.adi_frames import MAGIC_ADI2, MAGIC_ADI3, pop_frame


def test_pop_adi2_extended_frame_1024_width():
    buffer = bytearray(MAGIC_ADI2 + bytes([0x04, 0x00, 0x00, 0x01]) + b"x" * 1024)

    frame = pop_frame(buffer)

    assert frame is not None
    assert frame.kind == MAGIC_ADI2
    assert frame.width == 1024
    assert frame.height == 1
    assert frame.raw_size == 1024
    assert frame.pixels == b"x" * 1024
    assert buffer == bytearray()


def test_pop_adi3_extended_packed_frame_1024_pixels():
    payload = bytes([0b1010_0000]) * 128
    buffer = bytearray(MAGIC_ADI3 + bytes([0x04, 0x00, 0x00, 0x01]) + payload)

    frame = pop_frame(buffer)

    assert frame is not None
    assert frame.kind == MAGIC_ADI3
    assert frame.width == 1024
    assert frame.height == 1
    assert frame.raw_size == 128
    assert len(frame.pixels) == 1024
    assert frame.pixels[:4] == bytes([1, 0, 1, 0])
