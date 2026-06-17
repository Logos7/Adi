from __future__ import annotations

import argparse
import shlex
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import serial
except ImportError:
    serial = None

MAGIC = bytes([0xAD, 0x10])
CMD_CLEAR = 0x01
CMD_SPHERE = 0x02
CMD_RENDER = 0x03
DEFAULT_GOWIN = r"C:\Gowin\Gowin_V1.9.12.02_SP1_x64\IDE\bin\gw_sh.exe"
DEFAULT_PROJECT = Path(__file__).resolve().parents[2] / "systems" / "raytracer_spi" / "tang_primer_25k" / "spheres_uart_demo"


def q8(value: float) -> int:
    raw = int(round(value * 256.0))
    if raw < -32768 or raw > 32767:
        raise ValueError(f"Q8.8 poza zakresem: {value}")
    return raw


def rgb565(r: float, g: float, b: float) -> int:
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    return (int(round(r * 31)) << 11) | (int(round(g * 63)) << 5) | int(round(b * 31))


def packet(cmd: int, payload: bytes = b"") -> bytes:
    if len(payload) > 255:
        raise ValueError("Payload za długi")
    return MAGIC + bytes([cmd, len(payload)]) + payload


@dataclass
class Sphere:
    slot: int
    x: float
    y: float
    z: float
    r: float
    color: int
    active: int = 1

    def encode(self) -> bytes:
        if self.slot < 0 or self.slot > 7:
            raise ValueError("Slot sfery musi być 0..7")
        return struct.pack(
            "<BBhhhhH",
            self.slot,
            self.active,
            q8(self.x),
            q8(self.y),
            q8(self.z),
            q8(self.r),
            self.color,
        )


class SceneCompiler:
    def __init__(self) -> None:
        self.current_color = rgb565(1.0, 0.55, 0.20)
        self.next_slot = 0
        self.packets: list[bytes] = []

    def compile_line(self, line: str, line_no: int) -> None:
        line = line.split("#", 1)[0].strip()
        if not line:
            return
        tokens = shlex.split(line)
        cmd = tokens[0].lower()
        args = tokens[1:]
        if cmd == "clear":
            self.packets.append(packet(CMD_CLEAR))
            self.next_slot = 0
        elif cmd == "color":
            if len(args) != 3:
                raise ValueError(f"Linia {line_no}: color r g b")
            self.current_color = rgb565(float(args[0]), float(args[1]), float(args[2]))
        elif cmd == "sphere":
            sphere = self.parse_sphere(args, line_no)
            self.packets.append(packet(CMD_SPHERE, sphere.encode()))
        elif cmd == "render":
            self.packets.append(packet(CMD_RENDER))
        else:
            raise ValueError(f"Linia {line_no}: nieznana komenda: {cmd}")

    def parse_sphere(self, args: list[str], line_no: int) -> Sphere:
        slot = self.next_slot
        color = self.current_color
        values: list[str] = []
        i = 0
        while i < len(args):
            a = args[i].lower()
            if a == "slot":
                i += 1
                slot = int(args[i])
            elif a == "color":
                color = rgb565(float(args[i + 1]), float(args[i + 2]), float(args[i + 3]))
                i += 3
            else:
                values.append(args[i])
            i += 1
        if len(values) != 4:
            raise ValueError(f"Linia {line_no}: sphere x y z r [slot n] [color r g b]")
        self.next_slot = max(self.next_slot, slot + 1)
        return Sphere(slot, float(values[0]), float(values[1]), float(values[2]), float(values[3]), color)

    def compile_file(self, path: Path) -> list[bytes]:
        self.packets.append(packet(CMD_CLEAR))
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            self.compile_line(line, line_no)
        if not self.packets or self.packets[-1] != packet(CMD_RENDER):
            self.packets.append(packet(CMD_RENDER))
        return self.packets


def demo_scene() -> list[bytes]:
    c = SceneCompiler()
    lines = [
        "clear",
        "sphere 0.0 0.0 3.0 0.58 color 1.0 0.48 0.12",
        "sphere -0.72 -0.25 3.5 0.34 color 0.0 0.9 1.0",
        "sphere 0.82 0.18 4.2 0.42 color 0.8 0.2 1.0",
        "render",
    ]
    for i, line in enumerate(lines, 1):
        c.compile_line(line, i)
    return c.packets


def send_packets(port: str, baud: int, packets: list[bytes]) -> None:
    if serial is None:
        raise RuntimeError("Brak pyserial. Zainstaluj: py -m pip install pyserial")
    with serial.Serial(port, baudrate=baud, timeout=1) as s:
        for p in packets:
            s.write(p)
            s.flush()


def run_gowin(project: Path, gowin: Path, create: bool, build: bool) -> None:
    project = project.resolve()
    gowin_script = project / "gowin" / "build.tcl"
    project_file = project / "spheres_uart_demo.gprj"
    if not project_file.exists():
        raise RuntimeError(f"Brak projektu Gowin: {project_file}")
    if not gowin_script.exists():
        raise RuntimeError(f"Brak skryptu Gowin: {gowin_script}")
    if create:
        print("create_project pominięte: używam statycznego .gprj zgodnego ze stylem Sipeed pmod_lcd")
    if build:
        subprocess.run([str(gowin), str(gowin_script)], cwd=project, check=True)


def compile_packets(args: argparse.Namespace) -> list[bytes]:
    if args.demo:
        return demo_scene()
    if args.scene:
        return SceneCompiler().compile_file(Path(args.scene))
    raise SystemExit("Podaj --demo albo --scene plik.txt")


def main() -> int:
    root = argparse.ArgumentParser(prog="raydog")
    sub = root.add_subparsers(dest="cmd", required=True)

    send = sub.add_parser("send")
    send.add_argument("--port", required=True)
    send.add_argument("--baud", type=int, default=115200)
    send.add_argument("--scene")
    send.add_argument("--demo", action="store_true")

    dry = sub.add_parser("dry")
    dry.add_argument("--scene")
    dry.add_argument("--demo", action="store_true")

    build = sub.add_parser("build")
    build.add_argument("--project", default=str(DEFAULT_PROJECT))
    build.add_argument("--gowin", default=DEFAULT_GOWIN)
    build.add_argument("--no-create", action="store_true")
    build.add_argument("--no-build", action="store_true")

    args = root.parse_args()

    if args.cmd == "send":
        packets = compile_packets(args)
        send_packets(args.port, args.baud, packets)
        print(f"Wysłano {len(packets)} pakietów na {args.port} @ {args.baud}")
        return 0
    if args.cmd == "dry":
        sys.stdout.buffer.write(b"".join(compile_packets(args)))
        return 0
    if args.cmd == "build":
        run_gowin(Path(args.project), Path(args.gowin), not args.no_create, not args.no_build)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
