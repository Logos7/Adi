# Indra Binary Format v0

The Indra text format is packed into three binary blobs:

```text
<name>.program.bin
<name>.weights.bin
<name>.biases.bin
```

A manifest is also emitted for debugging:

```text
<name>.manifest.json
```

## Program Records

Each program record is 16 bytes.

### DENSE Record

```text
byte  0      opcode       0x01
byte  1      input_count
byte  2      output_count
byte  3      activation_id
bytes 4..7   weight_offset_u32_le
bytes 8..11  bias_offset_u32_le
byte  12     shift
byte  13     reserved
byte  14     reserved
byte  15     reserved
```

### END Record

```text
byte  0      opcode       0xFF
bytes 1..15  zero
```

## Activation IDs

```text
NONE  = 0
RELU  = 1
CLAMP = 2
SIGN  = 3
```

## Weight Blob

Weights are stored as signed int8 bytes.

Layer weights are row-major by output neuron:

```text
out0: w00 w01 w02 ...
out1: w10 w11 w12 ...
```

## Bias Blob

Biases are stored as signed int32 little-endian values.

## Shift

The `shift` field is an arithmetic right shift applied after accumulation and before activation.

```text
acc = acc >> shift
```
