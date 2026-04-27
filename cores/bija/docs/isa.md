# Brahma-Bija ISA / Sutra v1.4

## Styl

Oficjalny styl Sutra jest lowercase. Parser jest case-insensitive, więc `MOVE R0, π` też przejdzie, ale przykłady piszemy małymi literami.

```asm
move r0, π
fadd r1, r0, 1.0
move @led0, low
move b0, @uart_ready
```

## Operandy

```text
123        wartość integer
1.0        wartość fixed Q7.25
π          stała fixed Q7.25
τ          stała fixed Q7.25 = 2π
φ          złota proporcja fixed Q7.25
√500       stała fixed Q7.25 = sqrt(500)
true       wartość bool 1
false      wartość bool 0
high       wartość bool 1
low        wartość bool 0
0, 1       wartości integer/word, nigdy bool

@7         pamięć/IO pod adresem 7
@uart_tx   MMIO UART_TX
@uart_rx   MMIO UART_RX, odczyt ostatniego bajtu i skasowanie ready
@uart_rx_ready   bool MMIO, 1 gdy czeka bajt RX
@led0      alias bool_mem[15], który top.v mapuje na fizyczną LED0
@pin15     bool_mem[15], nie automatycznie dowolny fizyczny pin FPGA
@r1        pamięć/IO pod adresem zapisanym w r1

&uart_tx   adres UART_TX jako zwykła liczba
&led0      adres bool LED0 jako zwykła liczba, czyli 15
&pin15     adres bool 15 jako zwykła liczba
```

Nie używamy `#` dla immediate i nie używamy `[adres]`.

## Rejestry

```text
r0..r31          32-bit GPR
t0..t7           aliasy r24..r31, scratch/volatile
b0..b7           rejestry bool/predykaty
z0 = r0:r1
z1 = r2:r3
...
z11 = r22:r23
```

`z12..z15` nachodzą na `t0..t7`, dlatego nie są bezpieczne dla makr complex.

## Stałe matematyczne

Preferowane w dokumentacji/przykładach są znaki matematyczne:

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

ASCII aliasy nadal są akceptowane przez assembler, ale nie są stylem domyślnym. Przykłady i dokumentacja używają znaków matematycznych.

## Memory / IO / GPIO

Aktualny RTL implementuje:

```text
data_mem[0..255]       word RAM, 32-bit
bool_mem[0..127]       bool/GPIO RAM
@uart_tx = 240         word MMIO, zapis low8 wysyła bajt UART
@uart_rx = 241         word MMIO read-only, odczyt low8 odbiera bajt i czyści @uart_rx_ready
@uart_ready = 128      bool MMIO read-only, 1 gdy UART TX gotowy
@uart_rx_ready = 129   bool MMIO read-only, 1 gdy czeka bajt UART RX
```

Ważne: `@pinN` oznacza **adres bool_mem[N]**, a nie magiczne podłączenie dowolnego fizycznego pinu FPGA. Fizyczne wyprowadzenia robi `brahma_bija_top.v`.

Na Tang Nano 20K obecny `top.v` mapuje tylko:

```text
@led0 = @pin15 -> fizyczna LED0 / pin15
@led1 = @pin16 -> fizyczna LED1 / pin16
@led2 = @pin17 -> fizyczna LED2 / pin17
@led3 = @pin18 -> fizyczna LED3 / pin18
@led4 = @pin19 -> fizyczna LED4 / pin19
@led5 = @pin20 -> fizyczna LED5 / pin20
```

LED-y na płytce są aktywne niskim stanem:

```text
move @led0, low    ; LED świeci
move @led0, high   ; LED zgaszona
```

Assembler odrzuca statyczne dostępy bool poza zaimplementowanym zakresem `@pin0..@pin127`, z wyjątkiem odczytu `@uart_ready` i `@uart_rx_ready`.

## Instrukcje

### System/control

```asm
nop
halt
wait r0
wait 27000000
jump label
```

`wait 0` kończy się natychmiast — RTL ma wczesne wyjście dla zera.

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

`fabs` liczy wartość bezwzględną fixed-point/signed 32-bit.

### Bool

```asm
band b2, b0, true
bor  b2, b0, b1
bxor b2, b0, b1
bnot b2, b0
```

### Porównania

```asm
cmp.eq b0, r1, r2
cmp.ne b0, r1, 0
cmp.lt b0, r1, 64
cmp.le b0, r1, r2
cmp.gt b0, r1, 4.0
cmp.ge b0, r1, 64
```

Dla fixed-pointów, które przeszły przez `fmul`, zwykłe `cmp.eq` może być zbyt kruche przez rounding. Do tego jest makro:

```asm
cmp.feq b0, r1, 2.0, 0.0001
```

Rozwija się do:

```asm
fsub tmp, r1, 2.0
fabs tmp, tmp
cmp.le b0, tmp, 0.0001
```


### Makra branch / wygoda

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

Branch/min/max używają `b7` jako scratch.

### UART runtime macros

```asm
wait_rx
read_rx r0
wait_uart
write_tx r0
```

Echo UART:

```asm
loop:
    read_rx r0
    write_tx r0
    jump loop
```

`read_rx` czeka na `@uart_rx_ready`, potem czyta `@uart_rx`. `write_tx` czeka na `@uart_ready`, potem zapisuje `@uart_tx`.

### Complex macros

Complex jest obecnie makrami assemblera na scalar ALU:

```asm
cadd  z2, z0, z1
csub  z2, z0, z1
cmul  z2, z0, z1
cabs2 r8, z0
```

Makra używają `t0..t3`.

## Predykcja

```asm
(b0)  move @led0, low
(!b0) move @led0, high
```

Dostępne:

```text
(b0)..(b7)
(!b0)..(!b6)
```

`(!b7)` koliduje z kodem `always`.
