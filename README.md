# Adi

**Adi** is an experimental FPGA computing playground built around a custom soft CPU, a small assembler, UART tooling, and visual demos running directly on hardware.

At the center of the project is **Brahma**, a custom CPU core, and **Sutra**, a minimal assembly language used to write programs for it.

![Adi fractal demo 1](docs/images/julia.png)
![Adi fractal demo 2](docs/images/mandelbrot.png)
![Adi fractal demo 3](docs/images/spiral.png)

UART viewer screenshots.

---

## What is this?

Adi is a hardware/software experiment for learning, testing, and building small computing systems from the ground up.

It includes:

- a custom soft CPU implemented in Verilog,
- a small assembler called **Sutra**,
- a UART bootloader for uploading programs to FPGA hardware,
- Python tools for upload, terminal I/O, and graphical frame viewing,
- example programs written in Sutra,
- simulator and assembler tests,
- GitHub Actions CI for regression checks.

The project is intentionally experimental. The architecture, instruction set, examples, and tooling are still evolving.

---

## Main components

### Brahma

**Brahma** is the custom CPU core. It is designed as a small, understandable soft CPU that can run on FPGA hardware and be extended step by step.

The current focus is not maximum performance, but clarity, experimentation, and building a complete working stack.

### Sutra

**Sutra** is the assembly language used to write programs for Brahma.

It supports labels, instructions, memory-mapped I/O, framebuffer operations, helper macros, and since **v1.5** a split code/data image with `.data`, `.code`, `.org`, `.word`, `.q7_25`, `.sin_lut`, and `.zero` directives.

### UART bootloader

The FPGA design can wait for a host-side upload over UART. The Python tools repeatedly send the `ADI!` handshake until the FPGA replies with `READY`, then upload the assembled code image and, when present, the data image.

### Viewer and terminal tools

Adi currently has two main host-side tools:

- a text UART terminal,
- a graphical UART viewer.

The terminal is useful for text-based experiments. The viewer is useful for graphical programs, including fractals and simple framebuffer-style demos.

It understands the current ADI frame formats used by the examples:

- **ADI0** — raw 8-bit pixels, useful for fractals and byte-per-pixel graphics,
- **ADI1** — packed 1-bit 64x64 framebuffer, useful for wireframe and monochrome framebuffer demos.

---

## Quick start

Clone the repository:

```powershell
git clone https://github.com/Logos7/Adi.git
cd Adi
```

Install development dependencies:

```powershell
py -m pip install -r requirements-dev.txt
```

Run tests:

```powershell
py -m pytest -q cores/bija/tests
```

Run the UART terminal:

```powershell
py apps/bija/uart_terminal.py
```

Run the graphical UART viewer:

```powershell
py apps/bija/uart_viewer.py
```

Upload a Sutra example through the viewer:

```powershell
py apps/bija/uart_viewer.py COM9 --upload examples/bija/fractals/julia.sutra
```

Adjust `COM9` to match your own serial port.

---

## Testing

Run the full current test suite with:

```powershell
py -m pytest -q cores/bija/tests
```

The tests cover the assembler, simulator behavior, CPU-level functionality, example compilation, direct UART write conventions, and the Sutra v1.5 code/data image path.

Python sources can also be syntax-checked with:

```powershell
py -m compileall -q sutra cores/bija/sim tools apps/bija
```

GitHub Actions runs the test suite automatically on pushes and pull requests.

---

## Philosophy

Adi is not just a single CPU or a single tool.

It is a small universe for exploring how computation can be built layer by layer:

```text
logic gates -> CPU -> assembler -> programs -> graphics -> interaction
```

The goal is to keep the system understandable while still making it powerful enough to produce visible, exciting results on real FPGA hardware.

---

## License

Adi is released under the Adi Non-Commercial Attribution License.

You may use, copy, modify, and fork this project for personal, educational, research, and non-commercial purposes.

Commercial use requires explicit written permission from the author.

See [LICENSE](LICENSE).
