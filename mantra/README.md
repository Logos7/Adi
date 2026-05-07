# Mantra

Mantra is Adi's high-level language.

Mantra lowers into Sutra, which is then assembled for processor targets such as Agni and Brahma.

---

## Initial goals

- readable structured syntax,
- simple compilation to Sutra,
- support for Agni first,
- future support for Brahma,
- diagnostics good enough for Adi.Studio integration.

---

## Planned compiler shape

```text
mantra/
├─ README.md
├─ mantra/
│  ├─ __init__.py
│  ├─ lexer.py
│  ├─ parser.py
│  ├─ ast.py
│  ├─ checker.py
│  ├─ lowering.py
│  └─ emit_sutra.py
└─ tests/
```

---

## Language stack

```text
Mantra source
  -> Mantra compiler
  -> Sutra source
  -> Sutra assembler
  -> target image for Agni/Brahma
```
