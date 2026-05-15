from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

MAGIC_ADI0 = b"ADI0"
MAGIC_ADI1 = b"ADI1"
MAGIC_ADI2 = b"ADI2"
MAGIC_ADI3 = b"ADI3"
MAGICS = (MAGIC_ADI0, MAGIC_ADI1, MAGIC_ADI2, MAGIC_ADI3)
BOOT_PREFIX = b"ADI_BOOT_"

LEGACY_HEADER_SIZE = 6
EXTENDED_HEADER_SIZE = 8
MAX_FRAME_DIM = 1024
MAX_UNPACKED_PAYLOAD_SIZE = MAX_FRAME_DIM * MAX_FRAME_DIM
MAX_PACKED_PAYLOAD_SIZE = (MAX_FRAME_DIM * MAX_FRAME_DIM + 7) // 8
MAX_TEXT_BUFFER_SIZE = 8192


@dataclass(frozen=True)
class AdiFrame:
    kind: bytes
    width: int
    height: int
    pixels: bytes
    raw_size: int


def is_packed_kind(kind: bytes) -> bool:
    return kind in (MAGIC_ADI1, MAGIC_ADI3)


def header_size(kind: bytes) -> int:
    return EXTENDED_HEADER_SIZE if kind in (MAGIC_ADI2, MAGIC_ADI3) else LEGACY_HEADER_SIZE


def read_dimensions(kind: bytes, buffer: bytearray | bytes) -> tuple[int, int] | None:
    size = header_size(kind)
    if len(buffer) < size:
        return None

    if size == LEGACY_HEADER_SIZE:
        return buffer[4], buffer[5]

    width = (buffer[4] << 8) | buffer[5]
    height = (buffer[6] << 8) | buffer[7]
    return width, height


def dimensions_are_valid(width: int, height: int) -> bool:
    return 1 <= width <= MAX_FRAME_DIM and 1 <= height <= MAX_FRAME_DIM


def unpack_packed_payload(width: int, height: int, payload: bytes) -> bytes:
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


def unpack_adi1_payload(width: int, height: int, payload: bytes) -> bytes:
    return unpack_packed_payload(width, height, payload)


def frame_payload_size(kind: bytes, width: int, height: int) -> int:
    pixels = width * height
    if is_packed_kind(kind):
        return (pixels + 7) // 8
    return pixels


def frame_payload_size_is_valid(kind: bytes, payload_size: int) -> bool:
    if is_packed_kind(kind):
        return payload_size <= MAX_PACKED_PAYLOAD_SIZE
    return payload_size <= MAX_UNPACKED_PAYLOAD_SIZE


def find_next_magic(buffer: bytearray | bytes, magics: Iterable[bytes] = MAGICS, start: int = 0) -> tuple[int, bytes] | None:
    text = bytes(buffer)
    best_pos = -1
    best_magic = b""
    for magic in magics:
        pos = text.find(magic, start)
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


def _drop_false_magic(buffer: bytearray) -> None:
    del buffer[0]


def _has_next_magic_before(buffer: bytearray, limit: int) -> bool:
    found = find_next_magic(buffer, start=1)
    return found is not None and found[0] < limit


def pop_frame(buffer: bytearray) -> AdiFrame | None:
    while True:
        found = find_next_magic(buffer)
        if found is None:
            if len(buffer) > 3:
                del buffer[:-3]
            return None

        pos, kind = found
        if pos > 0:
            del buffer[:pos]

        size = header_size(kind)
        if len(buffer) < size:
            return None

        dims = read_dimensions(kind, buffer)
        if dims is None:
            return None

        width, height = dims
        if not dimensions_are_valid(width, height):
            _drop_false_magic(buffer)
            continue

        payload_size = frame_payload_size(kind, width, height)
        if not frame_payload_size_is_valid(kind, payload_size):
            _drop_false_magic(buffer)
            continue

        total_size = size + payload_size

        if len(buffer) < total_size:
            if _has_next_magic_before(buffer, len(buffer)):
                _drop_false_magic(buffer)
                continue
            return None

        if _has_next_magic_before(buffer, total_size):
            _drop_false_magic(buffer)
            continue

        payload = bytes(buffer[size:total_size])
        del buffer[:total_size]

        if is_packed_kind(kind):
            pixels = unpack_packed_payload(width, height, payload)
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

            if len(self._buf) > MAX_TEXT_BUFFER_SIZE:
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

            if len(out) >= MAX_TEXT_BUFFER_SIZE:
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
        size = header_size(kind)
        if len(self._buf) < size:
            return False

        dims = read_dimensions(kind, self._buf)
        if dims is None:
            return False

        width, height = dims
        if not dimensions_are_valid(width, height):
            self.dropped_bytes += 1
            del self._buf[0]
            return True

        frame_size = size + frame_payload_size(kind, width, height)
        if len(self._buf) < frame_size:
            if _has_next_magic_before(self._buf, len(self._buf)):
                self.dropped_bytes += 1
                del self._buf[0]
                return True
            return False

        self.dropped_frames += 1
        self.dropped_bytes += frame_size
        del self._buf[:frame_size]
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
