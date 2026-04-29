#!/usr/bin/env python3
"""
Sutra UART uploader dla Brahma-Bija bootloadera v1.4.3.

Workflow bez resetu FPGA:
    py tools/sutra_upload.py COM9 examples/bija/04_uart/echo_rx.sutra --graphics off

Parametryzacja przykładowych fraktali:
    py tools/sutra_upload.py COM9 examples/bija/05_fractals/mandelbrot_uart.sutra --width 96 --height 64 --max-iter 80

Protokół:
    1. host wysyła b"ADI!" aż FPGA odpowie b"ADI_BOOT_READY\n"
    2. host wysyła version/count/checksum/payload
    3. FPGA odpowiada b"ADI_BOOT_OK\n" albo b"ADI_BOOT_ERR\n"
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "sutra"))

from sutra import assemble, flatten_program

try:
    import serial
except ImportError:
    serial = None


MAGIC = b"ADI!"
VERSION = 1
ACK_READY = b"ADI_BOOT_READY\n"
ACK_OK = b"ADI_BOOT_OK\n"
ACK_ERR = b"ADI_BOOT_ERR\n"
BOOT_ACKS = (ACK_READY, ACK_OK, ACK_ERR)
MAX_WORDS = 1024


def _check_byte_param(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if value < 1 or value > 255:
        raise SystemExit(f"{name} musi być w zakresie 1..255, bo ramka UART trzyma to w 1 bajcie")
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


def _is_move_uart_imm(line: str, imm: int) -> bool:
    m = re.match(r"^move\s+@uart_tx\s*,\s*([-+]?\d+)\s*$", _strip_comment(line), re.IGNORECASE)
    return bool(m and int(m.group(1)) == imm)


def looks_like_adi0_graphics_source(source: str) -> bool:
    lines = source.splitlines()
    for i in range(len(lines)):
        if i + 3 < len(lines):
            if (
                _is_move_uart_imm(lines[i], 65)
                and _is_move_uart_imm(lines[i + 1], 68)
                and _is_move_uart_imm(lines[i + 2], 73)
                and _is_move_uart_imm(lines[i + 3], 48)
            ):
                return True

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
    return False


def _patch_adi0_header(source: str, width: int | None, height: int | None) -> tuple[str, bool]:
    lines = source.splitlines()
    endings_newline = source.endswith("\n")

    for i in range(len(lines)):
        if i + 5 < len(lines):
            old = (
                _is_move_uart_imm(lines[i], 65)
                and _is_move_uart_imm(lines[i + 1], 68)
                and _is_move_uart_imm(lines[i + 2], 73)
                and _is_move_uart_imm(lines[i + 3], 48)
            )
            if old:
                mw = re.match(r"^move\s+@uart_tx\s*,\s*([-+]?\d+)\s*$", _strip_comment(lines[i + 4]), re.IGNORECASE)
                mh = re.match(r"^move\s+@uart_tx\s*,\s*([-+]?\d+)\s*$", _strip_comment(lines[i + 5]), re.IGNORECASE)
                if mw and mh:
                    indent = re.match(r"^([ \t]*)", lines[i]).group(1)
                    w = width if width is not None else int(mw.group(1))
                    h = height if height is not None else int(mh.group(1))
                    lines[i:i + 6] = [
                        f"{indent}move r0, 65",
                        f"{indent}write_tx r0",
                        f"{indent}move r0, 68",
                        f"{indent}write_tx r0",
                        f"{indent}move r0, 73",
                        f"{indent}write_tx r0",
                        f"{indent}move r0, 48",
                        f"{indent}write_tx r0",
                        f"{indent}move r0, {w}",
                        f"{indent}write_tx r0",
                        f"{indent}move r0, {h}",
                        f"{indent}write_tx r0",
                    ]
                    out = "\n".join(lines)
                    if endings_newline:
                        out += "\n"
                    return out, True

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
        raise SystemExit("graphics musi mieć wartość: auto, on albo off")

    if graphics == "off":
        return source

    if graphics == "auto" and not looks_like_adi0_graphics_source(source):
        return source

    out = source

    if width is not None or height is not None:
        out, patched = _patch_adi0_header(out, width, height)
        if not patched:
            raise SystemExit("Nie znalazłem nagłówka ramki ADI0 w .sutra, więc nie umiem zmienić width/height")

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
        if n1 + n2 == 0:
            raise SystemExit("Nie znalazłem limitu iteracji r11, więc nie umiem zmienić max_iter")

    if width is not None:
        out, n1 = re.subn(
            r"(?m)^(?P<i>[ \t]*)cmp\.lt[ \t]+b0,[ \t]*r4,[ \t]*[-+]?\d+(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}cmp.lt b0, r4, {width}",
            out,
        )
        out, n2 = re.subn(
            r"(?m)^(?P<i>[ \t]*)blt[ \t]+r4,[ \t]*[-+]?\d+,[ \t]*(?P<label>[A-Za-z_.$][A-Za-z0-9_.$]*)(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}blt r4, {width}, {m.group('label')}",
            out,
        )
        if n1 + n2 == 0:
            raise SystemExit("Nie znalazłem pętli X na r4")
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
        out, n1 = re.subn(
            r"(?m)^(?P<i>[ \t]*)cmp\.lt[ \t]+b0,[ \t]*r5,[ \t]*[-+]?\d+(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}cmp.lt b0, r5, {height}",
            out,
        )
        out, n2 = re.subn(
            r"(?m)^(?P<i>[ \t]*)blt[ \t]+r5,[ \t]*[-+]?\d+,[ \t]*(?P<label>[A-Za-z_.$][A-Za-z0-9_.$]*)(?:[ \t]*;[^\n]*)?$",
            lambda m: f"{m.group('i')}blt r5, {height}, {m.group('label')}",
            out,
        )
        if n1 + n2 == 0:
            raise SystemExit("Nie znalazłem pętli Y na r5")
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


def assemble_source(source: str) -> list[int]:
    words = flatten_program(assemble(source))
    if not words:
        raise SystemExit("Program jest pusty")
    if len(words) > MAX_WORDS:
        raise SystemExit(f"Program ma {len(words)} słów, bootloader mieści {MAX_WORDS}")
    return words


def assemble_file(
    path: str,
    width: int | None = None,
    height: int | None = None,
    max_iter: int | None = None,
    graphics: str = "auto",
) -> list[int]:
    with open(path, encoding="utf-8") as f:
        source = f.read()
    return assemble_source(patch_sutra_params(source, width=width, height=height, max_iter=max_iter, graphics=graphics))


def make_body(words: list[int]) -> bytes:
    payload = bytearray()
    for w in words:
        payload += struct.pack("<I", w & 0xFFFFFFFF)
    checksum = sum(payload) & 0xFFFFFFFF
    header = bytes([VERSION]) + struct.pack("<H", len(words)) + struct.pack("<I", checksum)
    return bytes(header + payload)


def read_until_any(ser, needles: list[bytes], deadline: float, keep_tail: int = 300) -> tuple[bytes | None, bytes]:
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
    print("Szukam bootloadera: wysyłam ADI! aż FPGA odpowie READY...")
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
            if len(buf) > 400:
                del buf[:-400]
        else:
            time.sleep(0.005)

    tail = bytes(buf[-160:])
    raise SystemExit(
        "Timeout wejścia do bootloadera. "
        f"Końcówka RX={tail!r}\n"
        "Jeśli końcówka wygląda jak bajty pikseli (np. 01/02/03...), FPGA nadal uruchamia stary program. "
        "Wgraj bitstream v1.4.3 po pełnym cleanie Gowina. "
        "Jeśli LED0 świeci, ale READY nie przychodzi, sprawdź pin uart_rx."
    )


def upload_words_to_serial(
    ser,
    words: list[int],
    boot_timeout: float = 30.0,
    ack_timeout: float = 12.0,
    spam_interval: float = 0.03,
    settle_delay: float = 0.06,
) -> None:
    body = make_body(words)
    port = getattr(ser, "port", "otwarty port")
    baud = getattr(ser, "baudrate", "?")
    print(f"Upload: {len(words)} słów / {len(body) + len(MAGIC)} bajtów → {port} @ {baud}")

    enter_bootloader(ser, boot_timeout, spam_interval)

    # READY jest już odebrane. Dajemy chwilę na dopłynięcie resztek ACK po stronie PC.
    # Spóźnione ADI! po stronie FPGA ignoruje bootloader v1.4.3.
    if settle_delay > 0:
        drain_input(ser, settle_delay)
    ser.reset_input_buffer()

    print("Wysyłam program...")
    ser.write(body)
    ser.flush()

    deadline = time.monotonic() + ack_timeout
    match, buf = read_until_any(ser, [ACK_OK, ACK_ERR], deadline)
    if match == ACK_OK:
        print("Bootloader: OK")
        return
    if match == ACK_ERR:
        raise SystemExit(f"Bootloader: ERR; końcówka RX={buf[-160:]!r}")
    raise SystemExit(f"Timeout czekania na OK/ERR. Końcówka RX={buf[-160:]!r}")


def upload_words(
    port: str,
    baud: int,
    words: list[int],
    boot_timeout: float = 30.0,
    ack_timeout: float = 12.0,
    spam_interval: float = 0.03,
    settle_delay: float = 0.06,
) -> None:
    if serial is None:
        print("Brak pyserial. Zainstaluj: py -m pip install pyserial", file=sys.stderr)
        raise SystemExit(2)
    with serial.Serial(port, baudrate=baud, timeout=0.02, write_timeout=2.0) as ser:
        upload_words_to_serial(ser, words, boot_timeout, ack_timeout, spam_interval, settle_delay)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="np. COM9 albo /dev/ttyUSB0")
    parser.add_argument("source", help="plik .sutra do uploadu")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--width", type=int, help="nadpisz szerokość ramki ADI0 i pętlę X, 1..255")
    parser.add_argument("--height", type=int, help="nadpisz wysokość ramki ADI0 i pętlę Y, 1..255")
    parser.add_argument("--max-iter", type=int, help="nadpisz limit iteracji r11, 1..255")
    parser.add_argument("--graphics", choices=["auto", "on", "off"], default="auto", help="patch parametrów ADI0: auto/on/off; off dla zwykłych programów")
    parser.add_argument("--boot-timeout", type=float, default=30.0, help="ile sekund wysyłać ADI! czekając na READY")
    parser.add_argument("--ack-timeout", type=float, default=12.0, help="ile sekund czekać na OK/ERR po wysłaniu programu")
    parser.add_argument("--spam-interval", type=float, default=0.03, help="odstęp między kolejnymi ADI! podczas handshake")
    parser.add_argument("--settle-delay", type=float, default=0.06, help="krótka pauza po READY przed wysłaniem programu")
    args = parser.parse_args()

    words = assemble_file(args.source, width=args.width, height=args.height, max_iter=args.max_iter, graphics=args.graphics)
    upload_words(args.port, args.baud, words, args.boot_timeout, args.ack_timeout, args.spam_interval, args.settle_delay)


if __name__ == "__main__":
    main()
