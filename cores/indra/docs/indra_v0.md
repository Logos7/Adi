# Indra v0

Indra is a small programmable neural processor for tiny AI brains.

The hardware is built once. Different brains are loaded as programs, weights, biases, and input vectors.

## Goal

Indra executes small creature brains for artificial life, games, simulations, and Unity-based agents.

Typical brain size:

```text
8..32 inputs
1..4 layers
4..32 neurons per layer
2..16 outputs
int8 weights
int8 activations
int32 accumulators
```

## Brain Program Example

```indra
brain_wolf:
  DENSE 24 16 W=wolf_w0 B=wolf_b0 ACT=RELU SHIFT=7
  DENSE 16 8  W=wolf_w1 B=wolf_b1 ACT=RELU SHIFT=7
  DENSE 8  6  W=wolf_w2 B=wolf_b2 ACT=CLAMP SHIFT=7
  END
```

## v0 Instructions

```text
DENSE in_count out_count W=weights B=biases ACT=activation [SHIFT=shift]
END
```

If `SHIFT` is omitted, the assembler uses:

```text
SHIFT=7
```

## v0 Activations

```text
NONE
RELU
CLAMP
SIGN
```

## v0 Hardware Limits

```text
MAX_INPUTS      = 32
MAX_LAYER_WIDTH = 32
MAX_LAYERS      = 4
MAX_OUTPUTS     = 16
MAC_LANES       = 8
```

## Numeric Format

Indra v0 uses signed integer arithmetic with a normalized fixed-point interpretation.

```text
inputs:      int8,  scale = 1/128
weights:     int8,  scale = 1/128
biases:      int32, scale = 1/16384
accumulator: int32, scale = 1/16384
outputs:     int8,  scale = 1/128
```

A dense layer computes:

```text
acc = bias + sum(input[i] * weight[i])
scaled = acc >> SHIFT
output = activation_and_saturate_i8(scaled)
```

The natural default for normalized int8 values is:

```text
SHIFT=7
```

## v0 Scope

Indra v0 supports dense integer inference only.

It does not support training, floating-point math, convolutions, transformers, or dynamic allocation.
