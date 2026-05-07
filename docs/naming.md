# Adi naming model

Adi is the whole hardware/software laboratory.

It is not a single CPU, a single tool, or a single board project. Adi contains processors, languages, boards, systems, tools, examples, and applications.

---

## Main names

- **Adi** — the whole repository and project space.
- **Agni** — small general-purpose soft CPU, originally developed for Tang Nano 20K.
- **Brahma** — future larger general-purpose soft CPU.
- **Indra** — neural/AI brain processor.
- **Nada** — audio/DSP/synthesis/reverb processor.
- **Sutra** — low-level assembly language and assembler infrastructure.
- **Mantra** — high-level language that lowers into Sutra.
- **Adi.Studio** — main C# desktop application for editing, building, uploading, running, and observing Adi programs.

---

## Repository axes

Adi separates four independent axes:

- **core** — processor implementation, for example Agni, Brahma, Indra, Nada.
- **board** — physical FPGA board, for example Tang Nano 20K, Tang Mega 138K, Basys 3.
- **toolchain** — FPGA vendor/build toolchain, for example Gowin, Vivado, Yosys, Quartus.
- **system** — concrete combination of core, board, variant, and toolchain build configuration.

---

## Directory model

- `cores/` — reusable processor cores.
- `boards/` — board definitions, constraints, clock information, pin mappings.
- `systems/` — concrete FPGA systems that combine a core with a board.
- `sutra/` — Sutra language, assembler, libraries, and targets.
- `mantra/` — Mantra language and compiler.
- `examples/` — example programs, brain descriptions, patches, and demos.
- `tools/` — command-line tools, build scripts, packers, formatters, checkers.
- `apps/` — larger user-facing applications.
- `docs/` — project-wide documentation.

---

## Important rule

A core is not a board.

```text
Agni is not Tang Nano 20K.
Tang Nano 20K is not Agni.
Agni on Tang Nano 20K is a system.
```

Example:

```text
systems/agni/tang_nano_20k/uart_bootloader
```

---

## Legacy naming

The old **Bija** name is retired.

Code, documentation, examples, and paths should use **Agni** for the small CPU line.
