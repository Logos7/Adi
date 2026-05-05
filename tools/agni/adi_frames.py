from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

MAGIC_ADI0 = b"ADI0"
MAGIC_ADI1 = b"ADI1"
MAGICS = (MAGIC_ADI0, MAGIC_ADI1)
BOOT_PREFIX = b"ADI_BOOT_"


@dataclass(frozen=True)
class AdiFrame:
    kind: bytes
    width: int
    height: int
    pixels: bytes
    raw_size: int


def unpack_adi1_payload(width: int, height: int, payload: bytes) -> bytes:
    total = width * height
    out = bytearray(total)
    i = 0
    for byte in payload:
        for shift in range(7, -1, -1):
            if i >= total:
                return bytes(out)
            out[i] = 1 if ((byte >> shift) & 1) else 0
            i += 1
    return bytes(out)


def frame_payload_size(kind: bytes, width: int, height: int) -> int:
    pixels = width * height
    if kind == MAGIC_ADI1:
        return (pixels + 7) // 8
    return pixels


def find_next_magic(buffer: bytearray, magics: Iterable[bytes] = MAGICS) -> tuple[int, bytes] | None:
    best_pos = -1
    best_magic = b""
    for magic in magics:
        pos = buffer.find(magic)
        if pos >= 0 and (best_pos < 0 or pos < best_pos):
            best_pos = pos
            best_magic = magic
    if best_pos < 0:
        return None
    return best_pos, best_magic


def buffer_starts_partial_magic(buffer: bytearray, magics: Iterable[bytes] = MAGICS) -> bool:
    if not buffer:
        return False
    text = bytes(buffer)
    return len(text) < 4 and any(magic.startswith(text) for magic in magics)


def pop_frame(buffer: bytearray) -> AdiFrame | None:
    found = find_next_magic(buffer)
    if found is None:
        if len(buffer) > 3:
            del buffer[:-3]
        return None

    pos, kind = found
    if pos > 0:
        del buffer[:pos]

    if len(buffer) < 6:
        return None

    width = buffer[4]
    height = buffer[5]
    if width == 0 or height == 0:
        del buffer[:4]
        return None

    payload_size = frame_payload_size(kind, width, height)
    total_size = 6 + payload_size
    if len(buffer) < total_size:
        return None

    payload = bytes(buffer[6:total_size])
    del buffer[:total_size]

    if kind == MAGIC_ADI1:
        pixels = unpack_adi1_payload(width, height, payload)
    else:
        pixels = payload

    return AdiFrame(kind=kind, width=width, height=height, pixels=pixels, raw_size=payload_size)


class TerminalRxFilter:
    def __init__(self, boot_acks: Iterable[bytes] = ()) -> None:
        self._buf = bytearray()
        self._boot_acks = tuple(boot_acks)
        self.dropped_frames = 0
        self.dropped_bytes = 0

    def feed(self, data: bytes) -> bytes:
        if not data:
            return b""

        self._buf += data
        out = bytearray()

        while self._buf:
            if self._drop_boot_ack_if_ready():
                continue
            if self._has_partial_boot_ack():
                break
            if self._drop_boot_line_if_ready():
                continue

            found = find_next_magic(self._buf)
            if found is not None:
                pos, kind = found
                if pos > 0:
                    chunk = bytes(self._buf[:pos])
                    del self._buf[:pos]
                    out += self._sanitize_text(chunk)
                    continue
                if not self._drop_frame_if_ready(kind):
                    break
                continue

            if buffer_starts_partial_magic(self._buf):
                break

            if len(self._buf) > 8192:
                chunk = bytes(self._buf[:-3])
                del self._buf[:-3]
                out += self._sanitize_text(chunk)
                continue

            b = self._buf.pop(0)
            clean = self._sanitize_byte(b)
            if clean is None:
                self.dropped_bytes += 1
            else:
                out.append(clean)
            if len(out) >= 8192:
                break

        return bytes(out)

    def _drop_boot_ack_if_ready(self) -> bool:
        for ack in self._boot_acks:
            if self._buf.startswith(ack):
                del self._buf[:len(ack)]
                return True
        return False

    def _has_partial_boot_ack(self) -> bool:
        return any(ack.startswith(bytes(self._buf)) for ack in self._boot_acks)

    def _drop_boot_line_if_ready(self) -> bool:
        if not self._buf.startswith(BOOT_PREFIX):
            return False
        newline = self._buf.find(b"\n")
        if newline < 0:
            if len(self._buf) < 80:
                return False
            self.dropped_bytes += 1
            del self._buf[0]
            return True
        self.dropped_bytes += newline + 1
        del self._buf[:newline + 1]
        return True

    def _drop_frame_if_ready(self, kind: bytes) -> bool:
        if len(self._buf) < 6:
            return False
        width = self._buf[4]
        height = self._buf[5]
        if width == 0 or height == 0:
            self.dropped_bytes += 4
            del self._buf[:4]
            return True
        size = 6 + frame_payload_size(kind, width, height)
        if len(self._buf) < size:
            return False
        self.dropped_frames += 1
        self.dropped_bytes += size
        del self._buf[:size]
        return True

    def _sanitize_text(self, data: bytes) -> bytes:
        out = bytearray()
        for b in data:
            clean = self._sanitize_byte(b)
            if clean is None:
                self.dropped_bytes += 1
            else:
                out.append(clean)
        return bytes(out)

    def _sanitize_byte(self, b: int) -> int | None:
        if b in (9, 10, 13):
            return b
        if 32 <= b <= 126:
            return b
        if b >= 128:
            return b
        return None
