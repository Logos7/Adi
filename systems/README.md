# Systems

This directory contains complete FPGA systems.

A system combines:

- processor/core,
- board,
- variant,
- build configuration,
- top-level RTL.

---

## Directory pattern

```text
systems/<core>/<board>/<variant>/
```

Examples:

```text
systems/agni/tang_nano_20k/uart_bootloader
systems/agni/basys3/uart_bootloader
systems/indra/tang_nano_20k/basic_dense
systems/nada/tang_nano_20k/audio_pwm
```

---

## What belongs here?

The system directory owns:

- top-level Verilog module,
- system-specific wiring,
- build files for one or more toolchains,
- system manifest,
- system-specific documentation.

Recommended shape:

```text
systems/<core>/<board>/<variant>/
├─ README.md
├─ system.yaml
├─ rtl/
│  └─ <core>_<board>_<variant>_top.v
└─ build/
   ├─ gowin/
   ├─ vivado/
   ├─ yosys/
   └─ quartus/
```

Only the relevant build directories need to exist for a given system.

---

## Important rule

Processor cores stay in `cores/`.

Physical board definitions stay in `boards/`.

A system is the concrete marriage of both:

```text
core + board + variant + toolchain build configuration
```
