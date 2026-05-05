from __future__ import annotations

import os


def copy_rgb_to_windows_clipboard(width: int, height: int, rgb: bytes) -> None:
    if os.name != "nt":
        raise RuntimeError("Image clipboard copy is currently implemented only for Windows.")
    if width <= 0 or height <= 0:
        raise RuntimeError("Invalid image size.")
    if len(rgb) != width * height * 3:
        raise RuntimeError("Invalid RGB buffer size.")

    import ctypes
    import struct

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_int
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_int

    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    cf_dib = 8
    gmem_moveable = 0x0002
    row_stride = ((width * 3 + 3) // 4) * 4
    padding = row_stride - width * 3
    pixel_data = bytearray()

    for y in range(height - 1, -1, -1):
        row_start = y * width * 3
        for x in range(width):
            i = row_start + x * 3
            pixel_data.extend((rgb[i + 2], rgb[i + 1], rgb[i]))
        if padding:
            pixel_data.extend(b"\x00" * padding)

    header = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(pixel_data), 0, 0, 0, 0)
    data = header + bytes(pixel_data)
    handle = kernel32.GlobalAlloc(gmem_moveable, len(data))
    if not handle:
        raise RuntimeError("GlobalAlloc failed.")

    locked = None
    try:
        locked = kernel32.GlobalLock(handle)
        if not locked:
            raise RuntimeError("GlobalLock failed.")
        ctypes.memmove(locked, data, len(data))
        kernel32.GlobalUnlock(handle)
        locked = None

        if not user32.OpenClipboard(None):
            raise RuntimeError("OpenClipboard failed.")
        try:
            if not user32.EmptyClipboard():
                raise RuntimeError("EmptyClipboard failed.")
            if not user32.SetClipboardData(cf_dib, handle):
                raise RuntimeError("SetClipboardData failed.")
            handle = None
        finally:
            user32.CloseClipboard()
    finally:
        if locked:
            kernel32.GlobalUnlock(handle)
        if handle:
            kernel32.GlobalFree(handle)
