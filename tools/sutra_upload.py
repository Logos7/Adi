#!/usr/bin/env python3
"""
Sutra UART uploader for Brahma-Bija bootloader v1.6.

v1.6 payload is compatible with v1.5 protocol:

    ADI! handshake -> ADI_BOOT_READY\n
    version: u8 = 2
    code_count: u16 little-endian
    data_count: u16 little-endian, flat data_mem blob starting at address 0
    checksum: u32 little-endian, sum of all code/data payload bytes modulo 2^32
    code_words: code_count * u32 little-endian
    data_words: data_count * u32 little-endian

v1.6 raises the supported image limits to 2048 code words and 2048 data words.
"""
from __future__ import annotations

import argparse
import os
import re
import struct
import sys
import time
from dataclasses import dataclass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "sutra"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from sutra import SutraImage, assemble, assemble_image, flatten_program

try:
    from sutra_expand import IncludeError, expand_file
except Exception:
    IncludeError = Exception
    expand_file = None

try:
    import serial
except ImportError:
    serial = None

MAGIC = b"ADI!"
VERSION_V15 = 2
ACK_READY = b"ADI_BOOT_READY\n"
ACK_OK = b"ADI_BOOT_OK\n"
ACK_ERR = b"ADI_BOOT_ERR\n"

MAX_CODE_WORDS = 2048
MAX_DATA_WORDS = 2048


@dataclass
class UploadImage:
    code_words: list[int]
    data_words: list[int]

    @property
    def words(self) -> list[int]:
        return self.code_words


def _check_byte_param(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if value < 1 or value > 255:
        raise SystemExit(f"{name} must be in range 1..255 because ADI0 frame stores it in one byte")
    return int(value)


def _fmt_float(x: float) -> str:
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _strip_comment(line: str) -> str:
    return line.split(";", 1)[0].strip()


def _is_move_reg_imm(line: str, imm: int) -> str | None:
    m = re.match(r"^move\s+(r\d+)\s*,\s*([-+]?\d+)\s*$", _strip_comment(line), re.IGNORECASE)
    if not m:
        return None
    return m.group(1) if int(m.group(2)) == imm else None


def _is_write_reg(line: str, reg: str) -> bool:
    return re.match(rf"^write_tx\s+{re.escape(reg)}\s*$", _strip_comment(line), re.IGNORECASE) is not None


def looks_like_adi0_graphics_source(source: str) -> bool:
    lines = source.splitlines()
    for i in range(len(lines)):
        if i + 7 < len(lines):
            r0 = _is_move_reg_imm(lines[i], 65)
            if (
                r0
                and _is_write_reg(lines[i + 1], r0)
                and (r1 := _is_move_reg_imm(lines[i + 2], 68))
                and _is_write_reg(lines[i + 3], r1)
                and (r2 := _is_move_reg_imm(lines[i + 4], 73))
                and _is_write_reg(lines[i + 5], r2)
                and (r3 := _is_move_reg_imm(lines[i + 6], 48))
                and _is_write_reg(lines[i + 7], r3)
            ):
                return True
    return "fbpresent" in source.lower() or "fbpresent1" in source.lower()


def _patch_adi0_header(source: str, width: int | None, height: int | None) -> tuple[str, bool]:
    lines = source.splitlines()
    endings_newline = source.endswith("\n")
    for i in range(len(lines)):
        if i + 11 < len(lines):
            r0 = _is_move_reg_imm(lines[i], 65)
            r1 = _is_move_reg_imm(lines[i + 2], 68) if r0 and _is_write_reg(lines[i + 1], r0) else None
            r2 = _is_move_reg_imm(lines[i + 4], 73) if r1 and _is_write_reg(lines[i + 3], r1) else None
            r3 = _is_move_reg_imm(lines[i + 6], 48) if r2 and _is_write_reg(lines[i + 5], r2) else None
            if r3 and _is_write_reg(lines[i + 7], r3):
                mw = re.match(r"^move\s+(r\d+)\s*,\s*([-+]?\d+)\s*$", _strip_comment(lines[i + 8]), re.IGNORECASE)
                mh = re.match(r"^move\s+(r\d+)\s*,\s*([-+]?\d+)\s*$", _strip_comment(lines[i + 10]), re.IGNORECASE)
                if mw and mh and _is_write_reg(lines[i + 9], mw.group(1)) and _is_write_reg(lines[i + 11], mh.group(1)):
                    indent = re.match(r"^([ \t]*)", lines[i]).group(1)
                    reg = mw.group(1)
                    w = width if width is not None else int(mw.group(2))
                    h = height if height is not None else int(mh.group(2))
                    lines[i:i + 12] = [
                        f"{indent}move {reg}, 65",
                        f"{indent}write_tx {reg}",
                        f"{indent}move {reg}, 68",
                        f"{indent}write_tx {reg}",
                        f"{indent}move {reg}, 73",
                        f"{indent}write_tx {reg}",
                        f"{indent}move {reg}, 48",
                        f"{indent}write_tx {reg}",
                        f"{indent}move {reg}, {w}",
                        f"{indent}write_tx {reg}",
                        f"{indent}move {reg}, {h}",
                        f"{indent}write_tx {reg}",
                    ]
                    out = "\n".join(lines)
                    if endings_newline:
                        out += "\n"
                    return out, True
    return source, False


def patch_sutra_params(
    source: str,
    width: int | None = None,
    height: int | None = None,
    max_iter: int | None = None,
    graphics: str = "auto",
) -> str:
    width = _check_byte_param("width", width)
    height = _check_byte_param("height", height)
    max_iter = _check_byte_param("max_iter", max_iter)
    if width is None and height is None and max_iter is None:
        return source
    if graphics not in ("auto", "on", "off"):
        raise SystemExit("graphics must be one of: auto, on, off")
    if graphics == "off":
        return source
    if graphics == "auto" and not looks_like_adi0_graphics_source(source):
        return source

    out = source
    if width is not None or height is not None:
        patched, ok = _patch_adi0_header(out, width, height)
        if ok:
            out = patched

    if max_iter is not None:
        out, n1 = re.subn(
            r"(?m)^(?P<i>[ \t]*)cmp\.ge[ \t]+b0,[ \t]*r11,[ \t]*[-+]?\d+(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}cmp.ge b0, r11, {max_iter}",
            out,
        )
        out, n2 = re.subn(
            r"(?m)^(?P<i>[ \t]*)bge[ \t]+r11,[ \t]*[-+]?\d+,[ \t]*(?P<label>[A-Za-z_.$][A-Za-z0-9_.$]*)(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}bge r11, {max_iter}, {m.group('label')}",
            out,
        )
        if n1 + n2 == 0 and graphics == "on":
            raise SystemExit("Could not find r11 max-iter limit to patch")

    if width is not None:
        x_step = _fmt_float(3.0 / width)
        out = re.sub(
            r"(?m)^(?P<i>[ \t]*)fadd[ \t]+r2,[ \t]*r2,[ \t]*[-+]?\d+(?:\.\d+)?(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}fadd r2, r2, {x_step}",
            out,
        )
        out = re.sub(
            r"(?m)^(?P<i>[ \t]*)fadd[ \t]+r6,[ \t]*r6,[ \t]*[-+]?\d+(?:\.\d+)?(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}fadd r6, r6, {x_step}",
            out,
        )

    if height is not None:
        y_step = _fmt_float(3.0 / height)
        out = re.sub(
            r"(?m)^(?P<i>[ \t]*)fadd[ \t]+r3,[ \t]*r3,[ \t]*[-+]?\d+(?:\.\d+)?(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}fadd r3, r3, {y_step}",
            out,
        )
        out = re.sub(
            r"(?m)^(?P<i>[ \t]*)fadd[ \t]+r7,[ \t]*r7,[ \t]*[-+]?\d+(?:\.\d+)?(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}fadd r7, r7, {y_step}",
            out,
        )

    return out


def read_sutra_source(path: str) -> str:
    if expand_file is not None:
        try:
            return expand_file(path)
        except IncludeError as e:
            raise SystemExit(f"Sutra include error: {e}") from e
    with open(path, encoding="utf-8") as f:
        return f.read()


def _normalize_upload_image(obj) -> UploadImage:
    if isinstance(obj, UploadImage):
        return obj
    if isinstance(obj, SutraImage):
        return UploadImage(list(obj.code_words), list(obj.data_words))
    if isinstance(obj, (list, tuple)):
        return UploadImage([int(x) & 0xFFFFFFFF for x in obj], [])
    raise TypeError(f"Unsupported upload image type: {type(obj)!r}")


def _check_image_size(image: UploadImage) -> None:
    if not image.code_words:
        raise SystemExit("Program is empty")
    if len(image.code_words) > MAX_CODE_WORDS:
        raise SystemExit(f"Program has {len(image.code_words)} words, bootloader supports {MAX_CODE_WORDS}")
    if len(image.data_words) > MAX_DATA_WORDS:
        raise SystemExit(f"Data blob has {len(image.data_words)} words, data_mem supports {MAX_DATA_WORDS}")


def assemble_source(source: str) -> UploadImage:
    image = _normalize_upload_image(assemble_image(source))
    _check_image_size(image)
    return image


def assemble_file(
    path: str,
    width: int | None = None,
    height: int | None = None,
    max_iter: int | None = None,
    graphics: str = "auto",
):
    source = read_sutra_source(path)
    return assemble_source(patch_sutra_params(source, width=width, height=height, max_iter=max_iter, graphics=graphics))


def make_body(image_or_words) -> bytes:
    image = _normalize_upload_image(image_or_words)
    _check_image_size(image)

    payload = bytearray()
    for w in image.code_words:
        payload += struct.pack("<I", int(w) & 0xFFFFFFFF)
    for w in image.data_words:
        payload += struct.pack("<I", int(w) & 0xFFFFFFFF)

    checksum = sum(payload) & 0xFFFFFFFF
    header = bytearray()
    header += struct.pack("<B", VERSION_V15)
    header += struct.pack("<H", len(image.code_words))
    header += struct.pack("<H", len(image.data_words))
    header += struct.pack("<I", checksum)
    return bytes(header + payload)


def read_until_any(ser, needles: list[bytes], deadline: float, keep_tail: int = 512) -> tuple[bytes | None, bytes]:
    buf = bytearray()
    while time.monotonic() < deadline:
        chunk = ser.read(256)
        if chunk:
            buf += chunk
            for n in needles:
                if n in buf:
                    return n, bytes(buf)
            if len(buf) > keep_tail:
                del buf[:-keep_tail]
        else:
            time.sleep(0.005)
    return None, bytes(buf)


def drain_input(ser, duration: float = 0.05) -> bytes:
    deadline = time.monotonic() + max(0.0, duration)
    buf = bytearray()
    while time.monotonic() < deadline:
        chunk = ser.read(256)
        if chunk:
            buf += chunk
        else:
            time.sleep(0.002)
    return bytes(buf)


def enter_bootloader(ser, timeout: float, spam_interval: float) -> bytes:
    print("Looking for bootloader: sending ADI! until FPGA replies READY...")
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    deadline = time.monotonic() + timeout
    buf = bytearray()
    next_ping = 0.0
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now >= next_ping:
            ser.write(MAGIC)
            ser.flush()
            next_ping = now + spam_interval
        chunk = ser.read(256)
        if chunk:
            buf += chunk
            if ACK_READY in buf:
                print("Bootloader: READY")
                return bytes(buf)
            if len(buf) > 512:
                del buf[:-512]
        else:
            time.sleep(0.005)
    tail = bytes(buf[-200:])
    raise SystemExit(
        "Timeout entering bootloader.\n"
        f"RX tail={tail!r}\n"
        "If RX tail looks like pixel bytes, the old program is still running. "
        "Rebuild and flash the v1.6 bitstream."
    )


def upload_words_to_serial(
    ser,
    image_or_words,
    boot_timeout: float = 30.0,
    ack_timeout: float = 12.0,
    spam_interval: float = 0.03,
    settle_delay: float = 0.06,
) -> None:
    image = _normalize_upload_image(image_or_words)
    body = make_body(image)
    port = getattr(ser, "port", "open port")
    baud = getattr(ser, "baudrate", "?")
    print(
        f"Upload v1.6: code={len(image.code_words)} words, "
        f"data={len(image.data_words)} words, bytes={len(body) + len(MAGIC)} -> {port} @ {baud}"
    )
    enter_bootloader(ser, boot_timeout, spam_interval)
    if settle_delay > 0:
        drain_input(ser, settle_delay)
    ser.reset_input_buffer()
    print("Sending code+data image...")
    ser.write(body)
    ser.flush()
    deadline = time.monotonic() + ack_timeout
    match, buf = read_until_any(ser, [ACK_OK, ACK_ERR], deadline)
    if match == ACK_OK:
        print("Bootloader: OK")
        return
    if match == ACK_ERR:
        raise SystemExit(f"Bootloader: ERR; RX tail={buf[-200:]!r}")
    raise SystemExit(f"Timeout waiting for OK/ERR. RX tail={buf[-200:]!r}")


def upload_words(
    port: str,
    baud: int,
    words,
    boot_timeout: float = 30.0,
    ack_timeout: float = 12.0,
    spam_interval: float = 0.03,
    settle_delay: float = 0.06,
) -> None:
    if serial is None:
        print("pyserial missing. Install it with: py -m pip install pyserial", file=sys.stderr)
        raise SystemExit(2)
    with serial.Serial(port, baudrate=baud, timeout=0.02, write_timeout=2.0) as ser:
        upload_words_to_serial(ser, words, boot_timeout, ack_timeout, spam_interval, settle_delay)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="e.g. COM9 or /dev/ttyUSB0")
    parser.add_argument("source", help=".sutra source to upload")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--width", type=int, help="override ADI0 width, 1..255")
    parser.add_argument("--height", type=int, help="override ADI0 height, 1..255")
    parser.add_argument("--max-iter", type=int, help="override common r11 fractal iteration limit, 1..255")
    parser.add_argument("--graphics", choices=["auto", "on", "off"], default="auto")
    parser.add_argument("--boot-timeout", type=float, default=30.0)
    parser.add_argument("--ack-timeout", type=float, default=12.0)
    parser.add_argument("--spam-interval", type=float, default=0.03)
    parser.add_argument("--settle-delay", type=float, default=0.06)
    args = parser.parse_args()

    image = assemble_file(
        args.source,
        width=args.width,
        height=args.height,
        max_iter=args.max_iter,
        graphics=args.graphics,
    )
    upload_words(args.port, args.baud, image, args.boot_timeout, args.ack_timeout, args.spam_interval, args.settle_delay)


if __name__ == "__main__":
    main()
