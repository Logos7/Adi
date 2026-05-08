# Agni UART bootloader on Tang Nano 20K, modular manifest

This is a manifest-first version of the current Tang Nano 20K Agni UART bootloader system.

It is intentionally added beside the stable `uart_bootloader/` variant, so the working FPGA path remains untouched.

Purpose:

- document the exact parts used by the system,
- prepare future automatic composition,
- make it easy to add sibling variants such as HDMI 320x200 1bpp,
- keep `cores/`, `boards/`, `rtl/`, and `systems/` separated.

This directory is not the HDMI implementation yet. It is the safe bridge between the existing fixed system and future LEGO-style systems.
