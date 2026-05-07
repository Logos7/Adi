# Tools

This directory contains command-line tools, developer utilities, build scripts, packers, checkers, formatters, and small hardware-facing helpers.

Large user-facing applications belong in `apps/`.

---

## Suggested tool groups

```text
tools/fpga/      FPGA build/program/list tools
tools/sutra/     Sutra CLI tools
tools/mantra/    Mantra CLI tools
tools/indra/     Indra parser, packer, runner, inspectors
tools/nada/      Nada parser, packer, audio render helpers
tools/dev/       repository maintenance and migration helpers
```

---

## Transitional state

Adi 2.0 is moving away from separate UART viewer/terminal scripts toward `apps/Adi.Studio`.

Legacy scripts may temporarily remain here during migration, but new integrated workflows should be designed for Adi.Studio.
