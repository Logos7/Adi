# Indra Binary v0

This document describes the initial binary format produced by `tools/indra_pack.py`.

## Output Files

For a brain named `brain_bug`, the packer writes:

```text
brain_bug.program.bin
brain_bug.weights.bin
brain_bug.biases.bin
brain_bug.program.hex
brain_bug.weights.hex
brain_bug.biases.hex
brain_bug.manifest.json
```

## Numeric Convention

```text
int8 real scale       = 1/128
accumulator scale     = 1/16384
default layer SHIFT   = 7
```

## Program Stream

Supported opcodes:

```text
0x01 = DENSE
0xFF = END
```

## DENSE Record

A DENSE record is 12 bytes:

```text
u8  opcode
u8  input_count
u8  output_count
u8  activation
u8  shift
u8  reserved0
u16 weight_offset_bytes
u16 bias_offset_i32
u16 reserved1
```

All multi-byte fields are little-endian.

## END Record

```text
u8 opcode = 0xFF
```

## Activation IDs

```text
0 = NONE
1 = RELU
2 = CLAMP
3 = SIGN
```
