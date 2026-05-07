# Boards

This directory contains physical FPGA board definitions.

A board definition describes the board itself, not a processor and not a complete FPGA system.

Examples:

- tang_nano_20k
- tang_mega_138k
- basys3

Each board may contain constraints for one or more toolchains.

Example:

boards/basys3/constraints/vivado/basys3.xdc
boards/tang_nano_20k/constraints/gowin/tang_nano_20k.cst
