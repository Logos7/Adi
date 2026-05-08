# Adi.Studio

Adi.Studio is the main desktop application for Adi.

It is the long-term integrated environment for editing, building, uploading,
running, and observing programs across Adi's processors and languages.

## Current shape

The current v2 repository uses the root solution:

```text
Adi.sln
```

The current application project is:

```text
apps/Adi.Studio/Adi.Studio.csproj
```

For now, Adi.Studio is intentionally small. It should grow in-place before it is
split into multiple projects.

## Initial goals

- edit Sutra programs,
- compile Sutra,
- upload programs to Agni systems,
- display ADI0 and ADI1 frames,
- show UART logs and terminal output,
- manage boards, systems, and ports.

## Future goals

- Mantra editor,
- Indra brain editor,
- Nada patch editor,
- FPGA build/program integration,
- memory/register inspection,
- debugger-like workflows.

## Planned future shape

The long-term layout may become modular when the application grows enough to
justify the split:

```text
apps/Adi.Studio/
  README.md
  src/
    Adi.Studio.App/
    Adi.Studio.Core/
    Adi.Studio.Workspace/
    Adi.Studio.Serial/
    Adi.Studio.Fpga/
    Adi.Studio.Sutra/
    Adi.Studio.Mantra/
    Adi.Studio.Agni/
    Adi.Studio.Indra/
    Adi.Studio.Nada/
  tests/
```

This is a target shape, not the current repository shape.

## Role in Adi

Adi.Studio is not a small developer script.

Small command-line helpers belong in `tools/`.

Adi.Studio belongs in `apps/` because it is a user-facing desktop application
and the central environment for the Adi ecosystem.
