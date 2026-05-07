# Adi.Studio

Adi.Studio is the main desktop application for Adi.

It will replace the old separate UART viewer and UART terminal tools with one integrated C# environment.

---

## Initial goals

- edit Sutra programs,
- compile Sutra,
- upload programs to Agni systems,
- display ADI0 and ADI1 frames,
- show UART logs and terminal output,
- manage boards, systems, and ports.

---

## Future goals

- Mantra editor,
- Indra brain editor,
- Nada patch editor,
- FPGA build/program integration,
- memory/register inspection,
- debugger-like workflows.

---

## Planned solution shape

```text
apps/Adi.Studio/
├─ Adi.Studio.sln
├─ README.md
├─ src/
│  ├─ Adi.Studio.App/
│  ├─ Adi.Studio.Core/
│  ├─ Adi.Studio.Workspace/
│  ├─ Adi.Studio.Serial/
│  ├─ Adi.Studio.Fpga/
│  ├─ Adi.Studio.Sutra/
│  ├─ Adi.Studio.Mantra/
│  ├─ Adi.Studio.Agni/
│  ├─ Adi.Studio.Indra/
│  └─ Adi.Studio.Nada/
└─ tests/
```

---

## Role in Adi

Adi.Studio is not a small developer script.

It is the long-term integrated environment for editing, building, uploading, running, and observing programs across Adi's processors and languages.
