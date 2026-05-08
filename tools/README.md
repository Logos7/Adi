# Tools

This directory contains command-line tools, developer utilities, build scripts,
packers, checkers, formatters, and small hardware-facing helpers.

Large user-facing applications belong in `apps/`.

## Tool groups

```text
tools/
  agni/          Agni-specific command-line helpers.
  dev/           Repository maintenance and migration helpers.
  fpga/          FPGA build, programming, and toolchain helpers.
  indra/         Indra parser, packer, runner, and inspectors.
  mantra/        Mantra command-line tools.
  nada/          Nada parser, packer, and audio render helpers.
  sutra/         Sutra command-line tools.
  sutra-vscode/  VS Code extension for Sutra syntax support.
```

## Current convention

Adi v2 uses grouped tool directories instead of old top-level helper scripts.

Prefer paths such as:

```text
tools/agni/upload_sutra.py
tools/agni/uart_terminal.py
tools/agni/uart_viewer.py
tools/sutra/...
tools/indra/...
tools/mantra/...
tools/nada/...
```

New command-line helpers should be placed in the appropriate grouped tool
directory.

## Rule of thumb

Use `tools/` for small tools that are useful from the command line.

Use `apps/` for larger interactive applications, graphical tools, viewers,
editors, and integrated workflows.
