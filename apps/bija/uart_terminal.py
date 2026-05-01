#!/usr/bin/env python3
"""
Adi UART Terminal

Single-window text UART terminal and uploader for Brahma-Bija.

Typical usage:

    py apps/bija/uart_terminal.py

    py apps/bija/uart_terminal.py COM9 examples/bija/basics/echo_rx.sutra

CLI mode:

    py apps/bija/uart_terminal.py COM9 examples/bija/basics/echo_rx.sutra --no-gui
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("pySerial is missing. Install it with: py -m pip install pyserial", file=sys.stderr)
    raise SystemExit(2)

from sutra_upload import ACK_ERR, ACK_OK, ACK_READY, assemble_file, upload_words


BOOT_ACKS = (ACK_READY, ACK_OK, ACK_ERR)
BOOT_PREFIX = b"ADI_BOOT_"
FRAME_MAGIC = b"ADI0"
DEFAULT_SOURCE = os.path.join("examples", "bija", "basics", "echo_rx.sutra")
MAX_TERMINAL_CHARS = 200_000


def app_state_file() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Adi", "uart_terminal_state.json")


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


class TerminalRxFilter:
    def __init__(self) -> None:
        self._buf = bytearray()
        self.dropped_frames = 0
        self.dropped_bytes = 0

    def feed(self, data: bytes) -> bytes:
        if not data:
            return b""

        self._buf += data
        out = bytearray()

        while self._buf:
            removed = False

            for ack in BOOT_ACKS:
                if self._buf.startswith(ack):
                    del self._buf[:len(ack)]
                    removed = True
                    break

            if removed:
                continue

            if any(ack.startswith(bytes(self._buf)) for ack in BOOT_ACKS):
                break

            if self._buf.startswith(BOOT_PREFIX):
                newline = self._buf.find(b"\n")

                if newline < 0:
                    if len(self._buf) < 80:
                        break

                    self.dropped_bytes += 1
                    del self._buf[0]
                    continue

                self.dropped_bytes += newline + 1
                del self._buf[:newline + 1]
                continue

            if self._buf.startswith(FRAME_MAGIC):
                if len(self._buf) < 6:
                    break

                width = self._buf[4]
                height = self._buf[5]

                if width == 0 or height == 0:
                    self.dropped_bytes += 4
                    del self._buf[:4]
                    continue

                size = 6 + width * height

                if len(self._buf) < size:
                    break

                self.dropped_frames += 1
                self.dropped_bytes += size
                del self._buf[:size]
                continue

            magic_pos = self._buf.find(FRAME_MAGIC)

            if magic_pos > 0:
                chunk = bytes(self._buf[:magic_pos])
                del self._buf[:magic_pos]
                out += self._sanitize_text(chunk)
                continue

            if len(self._buf) < 4 and FRAME_MAGIC.startswith(bytes(self._buf)):
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


def parse_baud(value: str) -> int:
    try:
        baud = int(value.strip())
    except Exception:
        raise ValueError("Baud must be an integer.")

    if baud < 1 or baud > 3_000_000:
        raise ValueError("Baud must be in range 1..3000000.")

    return baud


def upload_text_program(port: str, baud: int, path: str, boot_timeout: float, ack_timeout: float) -> None:
    words = assemble_file(path, graphics="off")
    upload_words(port, baud, words, boot_timeout=boot_timeout, ack_timeout=ack_timeout)


def run_cli(port: str, baud: int, upload: str | None, boot_timeout: float, ack_timeout: float) -> None:
    if upload:
        upload_text_program(port, baud, resolve_path(upload), boot_timeout, ack_timeout)

    rx_filter = TerminalRxFilter()
    last_report = time.monotonic()

    with serial.Serial(port, baudrate=baud, timeout=0.02, write_timeout=2.0) as ser:
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception:
            pass

        print(f"Adi UART Terminal: {port} @ {baud}. Ctrl+C exits.")

        try:
            while True:
                data = ser.read(1024)

                if data:
                    clean = rx_filter.feed(data)

                    if clean:
                        sys.stdout.write(clean.decode("utf-8", errors="replace"))
                        sys.stdout.flush()

                now = time.monotonic()

                if now - last_report >= 2.0 and rx_filter.dropped_frames:
                    print(f"\n[RX] dropped {rx_filter.dropped_frames} ADI0 frame(s)\n", end="")
                    last_report = now

                time.sleep(0.005)
        except KeyboardInterrupt:
            print()


def run_gui(
    default_port: str | None,
    default_upload: str | None,
    default_baud: int,
    boot_timeout: float,
    ack_timeout: float,
) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Adi UART Terminal")
    root.geometry("1000x800")

    ports = available_ports()

    port_var = tk.StringVar(value=default_port or choose_default_port(ports))
    baud_var = tk.StringVar(value=str(default_baud))
    file_var = tk.StringVar(value=default_upload or DEFAULT_SOURCE)
    send_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="Disconnected")

    ser_ref: dict[str, serial.Serial | None] = {"ser": None}
    rx_filter = TerminalRxFilter()
    last_drop_report = {"frames": 0, "bytes": 0}

    outer = ttk.Frame(root, padding=10)
    outer.pack(fill="both", expand=True)

    connection = ttk.LabelFrame(outer, text="Connection", padding=8)
    connection.pack(fill="x")

    ttk.Label(connection, text="Port").grid(row=0, column=0, sticky="w")

    port_box = ttk.Combobox(connection, textvariable=port_var, values=ports, width=16)
    port_box.grid(row=0, column=1, sticky="w", padx=(6, 12))

    ttk.Label(connection, text="Baud").grid(row=0, column=3, sticky="e", padx=(18, 6))
    ttk.Entry(connection, textvariable=baud_var, width=10).grid(row=0, column=4, sticky="w")

    connection_buttons = ttk.Frame(connection)
    connection_buttons.grid(row=0, column=5, sticky="e", padx=(18, 0))

    connection.columnconfigure(6, weight=1)

    program = ttk.LabelFrame(outer, text="Program", padding=8)
    program.pack(fill="x", pady=(10, 0))

    ttk.Label(program, text="Sutra file").grid(row=0, column=0, sticky="w")
    ttk.Entry(program, textvariable=file_var).grid(row=0, column=1, sticky="we", padx=(6, 8))

    program.columnconfigure(1, weight=1)

    actions = ttk.LabelFrame(outer, text="Actions", padding=8)
    actions.pack(fill="x", pady=(10, 0))

    terminal_frame = ttk.LabelFrame(outer, text="Terminal", padding=8)
    terminal_frame.pack(fill="both", expand=True, pady=(10, 0))

    terminal = ScrolledText(terminal_frame, width=120, height=28, font=("Consolas", 10), wrap="char")
    terminal.pack(fill="both", expand=True)

    send_frame = ttk.LabelFrame(outer, text="Send", padding=8)
    send_frame.pack(fill="x", pady=(10, 0))

    ttk.Label(send_frame, text="Text").pack(side="left")

    send_entry = ttk.Entry(send_frame, textvariable=send_var)
    send_entry.pack(side="left", fill="x", expand=True, padx=(6, 8))

    ttk.Label(outer, textvariable=status_var).pack(fill="x", pady=(8, 0))

    def trim_terminal() -> None:
        try:
            chars = len(terminal.get("1.0", "end-1c"))
            if chars > MAX_TERMINAL_CHARS:
                terminal.delete("1.0", "2000.0")
        except Exception:
            pass

    def log(text: str) -> None:
        terminal.insert("end", text)
        terminal.see("end")
        trim_terminal()

    def refresh_ports() -> None:
        new_ports = available_ports()
        port_box["values"] = new_ports

        if port_var.get() not in new_ports:
            port_var.set(choose_default_port(new_ports))

        log(f"\n[PORTS] {', '.join(new_ports) if new_ports else 'none'}\n")

    def browse() -> None:
        path = filedialog.askopenfilename(
            title="Select Sutra program",
            initialdir=load_last_sutra_dir(),
            filetypes=[("Sutra", "*.sutra"), ("All files", "*.*")],
        )

        if path:
            save_last_sutra_dir(os.path.dirname(path))
            file_var.set(as_repo_path(path))

    def current_baud() -> int:
        return parse_baud(baud_var.get())

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

        status_var.set(f"Connected: {port} @ {baud}")
        log(f"\n[OPEN] {port} @ {baud}\n")

    def connect() -> None:
        try:
            open_serial(clear_buffers=True)
        except Exception as e:
            status_var.set("Connection error")
            messagebox.showerror("Connection", str(e))

    def disconnect() -> None:
        close_serial()
        status_var.set("Disconnected")
        log("\n[CLOSE]\n")

    def upload() -> None:
        path = resolve_path(file_var.get())
        port = port_var.get().strip()

        try:
            if not port:
                raise ValueError("Port is empty.")

            baud = current_baud()
            close_serial()

            status_var.set(f"Uploading: {os.path.basename(path)}")
            log(f"\n[UPLOAD] {path}\n")
            root.update_idletasks()

            upload_text_program(port, baud, path, boot_timeout, ack_timeout)

            log("[UPLOAD OK]\n")
            open_serial(clear_buffers=True)
            status_var.set("Upload OK. Terminal connected.")
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

    def clear() -> None:
        terminal.delete("1.0", "end")
        status_var.set("Cleared")

    def send(add_lf: bool = False) -> None:
        ser = ser_ref["ser"]

        if ser is None or not ser.is_open:
            try:
                open_serial(clear_buffers=True)
                ser = ser_ref["ser"]
            except Exception as e:
                messagebox.showerror("Send", str(e))
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
            messagebox.showerror("Send", str(e))
            disconnect()

    def report_drops() -> None:
        if rx_filter.dropped_frames != last_drop_report["frames"]:
            last_drop_report["frames"] = rx_filter.dropped_frames
            last_drop_report["bytes"] = rx_filter.dropped_bytes
            status_var.set(
                f"Connected. Dropped {rx_filter.dropped_frames} ADI0 frame(s), "
                f"{rx_filter.dropped_bytes} byte(s)."
            )

    def pump() -> None:
        ser = ser_ref["ser"]

        if ser is not None and ser.is_open:
            try:
                data = ser.read(1024)

                if data:
                    clean = rx_filter.feed(data)

                    if clean:
                        log(clean.decode("utf-8", errors="replace"))

                    report_drops()
            except Exception as e:
                log(f"\n[RX ERR] {e}\n")
                disconnect()

        root.after(25, pump)

    def on_close() -> None:
        close_serial()
        root.destroy()

    ttk.Button(connection, text="Refresh", command=refresh_ports).grid(row=0, column=2, sticky="w")

    ttk.Button(connection_buttons, text="Connect", command=connect).pack(side="left")
    ttk.Button(connection_buttons, text="Disconnect", command=disconnect).pack(side="left", padx=(6, 0))

    ttk.Button(program, text="Browse", command=browse).grid(row=0, column=2, sticky="e")

    ttk.Button(actions, text="Upload / Run", command=upload).pack(side="left")
    ttk.Button(actions, text="Clear terminal", command=clear).pack(side="left", padx=(6, 0))

    ttk.Button(send_frame, text="Send", command=lambda: send(False)).pack(side="left")
    ttk.Button(send_frame, text="Send + LF", command=lambda: send(True)).pack(side="left", padx=(6, 0))

    send_entry.bind("<Return>", lambda _e: send(False))
    send_entry.bind("<Control-Return>", lambda _e: send(True))

    root.protocol("WM_DELETE_WINDOW", on_close)

    if default_upload:
        root.after(150, upload)
    elif default_port:
        root.after(150, connect)

    root.after(25, pump)
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", help="COM port, for example COM9. Without a port, the GUI opens disconnected.")
    parser.add_argument("source", nargs="?", help="Optional text-mode Sutra program to upload.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--boot-timeout", type=float, default=30.0)
    parser.add_argument("--ack-timeout", type=float, default=12.0)
    parser.add_argument("--no-gui", action="store_true")

    args = parser.parse_args()

    if args.no_gui:
        if not args.port:
            raise SystemExit("Provide a port, for example COM9.")

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
