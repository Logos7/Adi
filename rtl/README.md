# Shared RTL

This directory contains reusable hardware building blocks for Adi systems.

The code here should be independent from any single processor core or physical FPGA board. Processor-specific logic belongs under `cores/`. Board pin mappings and physical constraints belong under `boards/`. Complete assembled FPGA systems belong under `systems/`.

Recommended rules:

- keep module ports simple and language-neutral,
- keep vendor primitives behind small wrappers,
- keep Verilog/VHDL/SystemVerilog files separated by directory when needed,
- do not make shared RTL depend on Agni-specific memory maps or Tang Nano 20K pins.

Typical consumers:

```text
systems/agni/tang_nano_20k/uart_bootloader_modular/
systems/agni/tang_nano_20k/uart_bootloader_hdmi_320x200_1bpp/
systems/brahma/.../
systems/indra/.../
```
