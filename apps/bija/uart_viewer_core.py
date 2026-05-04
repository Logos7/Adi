from __future__ import annotations

import os
import time

import app_paths
from adi_frames import AdiFrame, pop_frame
from clipboard_image import copy_rgb_to_windows_clipboard
from program_upload import upload_graphics_program
from serial_ports import available_ports, choose_default_port, parse_baud, reset_buffers, serial
from viewer_args import DEFAULT_SOURCE, ViewerDefaults, optional_byte, parse_int
from viewer_palette import DEFAULT_PALETTE, PALETTE_KEY_BY_LABEL, PALETTE_LABELS, palette_label
from viewer_render import render_frame

STATE_NAME = "uart_viewer_state.json"


def run_viewer_gui(defaults: ViewerDefaults) -> None:
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
    display_ref: dict[str, int | bytes | None] = {"width": 0, "height": 0, "rgb": None}
    counter = {"n": 0}
    timing = {"last": None, "fps": 0.0}

    outer = ttk.Frame(root, padding=10)
    outer.pack(fill="both", expand=True)

    connection = ttk.LabelFrame(outer, text="Connection", padding=8)
    connection.pack(fill="x")
    ttk.Label(connection, text="Port").grid(row=0, column=0, sticky="w")
    port_box = ttk.Combobox(connection, textvariable=port_var, values=ports, width=16)
    port_box.grid(row=0, column=1, sticky="w", padx=(6, 12))

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
            initialdir=app_paths.load_last_sutra_dir(STATE_NAME),
            filetypes=[("Sutra", "*.sutra"), ("All files", "*.*")],
        )
        if path:
            app_paths.save_last_sutra_dir(STATE_NAME, os.path.dirname(path))
            file_var.set(app_paths.as_repo_path(path))

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
    ttk.Combobox(render, textvariable=palette_var, values=PALETTE_LABELS, width=12, state="readonly").grid(row=0, column=9, sticky="w", padx=(6, 0))

    actions = ttk.LabelFrame(outer, text="Actions", padding=8)
    actions.pack(fill="x", pady=(10, 0))
    ttk.Label(outer, textvariable=status_var).pack(fill="x", pady=(8, 4))

    canvas_frame = ttk.LabelFrame(outer, text="Frame", padding=8)
    canvas_frame.pack(fill="both", expand=True)
    canvas = tk.Canvas(canvas_frame, width=512, height=384, background="#111111", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    log_box = ScrolledText(outer, width=120, height=8, font=("Consolas", 9), wrap="char")
    log_box.pack(fill="x", pady=(10, 0))

    def current_baud() -> int:
        return parse_baud(baud_var.get())

    def current_palette() -> str:
        return PALETTE_KEY_BY_LABEL.get(palette_var.get(), DEFAULT_PALETTE)

    def current_params() -> tuple[str, int | None, int | None, int, int, str]:
        path = app_paths.resolve_repo_path(file_var.get(), DEFAULT_SOURCE)
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
            reset_buffers(ser)
        buffer.clear()
        timing["last"] = None
        timing["fps"] = 0.0
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
        counter["n"] = 0
        timing["last"] = None
        timing["fps"] = 0.0
        image_ref["img"] = None
        display_ref["width"] = 0
        display_ref["height"] = 0
        display_ref["rgb"] = None
        canvas.delete("all")
        log_box.delete("1.0", "end")
        status_var.set("Cleared")

    def copy_image() -> None:
        width = display_ref["width"]
        height = display_ref["height"]
        rgb = display_ref["rgb"]
        if not isinstance(width, int) or not isinstance(height, int) or not isinstance(rgb, bytes) or width <= 0 or height <= 0:
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
        width = display_ref["width"]
        height = display_ref["height"]
        if img is None or not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            messagebox.showinfo("Save image", "No frame image to save yet.")
            return
        images_dir = os.path.join(app_paths.ROOT, "docs", "images")
        initial_dir = images_dir if os.path.isdir(images_dir) else app_paths.ROOT
        path = filedialog.asksaveasfilename(
            title="Save current frame image",
            initialdir=initial_dir,
            initialfile=f"adi-frame-{counter['n']:04d}-{width}x{height}.png",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            img.write(path, format="png")
            status_var.set(f"Saved image: {app_paths.as_repo_path(path)}")
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
            close_serial()
            status_var.set(f"Uploading: {os.path.basename(path)}")
            log(f"[UPLOAD] {path}\n")
            root.update_idletasks()
            upload_graphics_program(
                port,
                baud,
                path,
                width,
                height,
                max_iter,
                defaults.boot_timeout,
                defaults.ack_timeout,
            )
            buffer.clear()
            counter["n"] = 0
            timing["last"] = None
            timing["fps"] = 0.0
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
            frame = pop_frame(buffer)
            if frame is None:
                return
            draw_frame(frame)

    def draw_frame(frame: AdiFrame) -> None:
        try:
            max_iter = parse_int(max_iter_var.get(), "Max iter", 1, 255)
            scale = parse_int(scale_var.get(), "Scale", 1, 32)
            palette = current_palette()
        except Exception:
            max_iter = defaults.max_iter
            scale = defaults.scale
            palette = defaults.palette

        rendered = render_frame(frame, max_iter, scale, palette)
        img = tk.PhotoImage(width=frame.width, height=frame.height)
        img.put(rendered.photo_rows)
        image_ref["img"] = img.zoom(scale, scale)
        display_ref["width"] = rendered.display_width
        display_ref["height"] = rendered.display_height
        display_ref["rgb"] = rendered.rgb
        canvas.configure(width=rendered.display_width, height=rendered.display_height)
        canvas.delete("all")
        canvas.create_image(0, 0, image=image_ref["img"], anchor="nw")

        now = time.perf_counter()
        last = timing["last"]
        fps = timing["fps"]
        if isinstance(last, float):
            dt = now - last
            if dt > 0.0:
                instant_fps = 1.0 / dt
                fps = instant_fps if fps <= 0.0 else (fps * 0.85) + (instant_fps * 0.15)
        timing["fps"] = fps
        timing["last"] = now
        counter["n"] += 1

        kind = frame.kind.decode("ascii", errors="replace")
        fps_text = "warming" if fps <= 0.0 else f"{fps:.1f}"
        status_var.set(
            f"Frame #{counter['n']}: {kind}, {frame.width}x{frame.height}, "
            f"FPS={fps_text}, scale={scale}, image={rendered.display_width}x{rendered.display_height}, "
            f"palette={palette_label(palette)}, payload={frame.raw_size} bytes, maxIter={max_iter}"
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
