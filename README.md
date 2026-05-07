# Adi

Adi is an experimental FPGA computing laboratory.

It is not a single CPU, a single board project, or a single tool. Adi is a small hardware/software universe for building and exploring soft processors, languages, FPGA systems, development tools, and visual/audio/AI experiments from the ground up.

## Current direction

Adi v2 is organized around several independent axes:

- **processors / cores** — reusable computation engines such as Agni, Brahma, Indra, and Nada,
- **boards** — physical FPGA boards such as Tang Nano 20K, Tang Mega 138K, and Basys 3,
- **toolchains** — FPGA vendor/build flows such as Gowin and Vivado,
- **systems** — concrete combinations of processor, board, variant, top-level RTL, and build configuration,
- **languages** — Sutra as the low-level assembly layer and Mantra as the future high-level language,
- **applications** — especially Adi.Studio, the planned integrated C# environment.

## Main names

### Agni

Agni is the small general-purpose soft CPU line.

It is currently the main working CPU target for Tang Nano 20K experiments.

### Brahma

Brahma is the future larger general-purpose soft CPU line.

It is intended for bigger FPGA targets such as Tang Mega 138K or later boards with more resources.

### Indra

Indra is the neural/AI brain processor line.

It is intended for compact programmable neural-network-style agents and small inference engines.

### Nada

Nada is the audio/DSP processor line.

It is intended for synthesis, oscillators, filters, delay, reverb, and other programmable audio experiments.

### Sutra

Sutra is the low-level assembly language and assembler infrastructure.

It currently targets Agni and is intended to become shared infrastructure for Agni and Brahma.

### Mantra

Mantra is Adi's future high-level language.

Mantra will lower into Sutra, which is then assembled for processor targets such as Agni and Brahma.

### Adi.Studio

Adi.Studio is the planned main C# desktop application for Adi.

It will replace the old separate UART viewer and UART terminal workflow with one integrated environment for editing, building, uploading, running, and observing programs.

## Repository layout

```text
Adi/
├─ apps/
│  └─ Adi.Studio/
├─ boards/
│  ├─ tang_nano_20k/
│  ├─ tang_mega_138k/
│  └─ basys3/
├─ cores/
│  ├─ agni/
│  ├─ brahma/
│  ├─ indra/
│  └─ nada/
├─ docs/
├─ examples/
├─ mantra/
├─ sutra/
├─ systems/
├─ tests/
└─ tools/
```

## Directory model

### `cores/`

Reusable processor cores and their processor-specific documentation, RTL, simulators, and tests.

A core should not depend on one specific physical board.

Examples:

```text
cores/agni/
cores/brahma/
cores/indra/
cores/nada/
```

### `boards/`

Physical FPGA board definitions.

A board definition describes the board itself: constraints, pin mappings, clocks, and board-specific notes.

Examples:

```text
boards/tang_nano_20k/
boards/tang_mega_138k/
boards/basys3/
```

Different Gowin boards are still different boards. They only happen to use the same toolchain family.

### `systems/`

Complete FPGA systems.

A system combines:

- a processor/core,
- a board,
- a system variant,
- top-level RTL,
- build configuration for a specific toolchain.

Directory pattern:

```text
systems/<core>/<board>/<variant>/
```

Examples:

```text
systems/agni/tang_nano_20k/uart_bootloader/
systems/agni/basys3/uart_bootloader/
systems/indra/tang_nano_20k/basic_dense/
systems/nada/tang_nano_20k/audio_pwm/
```

### `sutra/`

Sutra language implementation, assembler infrastructure, target definitions, libraries, and tests.

### `mantra/`

Mantra language implementation and tests.

### `tools/`

Command-line tools, build helpers, upload helpers, packers, formatters, checkers, and migration utilities.

Tooling should be grouped by domain:

```text
tools/agni/
tools/fpga/
tools/indra/
tools/mantra/
tools/nada/
tools/sutra/
tools/dev/
```

### `apps/`

Larger user-facing applications.

The primary planned application is:

```text
apps/Adi.Studio/
```

## Important rule

A core is not a board.

Agni is not Tang Nano 20K.
Tang Nano 20K is not Agni.
Agni on Tang Nano 20K is a system.

In repository terms:

```text
cores/agni/
boards/tang_nano_20k/
systems/agni/tang_nano_20k/uart_bootloader/
```

## Quick start

Install development dependencies:

```powershell
py -m pip install -r requirements-dev.txt
```

Run the full test suite:

```powershell
py -m pytest -q
```

Compile a Sutra example for Agni:

```powershell
py tools\sutra\sutra2hex.py examples\agni\fractals\mandelbrot.sutra cores\agni\rtl\src\program.hex
```

Upload a Sutra program to an Agni UART bootloader system:

```powershell
py tools\agni\upload_sutra.py COM9 examples\agni\fractals\julia.sutra
```

Adjust `COM9` to match the actual serial port.

## Legacy notes



Old standalone UART viewer and terminal workflows are being replaced by Adi.Studio. Temporary or transitional scripts may still exist under `tools/`, but new user-facing development should move toward `apps/Adi.Studio/`.

## Philosophy

Adi is a small universe for exploring computation layer by layer:

```text
logic gates -> processors -> languages -> programs -> graphics/audio/AI -> interaction
```

The goal is to keep the system understandable while still making it powerful enough to produce visible, exciting results on real FPGA hardware.

## License

Adi is released under the Adi Non-Commercial Attribution License.

You may use, copy, modify, and fork this project for personal, educational, research, and non-commercial purposes.

Commercial use requires explicit written permission from the author.

See [LICENSE](LICENSE).
