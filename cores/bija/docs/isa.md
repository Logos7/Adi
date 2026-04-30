# Brahma-Bija ISA / Sutra v1.4

## Style

The official Sutra style is lowercase.

The parser is case-insensitive, so `MOVE R0, π` will also work, but examples should be written in lowercase.

```asm
move r0, π
fadd r1, r0, 1.0
move @led0, low
move b0, @uart_ready
```

## Operands

```text
123              integer value
1.0              fixed Q7.25 value

π                fixed Q7.25 constant
τ                fixed Q7.25 constant = 2π
φ                fixed Q7.25 golden ratio
√500             fixed Q7.25 constant = sqrt(500)

true             bool value 1
false            bool value 0
high             bool value 1
low              bool value 0

0, 1             integer/word values, never bool

@7               memory/IO at address 7
@uart_tx         MMIO UART_TX
@uart_rx         MMIO UART_RX, reads the last byte and clears ready
@uart_rx_ready   bool MMIO, 1 when an RX byte is waiting
@led0            alias for bool_mem[15], mapped by top.v to physical LED0
@pin15           bool_mem[15], not automatically any arbitrary physical FPGA pin
@r1              memory/IO at the address stored in r1

&uart_tx         UART_TX address as a regular number
&led0            bool LED0 address as a regular number, which is 15
&pin15           bool address 15 as a regular number
```

We do not use `#` for immediates and we do not use `[address]`.

## Registers

```text
r0..r31          32-bit GPR
t0..t7           aliases for r24..r31, scratch/volatile

b0..b7           bool/predicate registers

z0 = r0:r1
z1 = r2:r3
...
z11 = r22:r23
```

`z12..z15` overlap with `t0..t7`, so they are not safe for complex macros.

## Mathematical constants

The preferred style in documentation and examples is to use mathematical symbols:

```asm
move r0, π
move r1, τ
move r2, φ
move r3, √2
move r4, √500
move r5, 1/π
move r6, 1/τ
move r7, 1/√2
```

ASCII aliases are still accepted by the assembler, but they are not the default style.

Examples and documentation use mathematical symbols.

## Memory / IO / GPIO

The current RTL implements:

```text
data_mem[0..255]       word RAM, 32-bit
bool_mem[0..127]       bool/GPIO RAM

@uart_tx = 240         word MMIO, writing low8 sends a UART byte
@uart_rx = 241         word MMIO read-only, reading low8 receives a byte and clears @uart_rx_ready

@uart_ready = 128      bool MMIO read-only, 1 when UART TX is ready
@uart_rx_ready = 129   bool MMIO read-only, 1 when a UART RX byte is waiting
```

Important: `@pinN` means **bool_mem[N] address**, not a magical connection to any arbitrary physical FPGA pin.

Physical pin routing is done by `brahma_bija_top.v`.

On the Tang Nano 20K, the current `top.v` maps only:

```text
@led0 = @pin15 -> physical LED0 / pin15
@led1 = @pin16 -> physical LED1 / pin16
@led2 = @pin17 -> physical LED2 / pin17
@led3 = @pin18 -> physical LED3 / pin18
@led4 = @pin19 -> physical LED4 / pin19
@led5 = @pin20 -> physical LED5 / pin20
```

The board LEDs are active-low:

```text
move @led0, low    ; LED is on
move @led0, high   ; LED is off
```

The assembler rejects static bool accesses outside the implemented `@pin0..@pin127` range, except for reads from `@uart_ready` and `@uart_rx_ready`.

## Instructions

### System/control

```asm
nop
halt
wait r0
wait 27000000
jump label
```

`wait 0` finishes immediately — the RTL has an early exit for zero.

### Move

```asm
move r0, 123
move r0, π
move r0, &uart_tx
move r0, @7
move r0, @r1
move r0, @r1+4

move @7, r0
move @r1, r0
move @r1+4, r0

move @uart_tx, r0
move @uart_tx, 65

move b0, @uart_rx_ready
move r0, @uart_rx

move b0, @led0
move b0, @uart_ready

move @led0, low
move @led1, b0
```

### Integer / word

```asm
iadd r2, r0, r1
isub r2, r0, 1
imul r2, -6, 7

iand r2, r0, 0xff
ior  r2, r0, r1
ixor r2, r0, r1
inot r2, r0

shl r2, r0, 1
shr r2, r0, 1
sar r2, r0, 1
```

### Fixed Q7.25

```asm
fadd r2, r0, 1.0
fsub r2, r0, 0.5
fmul r2, r0, 2.0
fabs r2, r0

itof r1, 2
ftoi r2, 2.0
```

`fabs` computes the absolute value for fixed-point/signed 32-bit values.

### Bool

```asm
band b2, b0, true
bor  b2, b0, b1
bxor b2, b0, b1
bnot b2, b0
```

### Comparisons

```asm
cmp.eq b0, r1, r2
cmp.ne b0, r1, 0
cmp.lt b0, r1, 64
cmp.le b0, r1, r2
cmp.gt b0, r1, 4.0
cmp.ge b0, r1, 64
```

For fixed-point values produced by `fmul`, plain `cmp.eq` may be too fragile because of rounding.

For that case, use the macro:

```asm
cmp.feq b0, r1, 2.0, 0.0001
```

It expands to:

```asm
fsub tmp, r1, 2.0
fabs tmp, tmp
cmp.le b0, tmp, 0.0001
```

### Branch / convenience macros

```asm
inc r0
dec r0
neg r0, r1
fneg r0, r1

jump_if b0, label
jump_if_not b0, label

beq r0, r1, label
bne r0, 0, label
blt r0, 10, label
ble r0, r1, label
bgt r0, r1, label
bge r0, r1, label

imin r2, r0, r1
imax r3, r0, r1
fmin r4, r0, r1
fmax r5, r0, r1
```

Branch/min/max macros use `b7` as scratch.

### UART runtime macros

```asm
wait_rx
read_rx r0

wait_uart
write_tx r0
```

UART echo:

```asm
loop:
    read_rx r0
    write_tx r0
    jump loop
```

`read_rx` waits for `@uart_rx_ready`, then reads `@uart_rx`.

`write_tx` waits for `@uart_ready`, then writes `@uart_tx`.

### Complex macros

Complex support is currently implemented as assembler macros on top of the scalar ALU:

```asm
cadd z2, z0, z1
csub z2, z0, z1
cmul z2, z0, z1
cabs2 r8, z0
```

The macros use `t0..t3`.

## Predication

```asm
(b0)  move @led0, low
(!b0) move @led0, high
```

Available:

```text
(b0)..(b7)
(!b0)..(!b6)
```

`(!b7)` collides with the `always` encoding.
