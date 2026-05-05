from __future__ import annotations

import sys

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("pySerial is missing.", file=sys.stderr)
    print("Install it with: py -m pip install pyserial", file=sys.stderr)
    raise SystemExit(2)


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


def parse_baud(value: str) -> int:
    try:
        baud = int(value.strip())
    except Exception:
        raise ValueError("Baud must be an integer.")
    if baud < 1 or baud > 3_000_000:
        raise ValueError("Baud must be in range 1..3000000.")
    return baud


def reset_buffers(ser: serial.Serial) -> None:
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass
