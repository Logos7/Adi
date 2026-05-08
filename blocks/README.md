# Adi blocks

This directory contains block descriptors for Adi.Studio and future system composition tools.

A block descriptor describes a reusable hardware or target component. It does not have to contain the implementation itself. The actual RTL, constraints, documentation, tests, and build files may continue to live in their current domain directories.

## Core idea

- `blocks/` describes reusable component types.
- `systems/` describes concrete instances of those component types and their connections.
- `cores/` contains physical source trees for processor cores such as Agni, Brahma, Indra, and Nada.
- `rtl/` contains shared hardware building blocks and reusable IP.
- `boards/` contains physical board definitions, constraints, pins, clocks, and vendor-specific board notes.

In object-oriented terms:

```text
block descriptor = class/type
system instance  = object/instance
```

For example, one Agni block descriptor can be instantiated multiple times in a system:

```yaml
instances:
  - id: agni0
    block: cores/agni

  - id: agni1
    block: cores/agni

  - id: brahma0
    block: cores/brahma
```

This means Adi.Studio can eventually draw systems as graphs of reusable blocks without forcing the repository to move all source files under `blocks/`.

## Directory layout

```text
blocks/
├─ cores/       reusable processor / computation core descriptors
├─ ip/          reusable peripheral and hardware IP descriptors
├─ targets/     board / device target descriptors
└─ examples/    example system composition manifests
```

## Descriptor maturity

Descriptors may use a `status` field:

- `active` — already backed by current source files.
- `planned` — intended block, not implemented yet.
- `extraction_candidate` — logic exists, but is still physically located in an older or core-specific source tree and should later be extracted into reusable RTL.

## Rule

Do not move working RTL just to satisfy the block model.

First describe the blocks. Then let Adi.Studio and composition tooling consume the descriptors. Physical source layout can be refactored gradually and safely.
