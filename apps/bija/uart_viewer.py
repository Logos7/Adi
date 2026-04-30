#!/usr/bin/env python3
"""
Adi UART Viewer — UART receiver/uploader for Brahma-Bija.

GUI:
    py apps/bija/uart_viewer.py

CLI, image:
    py apps/bija/uart_viewer.py COM9 --upload examples/bija/05_fractals/julia_uart.sutra --width 96 --height 64 --max-iter 80 --scale 4

CLI, text:
    py apps/bija/uart_viewer.py COM9 --text

Frame protocol:
    magic: 4 bytes  b"ADI0"
    width: 1 byte
    height: 1 byte
    pixels: width*height bytes
"""

from __future__ import annotations

import argparse
import colorsys
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("Brak pyserial. Zainstaluj: py -m pip install pyserial", file=sys.stderr)
    raise SystemExit(2)

from sutra_upload import assemble_file, upload_words, upload_words_to_serial


def available_ports() -> list[str]:
    ports = [p.device for p in list_ports.comports()]

    def key(p: str):
        if p.upper().startswith("COM"):
            try:
                return (0, int(p[3:]))
            except ValueError:
                return (0, 9999)
        return (1, p)

    return sorted(ports, key=key)


def choose_default_port(ports: list[str]) -> str:
    if "COM9" in ports:
        return "COM9"
    if "COM8" in ports:
        return "COM8"
    return ports[0] if ports else "COM9"


def resolve_path(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def upload_on_port(
    port: str,
    baud: int,
    path: str,
    boot_timeout: float,
    ack_timeout: float,
    width: int | None = None,
    height: int | None = None,
    max_iter: int | None = None,
    graphics: str = "auto",
) -> None:
    words = assemble_file(path, width=width, height=height, max_iter=max_iter, graphics=graphics)
    upload_words(port, baud, words, boot_timeout=boot_timeout, ack_timeout=ack_timeout)


def upload_on_serial(
    ser,
    path: str,
    boot_timeout: float,
    ack_timeout: float,
    width: int | None = None,
    height: int | None = None,
    max_iter: int | None = None,
    graphics: str = "auto",
) -> None:
    words = assemble_file(path, width=width, height=height, max_iter=max_iter, graphics=graphics)
    upload_words_to_serial(ser, words, boot_timeout=boot_timeout, ack_timeout=ack_timeout)


def run_text(
    port: str,
    baud: int,
    upload: str | None = None,
    boot_timeout: float = 30.0,
    ack_timeout: float = 12.0,
    width: int | None = None,
    height: int | None = None,
    max_iter: int | None = None,
    graphics: str = "off",
):
    if upload:
        upload_on_port(port, baud, upload, boot_timeout, ack_timeout, width, height, max_iter, graphics=graphics)
    with serial.Serial(port, baudrate=baud, timeout=0.2) as ser:
        print(f"Odbieram tekst z {port} @ {baud} 8N1. Ctrl+C kończy.")
        while True:
            data = ser.read(256)
            if data:
                try:
                    print(data.decode("ascii", errors="replace"), end="", flush=True)
                except Exception:
                    print(data.hex(" "), flush=True)


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


def parse_int_var(value: str, name: str, min_value: int, max_value: int) -> int:
    try:
        x = int(value.strip())
    except Exception:
        raise ValueError(f"{name}: wpisz liczbę całkowitą")
    if x < min_value or x > max_value:
        raise ValueError(f"{name}: zakres {min_value}..{max_value}")
    return x


def run_frames(
    port: str,
    baud: int,
    scale: int,
    palette: bool,
    max_iter: int,
    upload: str | None = None,
    boot_timeout: float = 30.0,
    ack_timeout: float = 12.0,
    width: int | None = None,
    height: int | None = None,
):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Adi UART Fractal Viewer")

    ser = serial.Serial(port, baudrate=baud, timeout=0.01, write_timeout=2.0)
    buffer = bytearray()
    image_ref = {"img": None}
    frame_counter = {"n": 0}

    file_var = tk.StringVar(value=upload or os.path.join("examples", "bija", "05_fractals", "julia_uart.sutra"))
    width_var = tk.StringVar(value=str(width if width is not None else 64))
    height_var = tk.StringVar(value=str(height if height is not None else 64))
    max_iter_var = tk.StringVar(value=str(max_iter))
    scale_var = tk.StringVar(value=str(scale))
    gray_var = tk.BooleanVar(value=not palette)
    status_var = tk.StringVar(value=f"Czekam na ramki ADI0 z {port} @ {baud}...")

    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")

    ttk.Label(top, text="Program:").grid(row=0, column=0, sticky="w")
    file_entry = ttk.Entry(top, textvariable=file_var)
    file_entry.grid(row=0, column=1, columnspan=7, sticky="we", padx=6)

    def browse():
        path = filedialog.askopenfilename(
            title="Wybierz program Sutra",
            initialdir=os.path.join(ROOT, "examples", "bija"),
            filetypes=[("Sutra", "*.sutra"), ("Wszystkie pliki", "*.*")],
        )
        if path:
            try:
                file_var.set(os.path.relpath(path, ROOT))
            except ValueError:
                file_var.set(path)

    ttk.Button(top, text="Wybierz...", command=browse).grid(row=0, column=8, sticky="e")

    ttk.Label(top, text="W:").grid(row=1, column=0, sticky="e")
    ttk.Entry(top, textvariable=width_var, width=6).grid(row=1, column=1, sticky="w")
    ttk.Label(top, text="H:").grid(row=1, column=2, sticky="e")
    ttk.Entry(top, textvariable=height_var, width=6).grid(row=1, column=3, sticky="w")
    ttk.Label(top, text="Iter:").grid(row=1, column=4, sticky="e")
    ttk.Entry(top, textvariable=max_iter_var, width=6).grid(row=1, column=5, sticky="w")
    ttk.Label(top, text="Skala:").grid(row=1, column=6, sticky="e")
    ttk.Entry(top, textvariable=scale_var, width=6).grid(row=1, column=7, sticky="w")
    ttk.Checkbutton(top, text="Gray", variable=gray_var).grid(row=1, column=8, sticky="w", padx=(8, 0))

    label = ttk.Label(root, textvariable=status_var)
    label.pack(fill="x", padx=8)

    canvas = tk.Canvas(root, width=320, height=240)
    canvas.pack(padx=8, pady=8)

    def current_params() -> tuple[str, int, int, int, int]:
        path = resolve_path(file_var.get().strip())
        w = parse_int_var(width_var.get(), "W", 1, 255)
        h = parse_int_var(height_var.get(), "H", 1, 255)
        mi = parse_int_var(max_iter_var.get(), "Iter", 1, 255)
        sc = parse_int_var(scale_var.get(), "Skala", 1, 32)
        return path, w, h, mi, sc

    def do_upload():
        nonlocal buffer
        try:
            path, w, h, mi, sc = current_params()
            status_var.set(f"Uploaduję {os.path.basename(path)} jako {w}x{h}, iter={mi}...")
            root.update_idletasks()
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            upload_on_serial(ser, path, boot_timeout, ack_timeout, width=w, height=h, max_iter=mi, graphics="auto")
            buffer.clear()
            frame_counter["n"] = 0
            status_var.set("Upload OK. Czekam na pierwszą ramkę ADI0...")
        except SystemExit as e:
            messagebox.showerror("Upload", str(e))
            status_var.set("Upload nieudany")
        except Exception as e:
            messagebox.showerror("Upload", str(e))
            status_var.set("Upload nieudany")

    ttk.Button(top, text="Upload / przeładuj", command=do_upload).grid(row=2, column=0, columnspan=3, sticky="we", pady=(8, 0))
    ttk.Button(top, text="Wyczyść bufor", command=lambda: buffer.clear()).grid(row=2, column=3, columnspan=2, sticky="we", pady=(8, 0), padx=4)
    top.columnconfigure(1, weight=1)

    def pump():
        nonlocal buffer
        data = ser.read(4096)
        if data:
            buffer.extend(data)

        while True:
            magic_pos = buffer.find(b"ADI0")
            if magic_pos < 0:
                if len(buffer) > 3:
                    del buffer[:-3]
                break
            if magic_pos > 0:
                del buffer[:magic_pos]
            if len(buffer) < 6:
                break
            w = buffer[4]
            h = buffer[5]
            if w == 0 or h == 0:
                del buffer[:4]
                continue
            need = 6 + w * h
            if len(buffer) < need:
                break
            pixels = bytes(buffer[6:need])
            del buffer[:need]
            draw_frame(w, h, pixels)

        root.after(10, pump)

    def draw_frame(w: int, h: int, pixels: bytes):
        try:
            mi = parse_int_var(max_iter_var.get(), "Iter", 1, 255)
            sc = parse_int_var(scale_var.get(), "Skala", 1, 32)
        except Exception:
            mi = max_iter
            sc = scale
        color_fn = gray_color if gray_var.get() else mandelbrot_color
        frame_counter["n"] += 1
        status_var.set(f"Ramka #{frame_counter['n']} — {w}x{h}, {len(pixels)} pikseli, maxIter={mi}")
        img = tk.PhotoImage(width=w, height=h)
        rows = []
        for y in range(h):
            row = []
            base = y * w
            for x in range(w):
                row.append(color_fn(pixels[base + x], mi))
            rows.append("{" + " ".join(row) + "}")
        img.put(" ".join(rows))
        image_ref["img"] = img.zoom(sc, sc)
        canvas.configure(width=w * sc, height=h * sc)
        canvas.delete("all")
        canvas.create_image(0, 0, image=image_ref["img"], anchor="nw")

    try:
        if upload:
            do_upload()
        root.after(10, pump)
        root.mainloop()
    finally:
        ser.close()


def run_text_window(
    port: str,
    baud: int,
    upload: str | None = None,
    boot_timeout: float = 30.0,
    ack_timeout: float = 12.0,
):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Adi UART Terminal / Uploader")

    ser = serial.Serial(port, baudrate=baud, timeout=0.01, write_timeout=2.0)
    file_var = tk.StringVar(value=upload or os.path.join("examples", "04_uart", "hello_loop.sutra"))
    status_var = tk.StringVar(value=f"Terminal UART {port} @ {baud}. Tryb zwykły: bez patchowania WIDTH/HEIGHT/ITER.")
    send_var = tk.StringVar(value="")

    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")

    ttk.Label(top, text="Program:").grid(row=0, column=0, sticky="w")
    file_entry = ttk.Entry(top, textvariable=file_var)
    file_entry.grid(row=0, column=1, sticky="we", padx=6)

    def browse():
        path = filedialog.askopenfilename(
            title="Wybierz program Sutra",
            initialdir=os.path.join(ROOT, "examples", "bija"),
            filetypes=[("Sutra", "*.sutra"), ("Wszystkie pliki", "*.*")],
        )
        if path:
            try:
                file_var.set(os.path.relpath(path, ROOT))
            except ValueError:
                file_var.set(path)

    ttk.Button(top, text="Wybierz...", command=browse).grid(row=0, column=2, sticky="e")

    term = ScrolledText(root, width=96, height=28, font=("Consolas", 10))
    term.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def write_log(text: str):
        term.insert("end", text)
        term.see("end")

    def do_upload():
        try:
            path = resolve_path(file_var.get().strip())
            status_var.set(f"Uploaduję zwykły program: {os.path.basename(path)}...")
            write_log(f"\n[UPLOAD] {path}\n")
            root.update_idletasks()
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            upload_on_serial(ser, path, boot_timeout, ack_timeout, graphics="off")
            status_var.set("Upload OK. Program działa, terminal odbiera UART.")
            write_log("[UPLOAD OK]\n")
        except SystemExit as e:
            messagebox.showerror("Upload", str(e))
            status_var.set("Upload nieudany")
            write_log(f"[UPLOAD ERR] {e}\n")
        except Exception as e:
            messagebox.showerror("Upload", str(e))
            status_var.set("Upload nieudany")
            write_log(f"[UPLOAD ERR] {e}\n")

    ttk.Button(top, text="Upload / przeładuj zwykły program", command=do_upload).grid(row=1, column=0, columnspan=2, sticky="we", pady=(8, 0))
    ttk.Button(top, text="Wyczyść terminal", command=lambda: term.delete("1.0", "end")).grid(row=1, column=2, sticky="we", pady=(8, 0))

    send_frame = ttk.Frame(root, padding=(8, 0, 8, 8))
    send_frame.pack(fill="x")
    ttk.Label(send_frame, text="Wyślij do FPGA:").pack(side="left")
    send_entry = ttk.Entry(send_frame, textvariable=send_var)
    send_entry.pack(side="left", fill="x", expand=True, padx=6)

    def do_send(add_newline: bool = False):
        text = send_var.get()
        if add_newline:
            text += "\n"
        if not text:
            return
        data = text.encode("utf-8", errors="replace")
        ser.write(data)
        ser.flush()
        write_log(f"\n[TX] {data!r}\n")
        send_var.set("")

    ttk.Button(send_frame, text="Wyślij", command=lambda: do_send(False)).pack(side="left")
    ttk.Button(send_frame, text="Wyślij + LF", command=lambda: do_send(True)).pack(side="left", padx=(4, 0))
    send_entry.bind("<Return>", lambda _e: do_send(False))
    send_entry.bind("<Control-Return>", lambda _e: do_send(True))

    top.columnconfigure(1, weight=1)

    ttk.Label(root, textvariable=status_var).pack(fill="x", padx=8, pady=(0, 8))

    def pump():
        data = ser.read(4096)
        if data:
            try:
                write_log(data.decode("utf-8", errors="replace"))
            except Exception:
                write_log(data.hex(" ") + "\n")
        root.after(10, pump)

    try:
        if upload:
            root.after(100, do_upload)
        root.after(10, pump)
        root.mainloop()
    finally:
        ser.close()


def run_launcher() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    result = {"start": False}
    root = tk.Tk()
    root.title("Adi UART Viewer — launcher")
    root.geometry("720x330")

    ports = available_ports()
    port_var = tk.StringVar(value=choose_default_port(ports))
    baud_var = tk.StringVar(value="115200")
    file_var = tk.StringVar(value=os.path.join("examples", "bija", "05_fractals", "julia_uart.sutra"))
    width_var = tk.StringVar(value="64")
    height_var = tk.StringVar(value="64")
    scale_var = tk.StringVar(value="4")
    max_iter_var = tk.StringVar(value="64")
    upload_var = tk.BooleanVar(value=True)
    gray_var = tk.BooleanVar(value=False)
    text_var = tk.BooleanVar(value=False)

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="Port COM:").grid(row=0, column=0, sticky="w")
    port_box = ttk.Combobox(frm, textvariable=port_var, values=ports, width=18)
    port_box.grid(row=0, column=1, sticky="we", padx=6)

    def refresh_ports():
        new_ports = available_ports()
        port_box["values"] = new_ports
        if port_var.get() not in new_ports:
            port_var.set(choose_default_port(new_ports))

    ttk.Button(frm, text="Odśwież", command=refresh_ports).grid(row=0, column=2, sticky="w")

    ttk.Label(frm, text="Baud:").grid(row=1, column=0, sticky="w")
    ttk.Entry(frm, textvariable=baud_var, width=20).grid(row=1, column=1, sticky="w", padx=6)

    ttk.Checkbutton(frm, text="Najpierw uploaduj program .sutra", variable=upload_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

    ttk.Label(frm, text="Program .sutra:").grid(row=3, column=0, sticky="w")
    ttk.Entry(frm, textvariable=file_var).grid(row=3, column=1, sticky="we", padx=6)

    def browse():
        path = filedialog.askopenfilename(
            title="Wybierz program Sutra",
            initialdir=os.path.join(ROOT, "examples", "bija"),
            filetypes=[("Sutra", "*.sutra"), ("Wszystkie pliki", "*.*")],
        )
        if path:
            try:
                file_var.set(os.path.relpath(path, ROOT))
            except ValueError:
                file_var.set(path)

    ttk.Button(frm, text="Wybierz...", command=browse).grid(row=3, column=2, sticky="w")

    ttk.Label(frm, text="Szerokość:").grid(row=4, column=0, sticky="w")
    ttk.Entry(frm, textvariable=width_var, width=20).grid(row=4, column=1, sticky="w", padx=6)

    ttk.Label(frm, text="Wysokość:").grid(row=5, column=0, sticky="w")
    ttk.Entry(frm, textvariable=height_var, width=20).grid(row=5, column=1, sticky="w", padx=6)

    ttk.Label(frm, text="Skala:").grid(row=6, column=0, sticky="w")
    ttk.Entry(frm, textvariable=scale_var, width=20).grid(row=6, column=1, sticky="w", padx=6)

    ttk.Label(frm, text="Max iter:").grid(row=7, column=0, sticky="w")
    ttk.Entry(frm, textvariable=max_iter_var, width=20).grid(row=7, column=1, sticky="w", padx=6)

    ttk.Checkbutton(frm, text="Tryb tekstowy", variable=text_var).grid(row=8, column=0, sticky="w", pady=(8, 0))
    ttk.Checkbutton(frm, text="Grayscale", variable=gray_var).grid(row=8, column=1, sticky="w", pady=(8, 0))

    frm.columnconfigure(1, weight=1)

    def start():
        try:
            result.update(
                start=True,
                port=port_var.get().strip(),
                baud=int(baud_var.get()),
                upload=file_var.get().strip() if upload_var.get() else None,
                width=parse_int_var(width_var.get(), "Szerokość", 1, 255),
                height=parse_int_var(height_var.get(), "Wysokość", 1, 255),
                scale=parse_int_var(scale_var.get(), "Skala", 1, 32),
                max_iter=parse_int_var(max_iter_var.get(), "Max iter", 1, 255),
                gray=gray_var.get(),
                text=text_var.get(),
            )
            if not result["port"]:
                raise ValueError("Brak portu COM")
        except Exception as e:
            messagebox.showerror("Adi UART Viewer", str(e))
            return
        root.destroy()

    ttk.Button(frm, text="Start", command=start).grid(row=9, column=0, columnspan=3, pady=14)
    root.mainloop()

    if not result.get("start"):
        return

    upload = result["upload"]
    if upload:
        upload = resolve_path(upload)
    if result["text"]:
        run_text_window(result["port"], result["baud"], upload)
    else:
        run_frames(
            result["port"],
            result["baud"],
            result["scale"],
            not result["gray"],
            result["max_iter"],
            upload,
            width=result["width"],
            height=result["height"],
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", help="np. COM9 albo /dev/ttyUSB0; bez portu odpala GUI launcher")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--text", action="store_true", help="tekstowy monitor UART")
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument("--palette", action="store_true", help="kompatybilność: paleta jest domyślna")
    parser.add_argument("--gray", action="store_true", help="użyj grayscale zamiast palety")
    parser.add_argument("--width", type=int, default=None, help="nadpisz szerokość przykładowego fraktala, 1..255")
    parser.add_argument("--height", type=int, default=None, help="nadpisz wysokość przykładowego fraktala, 1..255")
    parser.add_argument("--max-iter", type=int, default=64, help="wartość iteracji traktowana jako wnętrze; domyślnie 64")
    parser.add_argument("--upload", help="najpierw załaduj .sutra przez bootloader UART, potem odbieraj dane")
    parser.add_argument("--boot-timeout", type=float, default=30.0, help="czas szukania bootloadera")
    parser.add_argument("--ack-timeout", type=float, default=12.0, help="czas czekania na OK/ERR")
    args = parser.parse_args()

    if not args.port:
        run_launcher()
        return

    upload = resolve_path(args.upload) if args.upload else None
    if args.text:
        run_text(args.port, args.baud, upload, args.boot_timeout, args.ack_timeout, args.width, args.height, args.max_iter)
    else:
        run_frames(
            args.port,
            args.baud,
            args.scale,
            not args.gray,
            args.max_iter,
            upload,
            args.boot_timeout,
            args.ack_timeout,
            args.width,
            args.height,
        )


if __name__ == "__main__":
    main()
