# Indra Binary Format v0

Indra v0 source files are packed into three binary images and one JSON manifest.

```text
<name>.program.bin
<name>.weights.bin
<name>.biases.bin
<name>.manifest.json
```

Hex text mirrors are also emitted for inspection and future FPGA memory initialization.

```text
<name>.program.hex
<name>.weights.hex
<name>.biases.hex
```

## Program Records

Each instruction record is 16 bytes.

All multi-byte fields use little-endian byte order.

### DENSE Record

```text
byte  0      opcode        1 = DENSE
byte  1      activation    activation id
byte  2      input_count   unsigned byte
byte  3      output_count  unsigned byte
bytes 4..7   weight_offset byte offset in weights image
bytes 8..11  bias_offset   byte offset in biases image
bytes 12..15 reserved      zero
```

### END Record

```text
byte  0      opcode        255 = END
bytes 1..15  zero
```

## Activation IDs

```text
0 = NONE
1 = RELU
2 = CLAMP
3 = SIGN
```

## Weight Image

Weights are packed as raw signed int8 values.

The source layout is row-major by output neuron.

For this layer:

```indra
DENSE 4 3 W=w0 B=b0 ACT=RELU
```

weights are stored as:

```text
out0_in0, out0_in1, out0_in2, out0_in3,
out1_in0, out1_in1, out1_in2, out1_in3,
out2_in0, out2_in1, out2_in2, out2_in3
```

## Bias Image

Biases are packed as signed int32 values, little-endian.

One bias is stored per output neuron.

## Manifest

The JSON manifest is intended for tools and tests. The hardware does not need to consume it.

It records:

```text
format
brain name
record size
program image size
weight image size
bias image size
layer descriptors
opcodes
activation ids
```
