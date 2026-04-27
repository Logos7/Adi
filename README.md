# Adi / Brahma-Bija / Sutra

Adi to mały ekosystem własnego CPU na FPGA:

```text
Sutra .sutra → assembler → program.hex → Brahma-Bija RTL → Tang Nano 20K
                         ↘ symulator Python / testy
```

## Brahma-Bija / Sutra v1.4.0

Najważniejsze zasady składni:

```asm
move r0, 123          ; wartość natychmiastowa
move r1, π            ; stała matematyczna Q7.25
move r2, √500         ; pierwiastek jako stała Q7.25
move r3, &uart_tx     ; adres jako zwykła liczba

move r4, @7           ; pamięć pod adresem 7
move @7, r4
move r5, @r6          ; pamięć pod adresem trzymanym w r6
move @uart_tx, r0     ; MMIO UART TX
move b0, @uart_rx_ready
move r0, @uart_rx      ; MMIO UART RX
move @led0, low       ; LED świeci, bo LED-y Tang Nano 20K są aktywne niskim stanem
move b0, @uart_ready
```

Czyli:

```text
wartość          → bez prefiksu: 123, 1.0, π, true, high
pamięć / IO      → @: @7, @uart_tx, @uart_rx, @led0, @r1, @r1+4
adres jako liczba → &: &uart_tx, &led0, &pin15
```

Dla bool używamy tylko `true/false/high/low`. Surowe `0` i `1` są zawsze wartościami integer/word, nie bitami.

Nie używamy już `#123` ani `[adres]`.

## Rejestry

```text
r0..r31          normalne GPR
t0..t7           aliasy r24..r31, scratch/volatile
z0 = r0:r1
z1 = r2:r3
...
z11 = r22:r23    bezpieczne complex-pairs
```

`cmul/cabs2` używają `t0..t3` jako scratch. Operacje typu `iadd/fadd/cmp` z operandami natychmiastowymi mogą używać `t4..t7` jako scratch. Nie trzymaj tam ważnych danych przez makra.

## Stałe

Preferowany styl w przykładach i dokumentacji używa symboli matematycznych:

```asm
move r0, π
move r1, τ
move r2, e
move r3, φ
move r4, √2
move r5, √500
move r6, √0.5
move r7, ln2
move r8, 1/π
```

ASCII aliasy nadal działają, ale przykłady i dokumentacja używają znaków matematycznych.

## Fixed-point i porównania

`fmul` pracuje w Q7.25, więc wyniki po mnożeniu mogą różnić się o najmłodsze bity. Do testów fixed-point używaj tolerancji:

```asm
fmul r9, √2, √2
cmp.feq b0, r9, 2.0, 0.0001
```

Dostępne jest też:

```asm
fabs r1, r0
```

## GPIO / LED / piny

`@pinN` oznacza **bool_mem[N]**, a nie automatyczne sterowanie dowolnym fizycznym pinem FPGA. Fizyczne wyprowadzenia są w `cores/bija/rtl/src/brahma_bija_top.v`.

Obecnie Tang Nano 20K ma podłączone:

```text
@led0 = @pin15
@led1 = @pin16
@led2 = @pin17
@led3 = @pin18
@led4 = @pin19
@led5 = @pin20
```

LED-y są aktywne niskim stanem:

```asm
move @led0, low    ; świeci
move @led0, high   ; zgaszona
```

## Przykłady

Przykłady są poukładane katalogami:

```text
examples/00_basics/blink_led.sutra
examples/00_basics/predication_led.sutra

examples/01_memory/move_direct_indirect.sutra

examples/02_math/integer_fixed.sutra
examples/02_math/bool_ops.sutra
examples/02_math/constants.sutra

examples/03_complex/complex_led.sutra

examples/04_uart/hello_loop.sutra
examples/04_uart/diag_x.sutra
examples/04_uart/diag_y.sutra
examples/04_uart/diag_xy.sutra

examples/05_fractals/mandelbrot_uart.sutra
examples/05_fractals/julia_uart.sutra
examples/05_fractals/tricorn_uart.sutra
```


## Bootloader UART

Po jednorazowym wgraniu bitstreamu z bootloaderem nowe programy `.sutra` wrzucasz przez COM, bez Gowina:

```powershell
py tools\sutra_upload.py COM9 examples\05_fractals\julia_uart.sutra
```

Albo GUI/viewer:

```powershell
py apps\Adi.UartViewer\adi_uart_viewer.py
```

W v1.4.0 po konfiguracji FPGA CPU czeka w bootloaderze na pierwszy upload. `LED0` powinien świecić. Po udanym uploadzie program startuje i może wysyłać obraz przez UART.

## UART / Mandelbrot

Aktualny `program.hex` jest wygenerowany z:

```text
examples/05_fractals/mandelbrot_uart.sutra
```

Ramka UART:

```text
ADI0 width height pixels...
```

Domyślnie:

```text
64x64, maxIter=64
```

Uruchom viewer:

```powershell
py -m pip install pyserial
py apps\Adi.UartViewer\adi_uart_viewer.py COM8 --scale 6
```

Zmień `COM8` na port Tang Nano.

## Asemblacja

```powershell
py tools\sutra2hex.py examples\05_fractals\mandelbrot_uart.sutra cores\bija\rtl\src\program.hex
```

Potem w Gowin najlepiej pełne odświeżenie:

```text
zamknij Gowina
usuń cores/bija/rtl/impl
otwórz projekt
Synthesize → Place & Route → Programmer
```

## Testy

```powershell
py cores\bija\tests\test_symbolic_constants.py
py cores\bija\tests\test_mandelbrot_uart.py
```


## v1.4.0 — runtime UART RX

CPU potrafi teraz odbierać bajty z PC w działającym programie:

```asm
loop:
    read_rx r0
    write_tx r0
    jump loop
```

Nowe MMIO i makra:

```text
@uart_rx
@uart_rx_ready
wait_rx
read_rx rX
wait_uart
write_tx rX
beq/bne/blt/ble/bgt/bge
inc/dec/neg/fneg
imin/imax/fmin/fmax
@rX+offset
```

Przykłady:

```powershell
py tools\sutra_upload.py COM9 examples_uart\echo_rx.sutra --graphics off
py apps\Adi.UartViewerdi_uart_viewer.py
```

W terminalu GUI możesz teraz wysyłać tekst do FPGA bez reuploadu programu.

## v1.3 — UART bootloader

Po jednorazowym wgraniu bitstreamu możesz ładować nowe programy Sutra przez UART, bez Gowina:

```powershell
py tools\sutra_upload.py COM8 examples\05_fractals\mandelbrot_uart.sutra
```

Albo od razu upload + viewer:

```powershell
py apps\Adi.UartViewer\adi_uart_viewer.py COM8 --upload examples\05_fractals\julia_uart.sutra --scale 4
```

Bootloader używa protokołu `ADI!` i odpowiada `ADI_BOOT_OK`. Szczegóły: `cores/bija/docs/bootloader.md`.


## UART bootloader v1.3.1

Po jednorazowym wgraniu bitstreamu można ładować programy Sutra bez Gowina:

```powershell
py tools\sutra_upload.py COM9 examples\05_fractals\julia_uart.sutra
```

Albo uruchomić viewer z wybieraczką portu COM i programu:

```powershell
py apps\Adi.UartViewer\adi_uart_viewer.py
```

Bootloader działa bez przycisku reset: uploader spamuje `ADI!`, FPGA odpowiada `ADI_BOOT_READY`, a potem przyjmuje program.
