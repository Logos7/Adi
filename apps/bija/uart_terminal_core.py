from __future__ import annotations

import os
import sys
import threading

import app_paths
from adi_frames import TerminalRxFilter
from program_upload import upload_text_program
from serial_ports import available_ports, choose_default_port, parse_baud, reset_buffers, serial
from sutra_upload import ACK_ERR, ACK_OK, ACK_READY
from terminal_args import DEFAULT_SOURCE

BOOT_ACKS = (ACK_READY, ACK_OK, ACK_ERR)
MAX_TERMINAL_CHARS = 200_000
STATE_NAME = "uart_terminal_state.json"


def run_cli(port: str, baud: int, upload: str | None, boot_timeout: float, ack_timeout: float) -> None:
    if upload:
        upload_text_program(port, baud, app_paths.resolve_repo_path(upload, DEFAULT_SOURCE), boot_timeout, ack_timeout)

    rx_filter = TerminalRxFilter(BOOT_ACKS)

    with serial.Serial(port, baudrate=baud, timeout=0.02, write_timeout=2.0) as ser:
        reset_buffers(ser)
        stop = threading.Event()

        def stdin_worker() -> None:
            while not stop.is_set():
                data = sys.stdin.buffer.readline()
                if not data:
                    break
                try:
                    ser.write(data)
                except Exception:
                    break

        thread = threading.Thread(target=stdin_worker, daemon=True)
        thread.start()
        print(f"Adi UART Terminal: {port} @ {baud}. Press Ctrl+C to exit.")
        try:
            while True:
                data = ser.read(4096)
                text = rx_filter.feed(data)
                if text:
                    sys.stdout.buffer.write(text)
                    sys.stdout.buffer.flush()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()


def run_terminal_gui(port_arg: str | None, baud_arg: int, upload_arg: str | None, boot_timeout: float, ack_timeout: float) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Adi UART Terminal")
    root.geometry("1000x760")

    ports = available_ports()
    port_var = tk.StringVar(value=port_arg or choose_default_port(ports))
    baud_var = tk.StringVar(value=str(baud_arg))
    file_var = tk.StringVar(value=upload_arg or DEFAULT_SOURCE)
    send_var = tk.StringVar()
    status_var = tk.StringVar(value="Disconnected")

    ser_ref: dict[str, serial.Serial | None] = {"ser": None}
    uploading_ref = {"active": False}
    rx_filter = TerminalRxFilter(BOOT_ACKS)

    outer = ttk.Frame(root, padding=10)
    outer.pack(fill="both", expand=True)

    connection = ttk.LabelFrame(outer, text="Connection", padding=8)
    connection.pack(fill="x")
    ttk.Label(connection, text="Port").grid(row=0, column=0, sticky="w")
    port_box = ttk.Combobox(connection, textvariable=port_var, values=ports, width=16)
    port_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
    ttk.Label(connection, text="Baud").grid(row=0, column=2, sticky="e", padx=(12, 6))
    ttk.Entry(connection, textvariable=baud_var, width=10).grid(row=0, column=3, sticky="w")
    connection_buttons = ttk.Frame(connection)
    connection_buttons.grid(row=0, column=4, sticky="e", padx=(18, 0))

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
            if len(terminal.get("1.0", "end-1c")) > MAX_TERMINAL_CHARS:
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
            initialdir=app_paths.load_last_sutra_dir(STATE_NAME),
            filetypes=[("Sutra", "*.sutra"), ("All files", "*.*")],
        )
        if path:
            app_paths.save_last_sutra_dir(STATE_NAME, os.path.dirname(path))
            file_var.set(app_paths.as_repo_path(path))

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
            reset_buffers(ser)
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
        if uploading_ref["active"]:
            return
        uploading_ref["active"] = True
        try:
            port = port_var.get().strip()
            if not port:
                raise ValueError("Port is empty.")
            baud = current_baud()
            path = app_paths.resolve_repo_path(file_var.get(), DEFAULT_SOURCE)
            close_serial()
            status_var.set(f"Uploading: {os.path.basename(path)}")
            log(f"\n[UPLOAD] {path}\n")
            root.update_idletasks()
            upload_text_program(port, baud, path, boot_timeout, ack_timeout)
            open_serial(clear_buffers=False)
            status_var.set("Upload OK. Terminal connected.")
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

    def send_text() -> None:
        ser = ser_ref["ser"]
        if ser is None or not ser.is_open:
            messagebox.showinfo("Send", "Serial port is not connected.")
            return
        text = send_var.get()
        if not text:
            return
        try:
            ser.write(text.encode("utf-8"))
            log(f"\n[TX] {text}\n")
            send_var.set("")
        except Exception as e:
            status_var.set("Send failed")
            log(f"[TX ERR] {e}\n")
            messagebox.showerror("Send", str(e))

    def clear_terminal() -> None:
        terminal.delete("1.0", "end")
        status_var.set("Cleared")

    def pump() -> None:
        if uploading_ref["active"]:
            root.after(10, pump)
            return
        ser = ser_ref["ser"]
        if ser is not None and ser.is_open:
            try:
                data = ser.read(4096)
                text = rx_filter.feed(data)
                if text:
                    log(text.decode("utf-8", errors="replace"))
            except Exception as e:
                log(f"\n[RX ERR] {e}\n")
                disconnect()
        root.after(10, pump)

    ttk.Button(connection, text="Refresh", command=refresh_ports).grid(row=0, column=5, sticky="w", padx=(8, 0))
    ttk.Button(connection_buttons, text="Connect", command=connect).pack(side="left")
    ttk.Button(connection_buttons, text="Disconnect", command=disconnect).pack(side="left", padx=(6, 0))
    ttk.Button(program, text="Browse", command=browse).grid(row=0, column=2, sticky="e")
    ttk.Button(actions, text="Upload / Run", command=upload).pack(side="left")
    ttk.Button(actions, text="Clear", command=clear_terminal).pack(side="left", padx=(6, 0))
    ttk.Button(send_frame, text="Send", command=send_text).pack(side="left")
    send_entry.bind("<Return>", lambda _event: send_text())

    def on_close() -> None:
        close_serial()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    if upload_arg:
        root.after(150, upload)
    elif port_arg:
        root.after(150, connect)
    root.after(10, pump)
    root.mainloop()
