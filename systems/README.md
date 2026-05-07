# Systems

This directory contains complete FPGA systems.

A system combines:

- processor/core
- board
- variant
- build configuration
- top-level RTL

Directory pattern:

systems/<core>/<board>/<variant>/

Examples:

systems/agni/tang_nano_20k/uart_bootloader
systems/agni/basys3/uart_bootloader
systems/indra/tang_nano_20k/basic_dense
systems/nada/tang_nano_20k/audio_pwm

The system directory owns the top-level Verilog module and the toolchain build files.
