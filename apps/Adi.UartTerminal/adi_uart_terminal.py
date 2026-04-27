#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

from sutra_upload import assemble_file, upload_words


def available_ports() -> list[str]:
    ports = [p.device for p in list_ports.comports()]

    def key(p: str):
        u = p.upper()
        if u.startswith("COM"):
            try:
                return (0, int(u[3:]))
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


def upload_text_program(port: str, baud: int, path: str, boot_timeout: float, ack_timeout: float) -> None:
    words = assemble_file(path, graphics="off")
    upload_words(port, baud, words, boot_timeout=boot_timeout, ack_timeout=ack_timeout)


def run_cli(port: str, baud: int, upload: str | None, boot_timeout: float, ack_timeout: float) -> None:
    if upload:
        upload_text_program(port, baud, resolve_path(upload), boot_timeout, ack_timeout)
    with serial.Serial(port, baudrate=baud, timeout=0.02, write_timeout=2.0) as ser:
        print(f"Adi UART Terminal: {port} @ {baud}. Ctrl+C kończy.")
        try:
            while True:
                data = ser.read(4096)
                if data:
                    sys.stdout.write(data.decode("utf-8", errors="replace"))
                    sys.stdout.flush()
                time.sleep(0.005)
        except KeyboardInterrupt:
            print()


def run_gui(default_port: str | None, default_upload: str | None, default_baud: int, boot_timeout: float, ack_timeout: float) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Adi UART Terminal")
    root.geometry("920x620")

    ports = available_ports()
    port_var = tk.StringVar(value=default_port or choose_default_port(ports))
    baud_var = tk.StringVar(value=str(default_baud))
    file_var = tk.StringVar(value=default_upload or os.path.join("examples", "04_uart", "echo_rx.sutra"))
    send_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="Rozłączony")

    ser_ref: dict[str, serial.Serial | None] = {"ser": None}

    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")

    ttk.Label(top, text="Port:").grid(row=0, column=0, sticky="w")
    port_box = ttk.Combobox(top, textvariable=port_var, values=ports, width=14)
    port_box.grid(row=0, column=1, sticky="w", padx=(4, 12))

    def refresh_ports() -> None:
        new_ports = available_ports()
        port_box["values"] = new_ports
        if port_var.get() not in new_ports:
            port_var.set(choose_default_port(new_ports))

    ttk.Button(top, text="Odśwież", command=refresh_ports).grid(row=0, column=2, sticky="w")

    ttk.Label(top, text="Baud:").grid(row=0, column=3, sticky="e", padx=(16, 4))
    ttk.Entry(top, textvariable=baud_var, width=10).grid(row=0, column=4, sticky="w")

    ttk.Label(top, text="Program:").grid(row=1, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(top, textvariable=file_var).grid(row=1, column=1, columnspan=4, sticky="we", padx=(4, 8), pady=(8, 0))

    def browse() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz program Sutra",
            initialdir=os.path.join(ROOT, "examples"),
            filetypes=[("Sutra", "*.sutra"), ("Wszystkie pliki", "*.*")],
        )
        if path:
            try:
                file_var.set(os.path.relpath(path, ROOT))
            except ValueError:
                file_var.set(path)

    ttk.Button(top, text="Wybierz...", command=browse).grid(row=1, column=5, sticky="e", pady=(8, 0))
    top.columnconfigure(1, weight=1)

    buttons = ttk.Frame(root, padding=(8, 0, 8, 8))
    buttons.pack(fill="x")

    term = ScrolledText(root, width=110, height=30, font=("Consolas", 10), wrap="char")
    term.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def log(text: str) -> None:
        term.insert("end", text)
        term.see("end")

    def current_baud() -> int:
        try:
            return int(baud_var.get().strip())
        except Exception:
            raise ValueError("Baud musi być liczbą")

    def close_serial() -> None:
        ser = ser_ref["ser"]
        ser_ref["ser"] = None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def open_serial() -> None:
        close_serial()
        port = port_var.get().strip()
        if not port:
            raise ValueError("Brak portu COM")
        baud = current_baud()
        ser_ref["ser"] = serial.Serial(port, baudrate=baud, timeout=0.01, write_timeout=2.0)
        status_var.set(f"Połączony: {port} @ {baud}")
        log(f"\n[OPEN] {port} @ {baud}\n")

    def connect() -> None:
        try:
            open_serial()
        except Exception as e:
            messagebox.showerror("Połączenie", str(e))
            status_var.set("Błąd połączenia")

    def disconnect() -> None:
        close_serial()
        status_var.set("Rozłączony")
        log("\n[CLOSE]\n")

    def upload() -> None:
        path = resolve_path(file_var.get().strip())
        port = port_var.get().strip()
        try:
            baud = current_baud()
            close_serial()
            status_var.set(f"Upload: {os.path.basename(path)}...")
            log(f"\n[UPLOAD] {path}\n")
            root.update_idletasks()
            upload_text_program(port, baud, path, boot_timeout, ack_timeout)
            log("[UPLOAD OK]\n")
            open_serial()
            status_var.set("Upload OK, terminal połączony")
        except SystemExit as e:
            status_var.set("Upload ERR")
            log(f"[UPLOAD ERR] {e}\n")
            messagebox.showerror("Upload", str(e))
            try:
                open_serial()
            except Exception:
                pass
        except Exception as e:
            status_var.set("Upload ERR")
            log(f"[UPLOAD ERR] {e}\n")
            messagebox.showerror("Upload", str(e))
            try:
                open_serial()
            except Exception:
                pass

    def clear() -> None:
        term.delete("1.0", "end")

    ttk.Button(buttons, text="Połącz", command=connect).pack(side="left")
    ttk.Button(buttons, text="Rozłącz", command=disconnect).pack(side="left", padx=(4, 0))
    ttk.Button(buttons, text="Upload tekstowego .sutra", command=upload).pack(side="left", padx=(12, 0))
    ttk.Button(buttons, text="Wyczyść", command=clear).pack(side="left", padx=(4, 0))

    send_frame = ttk.Frame(root, padding=(8, 0, 8, 8))
    send_frame.pack(fill="x")
    ttk.Label(send_frame, text="Wyślij:").pack(side="left")
    send_entry = ttk.Entry(send_frame, textvariable=send_var)
    send_entry.pack(side="left", fill="x", expand=True, padx=6)

    def send(add_lf: bool = False) -> None:
        ser = ser_ref["ser"]
        if ser is None or not ser.is_open:
            try:
                open_serial()
                ser = ser_ref["ser"]
            except Exception as e:
                messagebox.showerror("Wyślij", str(e))
                return
        text = send_var.get()
        if add_lf:
            text += "\n"
        if not text:
            return
        data = text.encode("utf-8", errors="replace")
        try:
            ser.write(data)
            ser.flush()
            log(f"\n[TX] {data!r}\n")
            send_var.set("")
        except Exception as e:
            messagebox.showerror("Wyślij", str(e))
            disconnect()

    ttk.Button(send_frame, text="Wyślij", command=lambda: send(False)).pack(side="left")
    ttk.Button(send_frame, text="Wyślij + LF", command=lambda: send(True)).pack(side="left", padx=(4, 0))
    send_entry.bind("<Return>", lambda _e: send(False))
    send_entry.bind("<Control-Return>", lambda _e: send(True))

    ttk.Label(root, textvariable=status_var).pack(fill="x", padx=8, pady=(0, 8))

    def pump() -> None:
        ser = ser_ref["ser"]
        if ser is not None and ser.is_open:
            try:
                data = ser.read(4096)
                if data:
                    log(data.decode("utf-8", errors="replace"))
            except Exception as e:
                log(f"\n[RX ERR] {e}\n")
                disconnect()
        root.after(10, pump)

    def on_close() -> None:
        close_serial()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    if default_upload:
        root.after(150, upload)
    else:
        root.after(150, connect)
    root.after(10, pump)
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", help="np. COM9; bez portu odpala GUI")
    parser.add_argument("source", nargs="?", help="opcjonalny zwykły program .sutra do uploadu")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--boot-timeout", type=float, default=30.0)
    parser.add_argument("--ack-timeout", type=float, default=12.0)
    parser.add_argument("--no-gui", action="store_true")
    args = parser.parse_args()

    if args.no_gui:
        if not args.port:
            raise SystemExit("Podaj port, np. COM9")
        run_cli(args.port, args.baud, args.source, args.boot_timeout, args.ack_timeout)
        return

    if args.port and args.source:
        run_gui(args.port, args.source, args.baud, args.boot_timeout, args.ack_timeout)
    elif args.port:
        run_gui(args.port, None, args.baud, args.boot_timeout, args.ack_timeout)
    else:
        run_gui(None, None, args.baud, args.boot_timeout, args.ack_timeout)


if __name__ == "__main__":
    main()
