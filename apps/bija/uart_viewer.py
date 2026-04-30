#!/usr/bin/env python3
"""
Adi UART Viewer

Single-window ADI0 frame viewer for Brahma-Bija.

Typical usage:

    py apps/bija/uart_viewer.py

    py apps/bija/uart_viewer.py COM9 --upload examples/bija/05_fractals/julia_uart.sutra

The text UART terminal is intentionally kept separate:

    py apps/bija/uart_terminal.py
"""

from __future__ import annotations

import argparse
import colorsys
import os
import sys
from dataclasses import dataclass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("pySerial is missing. Install it with: py -m pip install pyserial", file=sys.stderr)
    raise SystemExit(2)

from sutra_upload import assemble_file, upload_words_to_serial


DEFAULT_SOURCE = os.path.join("examples", "bija", "05_fractals", "julia_uart.sutra")
MAGIC = b"ADI0"


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
    gray: bool
    boot_timeout: float
    ack_timeout: float


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


def mandelbrot_color(v: int, max_iter: int) -> str:
    if v >= max_iter:
        return "#000000"
    if v <= 0:
        return "#07133d"

    t = max(0.0, min(1.0, v / max_iter))
    hue = 0.68 - 0.68 * (t ** 0.82)
    sat = 0.88
    val = 0.20 + 0.80 * (t ** 0.35)
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def gray_color(v: int, max_iter: int) -> str:
    if v >= max_iter:
        return "#000000"
    x = int(255 * max(0, min(max_iter, v)) / max_iter)
    return f"#{x:02x}{x:02x}{x:02x}"


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
    gray_var = tk.BooleanVar(value=defaults.gray)
    status_var = tk.StringVar(value="Disconnected")

    ser_ref: dict[str, serial.Serial | None] = {"ser": None}
    buffer = bytearray()
    image_ref: dict[str, tk.PhotoImage | None] = {"img": None}
    frame_counter = {"n": 0}

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
            initialdir=os.path.join(ROOT, "examples", "bija"),
            filetypes=[("Sutra", "*.sutra"), ("All files", "*.*")],
        )
        if path:
            file_var.set(as_repo_path(path))

    ttk.Button(program, text="Browse", command=browse).grid(row=0, column=2, sticky="e")
    program.columnconfigure(1, weight=1)

    render = ttk.LabelFrame(outer, text="ADI0 frame settings", padding=8)
    render.pack(fill="x", pady=(10, 0))

    ttk.Label(render, text="Width").grid(row=0, column=0, sticky="w")
    ttk.Entry(render, textvariable=width_var, width=7).grid(row=0, column=1, sticky="w", padx=(6, 14))

    ttk.Label(render, text="Height").grid(row=0, column=2, sticky="w")
    ttk.Entry(render, textvariable=height_var, width=7).grid(row=0, column=3, sticky="w", padx=(6, 14))

    ttk.Label(render, text="Max iter").grid(row=0, column=4, sticky="w")
    ttk.Entry(render, textvariable=max_iter_var, width=7).grid(row=0, column=5, sticky="w", padx=(6, 14))

    ttk.Label(render, text="Scale").grid(row=0, column=6, sticky="w")
    ttk.Entry(render, textvariable=scale_var, width=7).grid(row=0, column=7, sticky="w", padx=(6, 14))

    ttk.Checkbutton(render, text="Grayscale", variable=gray_var).grid(row=0, column=8, sticky="w")

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

    def current_params() -> tuple[str, int | None, int | None, int, int]:
        path = resolve_path(file_var.get())
        width = optional_byte(width_var.get(), "Width")
        height = optional_byte(height_var.get(), "Height")
        max_iter = parse_int(max_iter_var.get(), "Max iter", 1, 255)
        scale = parse_int(scale_var.get(), "Scale", 1, 32)
        return path, width, height, max_iter, scale

    def close_serial() -> None:
        ser = ser_ref["ser"]
        ser_ref["ser"] = None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def connect() -> None:
        try:
            close_serial()
            port = port_var.get().strip()
            if not port:
                raise ValueError("Port is empty.")
            baud = current_baud()
            ser = serial.Serial(port, baudrate=baud, timeout=0.01, write_timeout=2.0)
            ser_ref["ser"] = ser
            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception:
                pass
            buffer.clear()
            status_var.set(f"Connected: {port} @ {baud}")
            log(f"[OPEN] {port} @ {baud}\n")
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
        image_ref["img"] = None
        canvas.delete("all")
        log_box.delete("1.0", "end")
        status_var.set("Cleared")

    def upload() -> None:
        try:
            if ser_ref["ser"] is None or not ser_ref["ser"].is_open:
                connect()

            ser = ser_ref["ser"]
            if ser is None:
                return

            path, width, height, max_iter, _scale = current_params()
            words = assemble_file(
                path,
                width=width,
                height=height,
                max_iter=max_iter,
                graphics="auto",
            )

            status_var.set(f"Uploading: {os.path.basename(path)}")
            log(f"[UPLOAD] {path}\n")
            root.update_idletasks()

            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception:
                pass

            upload_words_to_serial(
                ser,
                words,
                boot_timeout=defaults.boot_timeout,
                ack_timeout=defaults.ack_timeout,
            )

            buffer.clear()
            frame_counter["n"] = 0
            status_var.set("Upload OK. Waiting for ADI0 frames...")
            log("[UPLOAD OK]\n")
        except SystemExit as e:
            status_var.set("Upload failed")
            log(f"[UPLOAD ERR] {e}\n")
            messagebox.showerror("Upload", str(e))
        except Exception as e:
            status_var.set("Upload failed")
            log(f"[UPLOAD ERR] {e}\n")
            messagebox.showerror("Upload", str(e))

    ttk.Button(connection_buttons, text="Connect", command=connect).pack(side="left")
    ttk.Button(connection_buttons, text="Disconnect", command=disconnect).pack(side="left", padx=(6, 0))

    ttk.Button(actions, text="Upload / Run", command=upload).pack(side="left")
    ttk.Button(actions, text="Clear", command=clear).pack(side="left", padx=(6, 0))

    def pump() -> None:
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
            magic_pos = buffer.find(MAGIC)
            if magic_pos < 0:
                if len(buffer) > 3:
                    del buffer[:-3]
                return

            if magic_pos > 0:
                del buffer[:magic_pos]

            if len(buffer) < 6:
                return

            width = buffer[4]
            height = buffer[5]

            if width == 0 or height == 0:
                del buffer[:4]
                continue

            needed = 6 + width * height
            if len(buffer) < needed:
                return

            pixels = bytes(buffer[6:needed])
            del buffer[:needed]
            draw_frame(width, height, pixels)

    def draw_frame(width: int, height: int, pixels: bytes) -> None:
        try:
            max_iter = parse_int(max_iter_var.get(), "Max iter", 1, 255)
            scale = parse_int(scale_var.get(), "Scale", 1, 32)
        except Exception:
            max_iter = defaults.max_iter
            scale = defaults.scale

        color_fn = gray_color if gray_var.get() else mandelbrot_color
        img = tk.PhotoImage(width=width, height=height)

        rows = []
        for y in range(height):
            start = y * width
            row = [color_fn(pixels[start + x], max_iter) for x in range(width)]
            rows.append("{" + " ".join(row) + "}")
        img.put(" ".join(rows))

        image_ref["img"] = img.zoom(scale, scale)
        canvas.configure(width=width * scale, height=height * scale)
        canvas.delete("all")
        canvas.create_image(0, 0, image=image_ref["img"], anchor="nw")

        frame_counter["n"] += 1
        status_var.set(f"Frame #{frame_counter['n']}: {width}x{height}, {len(pixels)} bytes, maxIter={max_iter}")

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
    parser.add_argument("--upload", help="Sutra program to upload before receiving ADI0 frames.")
    parser.add_argument("--width", type=int, default=64, help="ADI0 frame width, 1..255.")
    parser.add_argument("--height", type=int, default=64, help="ADI0 frame height, 1..255.")
    parser.add_argument("--max-iter", type=int, default=64, help="Iteration value treated as interior color, 1..255.")
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--gray", action="store_true", help="Use grayscale instead of the color palette.")
    parser.add_argument("--palette", action="store_true", help=argparse.SUPPRESS)
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
        gray=args.gray,
        boot_timeout=args.boot_timeout,
        ack_timeout=args.ack_timeout,
    )

    run_gui(defaults)


if __name__ == "__main__":
    main()
