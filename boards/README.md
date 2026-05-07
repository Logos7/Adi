# Boards

This directory contains physical FPGA board definitions.

A board definition describes the board itself, not a processor and not a complete FPGA system.

---

## Current board directories

```text
boards/tang_nano_20k
boards/tang_mega_138k
boards/basys3
```

---

## Board vs toolchain

Different boards are separate even when they use the same FPGA vendor toolchain.

For example, both boards below use Gowin tooling, but they are still different boards:

```text
boards/tang_nano_20k
boards/tang_mega_138k
```

Xilinx/AMD boards use a different constraints format and usually a different build flow:

```text
boards/basys3/constraints/vivado/basys3.xdc
```

Gowin boards use Gowin constraints:

```text
boards/tang_nano_20k/constraints/gowin/tang_nano_20k.cst
boards/tang_mega_138k/constraints/gowin/tang_mega_138k.cst
```

---

## Recommended board directory shape

```text
boards/<board_name>/
├─ README.md
├─ board.yaml
└─ constraints/
   ├─ gowin/
   ├─ vivado/
   ├─ yosys/
   └─ quartus/
```

Only the relevant toolchain directories need to exist for a given board.
