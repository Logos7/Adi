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

## Transitional entrypoints

Adi v2 is migrating from old top-level scripts toward grouped tools and the
future integrated `apps/Adi.Studio` workflow.

Some legacy top-level scripts may temporarily remain in this directory as
compatibility entrypoints during the migration.

Examples:

```text
tools/sutra2hex.py
tools/sutra_expand.py
tools/sutra_upload.py
tools/indra_asm.py
tools/indra_pack.py
tools/indra_run.py
```

New code should prefer the grouped tool packages where available.

## Rule of thumb

Use this directory for small tools that are useful from the command line.

Use `apps/` for larger interactive applications, graphical tools, viewers,
editors, and integrated workflows.
