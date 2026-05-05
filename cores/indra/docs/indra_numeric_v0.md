# Indra Numeric v0

Indra v0 uses signed integer arithmetic with a normalized fixed-point interpretation.

The hardware operates on integers. The fixed-point meaning is a convention shared by tools, tests, and future RTL.

## int8 Normalized Values

Inputs, weights, hidden activations, and outputs use signed int8 values:

```text
raw range = -128..127
real = raw / 128
real range = -1.0..0.9921875
```

Examples:

```text
raw -128 = -1.0
raw  -64 = -0.5
raw    0 =  0.0
raw   64 =  0.5
raw  127 =  0.9921875
```

## Multiplication

Both inputs and weights use scale `1/128`.

Therefore:

```text
input_real  = input_raw / 128
weight_real = weight_raw / 128
product_scale = 1 / 16384
```

The raw product is accumulated into an int32 accumulator:

```text
acc = bias + sum(input_raw[i] * weight_raw[i])
```

The accumulator scale is:

```text
accumulator scale = 1 / 16384
```

## Biases

Biases are stored as int32 values using the same scale as the accumulator:

```text
bias real = bias_raw / 16384
```

## Layer Shift

The natural shift for returning from accumulator scale to int8 normalized scale is:

```text
SHIFT=7
```

A layer computes:

```text
acc = bias + sum(input[i] * weight[i])
scaled = acc >> SHIFT
output = activation_and_saturate_i8(scaled)
```

## Custom SHIFT

`SHIFT=7` is the default.

Other values are allowed for experimentation:

```text
SHIFT < 7  = stronger layer output
SHIFT > 7  = weaker layer output
```

## Summary

Indra v0 uses:

```text
inputs:      int8,  scale = 1/128
weights:     int8,  scale = 1/128
biases:      int32, scale = 1/16384
accumulator: int32, scale = 1/16384
outputs:     int8,  scale = 1/128
default SHIFT = 7
```
