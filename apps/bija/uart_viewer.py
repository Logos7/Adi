#!/usr/bin/env python3

from __future__ import annotations

import argparse
import colorsys
import json
import os
import sys
import time
from dataclasses import dataclass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("pySerial is missing.", file=sys.stderr)

    print("Install it with: py -m pip install pyserial", file=sys.stderr)
    raise SystemExit(2)

from sutra_upload import assemble_file, upload_words

DEFAULT_SOURCE = os.path.join("examples", "bija", "fractals", "julia.sutra")
MAGIC_ADI0 = b"ADI0"
MAGIC_ADI1 = b"ADI1"
MAGICS = (MAGIC_ADI0, MAGIC_ADI1)

PALETTES: list[tuple[str, str]] = [
    ("classic", "Classic"),
    ("inferno", "Inferno"),
    ("fire", "Fire"),
    ("ocean", "Ocean"),
    ("viridis", "Viridis"),
    ("neon", "Neon"),
    ("nebula", "Nebula"),
    ("gold", "Gold"),
]

PALETTE_LABELS = [label for _key, label in PALETTES]
PALETTE_KEYS = [key for key, _label in PALETTES]
PALETTE_KEY_BY_LABEL = {label: key for key, label in PALETTES}
PALETTE_LABEL_BY_KEY = {key: label for key, label in PALETTES}
DEFAULT_PALETTE = "classic"


@dataclass
class ViewerDefaults:
    port: str | None
    baud: int
    source: str
    upload: str | None
    width: int
    height: int
    max_iter: int
    scale: int
    palette: str
    boot_timeout: float
    ack_timeout: float


def app_state_file() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Adi", "uart_viewer_state.json")


def load_app_state() -> dict:
    try:
        with open(app_state_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_app_state(state: dict) -> None:
    try:
        path = app_state_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def default_browse_dir() -> str:
    return os.path.join(ROOT, "examples", "bija")


def load_last_sutra_dir() -> str:
    state = load_app_state()
    path = state.get("last_sutra_dir", "")
    if isinstance(path, str) and os.path.isdir(path):
        return path
    return default_browse_dir()


def save_last_sutra_dir(path: str) -> None:
    if not path:
        return
    state = load_app_state()
    state["last_sutra_dir"] = path
    save_app_state(state)


def normalize_palette(value: str | None) -> str:
    if not value:
        return DEFAULT_PALETTE
    text = value.strip()
    if text in PALETTE_KEYS:
        return text
    lowered = text.lower()
    for key, label in PALETTES:
        if lowered == label.lower():
            return key
    return DEFAULT_PALETTE


def palette_label(value: str | None) -> str:
    return PALETTE_LABEL_BY_KEY.get(normalize_palette(value), PALETTE_LABEL_BY_KEY[DEFAULT_PALETTE])


def available_ports() -> list[str]:
    ports = [p.device for p in list_ports.comports()]

    def key(port: str) -> tuple[int, int | str]:
        upper = port.upper()
        if upper.startswith("COM"):
            try:
                return 0, int(upper[3:])
            except ValueError:
                return 0, 9999
        return 1, port

    return sorted(ports, key=key)


def choose_default_port(ports: list[str]) -> str:
    if "COM9" in ports:
        return "COM9"
    if "COM8" in ports:
        return "COM8"
    return ports[0] if ports else "COM9"


def resolve_path(path: str) -> str:
    path = path.strip()
    if not path:
        return os.path.join(ROOT, DEFAULT_SOURCE)
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def as_repo_path(path: str) -> str:
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def parse_int(value: str, name: str, min_value: int, max_value: int) -> int:
    try:
        x = int(value.strip())
    except Exception:
        raise ValueError(f"{name} must be an integer.")
    if x < min_value or x > max_value:
        raise ValueError(f"{name} must be in range {min_value}..{max_value}.")
    return x


def optional_byte(value: str, name: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    return parse_int(text, name, 1, 255)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def gradient_color(stops: list[tuple[float, tuple[int, int, int]]], t: float) -> tuple[int, int, int]:
    t = clamp01(t)
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        left_t, left_rgb = stops[i - 1]
        right_t, right_rgb = stops[i]
        if t <= right_t:
            local = 0.0 if right_t == left_t else (t - left_t) / (right_t - left_t)
            return (
                lerp(left_rgb[0], right_rgb[0], local),
                lerp(left_rgb[1], right_rgb[1], local),
                lerp(left_rgb[2], right_rgb[2], local),
            )
    return stops[-1][1]


def classic_palette(v: int, max_iter: int) -> tuple[int, int, int]:
    if v >= max_iter:
        return 0, 0, 0
    if v <= 0:
        return 7, 19, 61
    t = clamp01(v / max_iter)
    hue = 0.68 - 0.68 * (t ** 0.82)
    sat = 0.88
    val = 0.20 + 0.80 * (t ** 0.35)
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return int(r * 255), int(g * 255), int(b * 255)


def palette_rgb(v: int, max_iter: int, palette: str) -> tuple[int, int, int]:
    if v >= max_iter:
        return 0, 0, 0
    if max_iter <= 1:
        t = 0.0
    else:
        t = clamp01(v / max_iter)

    t_soft = t ** 0.72
    t_hot = t ** 0.45
    key = normalize_palette(palette)

    if key == "classic":
        return classic_palette(v, max_iter)

    if key == "inferno":
        return gradient_color(
            [
                (0.00, (0, 0, 4)),
                (0.18, (38, 12, 72)),
                (0.36, (113, 31, 93)),
                (0.58, (201, 65, 55)),
                (0.80, (249, 142, 8)),
                (1.00, (252, 255, 164)),
            ],
            t_soft,
        )

    if key == "fire":
        return gradient_color(
            [
                (0.00, (5, 0, 0)),
                (0.18, (80, 0, 0)),
                (0.42, (190, 28, 0)),
                (0.68, (255, 122, 16)),
                (0.88, (255, 220, 80)),
                (1.00, (255, 255, 230)),
            ],
            t_hot,
        )

    if key == "ocean":
        return gradient_color(
            [
                (0.00, (0, 6, 30)),
                (0.22, (0, 42, 92)),
                (0.46, (0, 112, 150)),
                (0.70, (0, 190, 185)),
                (0.90, (142, 238, 215)),
                (1.00, (235, 255, 247)),
            ],
            t_soft,
        )

    if key == "viridis":
        return gradient_color(
            [
                (0.00, (68, 1, 84)),
                (0.24, (59, 82, 139)),
                (0.48, (33, 145, 140)),
                (0.72, (94, 201, 98)),
                (1.00, (253, 231, 37)),
            ],
            t_soft,
        )

    if key == "neon":
        return gradient_color(
            [
                (0.00, (3, 0, 35)),
                (0.20, (30, 0, 130)),
                (0.42, (0, 96, 255)),
                (0.62, (0, 238, 255)),
                (0.82, (90, 255, 90)),
                (1.00, (255, 255, 255)),
            ],
            t_soft,
        )

    if key == "nebula":
        return gradient_color(
            [
                (0.00, (4, 0, 18)),
                (0.20, (28, 0, 70)),
                (0.42, (92, 24, 140)),
                (0.62, (190, 42, 150)),
                (0.82, (255, 126, 80)),
                (1.00, (255, 235, 170)),
            ],
            t_soft,
        )

    if key == "gold":
        return gradient_color(
            [
                (0.00, (18, 8, 0)),
                (0.22, (70, 38, 0)),
                (0.44, (150, 95, 18)),
                (0.66, (225, 165, 45)),
                (0.86, (255, 220, 115)),
                (1.00, (255, 252, 220)),
            ],
            t_soft,
        )

    return classic_palette(v, max_iter)


def frame_pixel_rgb(v: int, max_iter: int, palette: str, frame_kind: bytes) -> tuple[int, int, int]:
    if frame_kind == MAGIC_ADI1:
        return (255, 255, 255) if v else (0, 0, 0)
    return palette_rgb(v, max_iter, palette)


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
            r = rgb[i]
            g = rgb[i + 1]
            b = rgb[i + 2]
            pixel_data.extend((b, g, r))
        if padding:
            pixel_data.extend(b"\x00" * padding)

    header = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        height,
        1,
        24,
        0,
        len(pixel_data),
        2835,
        2835,
        0,
        0,
    )

    dib = header + bytes(pixel_data)
    handle = kernel32.GlobalAlloc(gmem_moveable, len(dib))
    if not handle:
        raise RuntimeError("GlobalAlloc failed.")

    locked = kernel32.GlobalLock(handle)
    if not locked:
        kernel32.GlobalFree(handle)
        raise RuntimeError("GlobalLock failed.")

    ctypes.memmove(locked, dib, len(dib))
    kernel32.GlobalUnlock(handle)

    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        raise RuntimeError("OpenClipboard failed.")

    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(cf_dib, handle):
            kernel32.GlobalFree(handle)
            raise RuntimeError("SetClipboardData failed.")
        handle = None
    finally:
        user32.CloseClipboard()
        if handle:
            kernel32.GlobalFree(handle)


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


def find_next_magic(buffer: bytearray) -> tuple[int, bytes] | None:
    best_pos = -1
    best_magic = b""

    for magic in MAGICS:
        pos = buffer.find(magic)
        if pos >= 0 and (best_pos < 0 or pos < best_pos):
            best_pos = pos
            best_magic = magic

    if best_pos < 0:
        return None

    return best_pos, best_magic


def run_gui(defaults: ViewerDefaults) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Adi UART Viewer")
    root.geometry("1000x800")

    ports = available_ports()

    port_var = tk.StringVar(value=defaults.port or choose_default_port(ports))
    baud_var = tk.StringVar(value=str(defaults.baud))
    file_var = tk.StringVar(value=defaults.upload or defaults.source)
    width_var = tk.StringVar(value=str(defaults.width))
    height_var = tk.StringVar(value=str(defaults.height))
    max_iter_var = tk.StringVar(value=str(defaults.max_iter))
    scale_var = tk.StringVar(value=str(defaults.scale))
    palette_var = tk.StringVar(value=palette_label(defaults.palette))
    status_var = tk.StringVar(value="Disconnected")

    ser_ref: dict[str, serial.Serial | None] = {"ser": None}
    uploading_ref = {"active": False}
    buffer = bytearray()
    image_ref: dict[str, tk.PhotoImage | None] = {"img": None}
    display_frame_ref: dict[str, int | bytes | None] = {"width": 0, "height": 0, "rgb": None}
    frame_counter = {"n": 0}
    frame_timing = {"last": None, "fps": 0.0}

    outer = ttk.Frame(root, padding=10)
    outer.pack(fill="both", expand=True)

    connection = ttk.LabelFrame(outer, text="Connection", padding=8)
    connection.pack(fill="x")

    ttk.Label(connection, text="Port").grid(row=0, column=0, sticky="w")
    port_box = ttk.Combobox(connection, textvariable=port_var, values=ports, width=16)
    port_box.grid(row=0, column=1, sticky="w", padx=(6, 12))

    log_box = ScrolledText(outer, width=120, height=8, font=("Consolas", 9), wrap="char")

    def log(text: str) -> None:
        log_box.insert("end", text)
        log_box.see("end")

    def refresh_ports() -> None:
        new_ports = available_ports()
        port_box["values"] = new_ports
        if port_var.get() not in new_ports:
            port_var.set(choose_default_port(new_ports))
        log(f"[PORTS] {', '.join(new_ports) if new_ports else 'none'}\n")

    ttk.Button(connection, text="Refresh", command=refresh_ports).grid(row=0, column=2, sticky="w")

    ttk.Label(connection, text="Baud").grid(row=0, column=3, sticky="e", padx=(18, 6))
    ttk.Entry(connection, textvariable=baud_var, width=10).grid(row=0, column=4, sticky="w")

    connection_buttons = ttk.Frame(connection)
    connection_buttons.grid(row=0, column=5, sticky="e", padx=(18, 0))

    program = ttk.LabelFrame(outer, text="Program", padding=8)
    program.pack(fill="x", pady=(10, 0))

    ttk.Label(program, text="Sutra file").grid(row=0, column=0, sticky="w")
    ttk.Entry(program, textvariable=file_var).grid(row=0, column=1, sticky="we", padx=(6, 8))

    def browse() -> None:
        path = filedialog.askopenfilename(
            title="Select Sutra program",
            initialdir=load_last_sutra_dir(),
            filetypes=[("Sutra", "*.sutra"), ("All files", "*.*")],
        )
        if path:
            save_last_sutra_dir(os.path.dirname(path))
            file_var.set(as_repo_path(path))

    ttk.Button(program, text="Browse", command=browse).grid(row=0, column=2, sticky="e")
    program.columnconfigure(1, weight=1)

    render = ttk.LabelFrame(outer, text="ADI0 / ADI1 frame settings", padding=8)
    render.pack(fill="x", pady=(10, 0))

    ttk.Label(render, text="Width").grid(row=0, column=0, sticky="w")
    ttk.Entry(render, textvariable=width_var, width=7).grid(row=0, column=1, sticky="w", padx=(6, 14))

    ttk.Label(render, text="Height").grid(row=0, column=2, sticky="w")
    ttk.Entry(render, textvariable=height_var, width=7).grid(row=0, column=3, sticky="w", padx=(6, 14))

    ttk.Label(render, text="Max iter").grid(row=0, column=4, sticky="w")
    ttk.Entry(render, textvariable=max_iter_var, width=7).grid(row=0, column=5, sticky="w", padx=(6, 14))

    ttk.Label(render, text="Scale").grid(row=0, column=6, sticky="w")
    ttk.Entry(render, textvariable=scale_var, width=7).grid(row=0, column=7, sticky="w", padx=(6, 14))

    ttk.Label(render, text="Palette").grid(row=0, column=8, sticky="w")
    palette_box = ttk.Combobox(render, textvariable=palette_var, values=PALETTE_LABELS, width=12, state="readonly")
    palette_box.grid(row=0, column=9, sticky="w", padx=(6, 0))

    actions = ttk.LabelFrame(outer, text="Actions", padding=8)
    actions.pack(fill="x", pady=(10, 0))

    ttk.Label(outer, textvariable=status_var).pack(fill="x", pady=(8, 4))

    canvas_frame = ttk.LabelFrame(outer, text="Frame", padding=8)
    canvas_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(canvas_frame, width=512, height=384, background="#111111", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    log_box.pack(fill="x", pady=(10, 0))

    def current_baud() -> int:
        return parse_int(baud_var.get(), "Baud", 1, 3_000_000)

    def current_palette() -> str:
        return PALETTE_KEY_BY_LABEL.get(palette_var.get(), DEFAULT_PALETTE)

    def current_params() -> tuple[str, int | None, int | None, int, int, str]:
        path = resolve_path(file_var.get())
        width = optional_byte(width_var.get(), "Width")
        height = optional_byte(height_var.get(), "Height")
        max_iter = parse_int(max_iter_var.get(), "Max iter", 1, 255)
        scale = parse_int(scale_var.get(), "Scale", 1, 32)
        palette = current_palette()
        return path, width, height, max_iter, scale, palette

    def close_serial() -> None:
        ser = ser_ref["ser"]
        ser_ref["ser"] = None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def open_serial(clear_buffers: bool = True) -> None:
        close_serial()
        port = port_var.get().strip()
        if not port:
            raise ValueError("Port is empty.")
        baud = current_baud()
        ser = serial.Serial(port, baudrate=baud, timeout=0.01, write_timeout=2.0)
        ser_ref["ser"] = ser
        if clear_buffers:
            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception:
                pass
        buffer.clear()
        frame_timing["last"] = None
        frame_timing["fps"] = 0.0
        status_var.set(f"Connected: {port} @ {baud}")
        log(f"[OPEN] {port} @ {baud}\n")

    def connect() -> None:
        try:
            open_serial(clear_buffers=True)
        except Exception as e:
            status_var.set("Connection error")
            messagebox.showerror("Connection", str(e))

    def disconnect() -> None:
        close_serial()
        status_var.set("Disconnected")
        log("[CLOSE]\n")

    def clear() -> None:
        buffer.clear()
        frame_counter["n"] = 0
        frame_timing["last"] = None
        frame_timing["fps"] = 0.0
        image_ref["img"] = None
        display_frame_ref["width"] = 0
        display_frame_ref["height"] = 0
        display_frame_ref["rgb"] = None
        canvas.delete("all")
        log_box.delete("1.0", "end")
        status_var.set("Cleared")

    def copy_image() -> None:
        width = display_frame_ref["width"]
        height = display_frame_ref["height"]
        rgb = display_frame_ref["rgb"]

        if not isinstance(width, int) or not isinstance(height, int) or not isinstance(rgb, bytes):
            messagebox.showinfo("Copy image", "No frame image to copy yet.")
            return

        if width <= 0 or height <= 0:
            messagebox.showinfo("Copy image", "No frame image to copy yet.")
            return

        try:
            copy_rgb_to_windows_clipboard(width, height, rgb)
            status_var.set(f"Copied image to clipboard: {width}x{height}")
            log(f"[COPY IMAGE] {width}x{height}\n")
        except Exception as e:
            status_var.set("Copy image failed")
            log(f"[COPY IMAGE ERR] {e}\n")
            messagebox.showerror("Copy image", str(e))

    def save_image() -> None:
        img = image_ref["img"]
        width = display_frame_ref["width"]
        height = display_frame_ref["height"]

        if img is None or not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            messagebox.showinfo("Save image", "No frame image to save yet.")
            return

        images_dir = os.path.join(ROOT, "docs", "images")
        initial_dir = images_dir if os.path.isdir(images_dir) else ROOT
        initial_file = f"adi-frame-{frame_counter['n']:04d}-{width}x{height}.png"

        path = filedialog.asksaveasfilename(
            title="Save current frame image",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )

        if not path:
            return

        try:
            img.write(path, format="png")
            status_var.set(f"Saved image: {as_repo_path(path)}")
            log(f"[SAVE IMAGE] {path}\n")
        except Exception as e:
            status_var.set("Save image failed")
            log(f"[SAVE IMAGE ERR] {e}\n")
            messagebox.showerror("Save image", str(e))

    def upload() -> None:
        if uploading_ref["active"]:
            return

        uploading_ref["active"] = True

        try:
            port = port_var.get().strip()
            if not port:
                raise ValueError("Port is empty.")

            baud = current_baud()
            path, width, height, max_iter, _scale, _palette = current_params()
            normalized_path = path.replace("\\", "/").lower()
            is_fractal = "fractals" in normalized_path

            close_serial()

            words = assemble_file(
                path,
                width=width,
                height=height,
                max_iter=max_iter if is_fractal else None,
                graphics="auto",
            )

            status_var.set(f"Uploading: {os.path.basename(path)}")
            log(f"[UPLOAD] {path}\n")
            root.update_idletasks()

            upload_words(
                port,
                baud,
                words,
                boot_timeout=defaults.boot_timeout,
                ack_timeout=defaults.ack_timeout,
            )

            buffer.clear()
            frame_counter["n"] = 0
            frame_timing["last"] = None
            frame_timing["fps"] = 0.0
            open_serial(clear_buffers=False)

            status_var.set("Upload OK. Waiting for ADI0 / ADI1 frames...")
            log("[UPLOAD OK]\n")

        except SystemExit as e:
            status_var.set("Upload failed")
            log(f"[UPLOAD ERR] {e}\n")
            messagebox.showerror("Upload", str(e))
            try:
                open_serial(clear_buffers=True)
            except Exception:
                pass

        except Exception as e:
            status_var.set("Upload failed")
            log(f"[UPLOAD ERR] {e}\n")
            messagebox.showerror("Upload", str(e))
            try:
                open_serial(clear_buffers=True)
            except Exception:
                pass

        finally:
            uploading_ref["active"] = False

    ttk.Button(connection_buttons, text="Connect", command=connect).pack(side="left")
    ttk.Button(connection_buttons, text="Disconnect", command=disconnect).pack(side="left", padx=(6, 0))

    ttk.Button(actions, text="Upload / Run", command=upload).pack(side="left")
    ttk.Button(actions, text="Copy image", command=copy_image).pack(side="left", padx=(6, 0))
    ttk.Button(actions, text="Save image...", command=save_image).pack(side="left", padx=(6, 0))
    ttk.Button(actions, text="Clear", command=clear).pack(side="left", padx=(6, 0))

    def pump() -> None:
        if uploading_ref["active"]:
            root.after(10, pump)
            return

        ser = ser_ref["ser"]
        if ser is not None and ser.is_open:
            try:
                data = ser.read(4096)
                if data:
                    buffer.extend(data)
                    parse_frames()
            except Exception as e:
                log(f"[RX ERR] {e}\n")
                disconnect()

        root.after(10, pump)

    def parse_frames() -> None:
        while True:
            found = find_next_magic(buffer)

            if found is None:
                if len(buffer) > 3:
                    del buffer[:-3]
                return

            magic_pos, magic = found

            if magic_pos > 0:
                del buffer[:magic_pos]

            if len(buffer) < 6:
                return

            width = buffer[4]
            height = buffer[5]

            if width == 0 or height == 0:
                del buffer[:4]
                continue

            pixel_count = width * height

            if magic == MAGIC_ADI0:
                needed = 6 + pixel_count
                if len(buffer) < needed:
                    return
                pixels = bytes(buffer[6:needed])
                del buffer[:needed]
                draw_frame(width, height, pixels, magic)
                continue

            if magic == MAGIC_ADI1:
                packed_count = (pixel_count + 7) // 8
                needed = 6 + packed_count
                if len(buffer) < needed:
                    return
                packed = bytes(buffer[6:needed])
                pixels = unpack_adi1_payload(width, height, packed)
                del buffer[:needed]
                draw_frame(width, height, pixels, magic)
                continue

            del buffer[:4]

    def draw_frame(width: int, height: int, pixels: bytes, frame_kind: bytes) -> None:
        try:
            max_iter = parse_int(max_iter_var.get(), "Max iter", 1, 255)
            scale = parse_int(scale_var.get(), "Scale", 1, 32)
            palette = current_palette()
        except Exception:
            max_iter = defaults.max_iter
            scale = defaults.scale
            palette = defaults.palette

        img = tk.PhotoImage(width=width, height=height)
        rows = []

        display_width = width * scale
        display_height = height * scale
        rgb_bytes = bytearray(display_width * display_height * 3)

        for y in range(height):
            start = y * width
            row_hex = []
            row_rgb = []

            for x in range(width):
                rgb = frame_pixel_rgb(pixels[start + x], max_iter, palette, frame_kind)
                row_hex.append(rgb_hex(rgb))
                row_rgb.append(rgb)

            rows.append("{" + " ".join(row_hex) + "}")

            for sy in range(scale):
                dest = ((y * scale + sy) * display_width) * 3
                for r, g, b in row_rgb:
                    for _ in range(scale):
                        rgb_bytes[dest] = r
                        rgb_bytes[dest + 1] = g
                        rgb_bytes[dest + 2] = b
                        dest += 3

        img.put(" ".join(rows))

        image_ref["img"] = img.zoom(scale, scale)
        display_frame_ref["width"] = display_width
        display_frame_ref["height"] = display_height
        display_frame_ref["rgb"] = bytes(rgb_bytes)

        canvas.configure(width=display_width, height=display_height)
        canvas.delete("all")
        canvas.create_image(0, 0, image=image_ref["img"], anchor="nw")

        now = time.perf_counter()
        last = frame_timing["last"]
        fps = frame_timing["fps"]

        if isinstance(last, float):
            dt = now - last
            if dt > 0.0:
                instant_fps = 1.0 / dt
                if fps <= 0.0:
                    fps = instant_fps
                else:
                    fps = (fps * 0.85) + (instant_fps * 0.15)
                frame_timing["fps"] = fps

        frame_timing["last"] = now
        frame_counter["n"] += 1

        kind = frame_kind.decode("ascii", errors="replace")
        raw_size = width * height if frame_kind == MAGIC_ADI0 else (width * height + 7) // 8
        fps_text = "warming" if fps <= 0.0 else f"{fps:.1f}"

        status_var.set(
            f"Frame #{frame_counter['n']}: {kind}, {width}x{height}, "
            f"FPS={fps_text}, scale={scale}, image={display_width}x{display_height}, "
            f"palette={palette_label(palette)}, payload={raw_size} bytes, maxIter={max_iter}"
        )

    def on_close() -> None:
        close_serial()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    if defaults.upload:
        root.after(150, upload)
    elif defaults.port:
        root.after(150, connect)

    root.after(10, pump)
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", help="COM port, for example COM9. Without a port, the GUI opens disconnected.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--upload", help="Sutra program to upload before receiving ADI0 / ADI1 frames.")
    parser.add_argument("--width", type=int, default=64, help="Frame width, 1..255.")
    parser.add_argument("--height", type=int, default=64, help="Frame height, 1..255.")
    parser.add_argument("--max-iter", type=int, default=64, help="Iteration value treated as interior color, 1..255.")
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--palette", choices=PALETTE_KEYS, default=DEFAULT_PALETTE)
    parser.add_argument("--text", action="store_true", help="Deprecated. Use apps/bija/uart_terminal.py for text UART.")
    parser.add_argument("--boot-timeout", type=float, default=30.0)
    parser.add_argument("--ack-timeout", type=float, default=12.0)

    args = parser.parse_args()

    if args.text:
        raise SystemExit("Text mode was moved to apps/bija/uart_terminal.py.")

    if not 1 <= args.width <= 255:
        raise SystemExit("width must be in range 1..255.")

    if not 1 <= args.height <= 255:
        raise SystemExit("height must be in range 1..255.")

    if not 1 <= args.max_iter <= 255:
        raise SystemExit("max-iter must be in range 1..255.")

    if not 1 <= args.scale <= 32:
        raise SystemExit("scale must be in range 1..32.")

    source = DEFAULT_SOURCE
    upload = as_repo_path(resolve_path(args.upload)) if args.upload else None

    defaults = ViewerDefaults(
        port=args.port,
        baud=args.baud,
        source=source,
        upload=upload,
        width=args.width,
        height=args.height,
        max_iter=args.max_iter,
        scale=args.scale,
        palette=normalize_palette(args.palette),
        boot_timeout=args.boot_timeout,
        ack_timeout=args.ack_timeout,
    )

    run_gui(defaults)


if __name__ == "__main__":
    main()
    