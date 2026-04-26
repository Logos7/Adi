# Brahma-Bija RTL

RTL jest celowo napisany jako prosty **Verilog-2001** pod Gowin/Tang Nano 20K. Nie wymaga trybu SystemVerilog.

Aktualny `program.hex` jest obrazem programu Sutra. Żeby zmienić program:

```powershell
py tools\sutra2hex.py examples\05_fractals\mandelbrot_uart.sutra cores\bija\rtl\src\program.hex
```

Potem w Gowin najlepiej zrobić pełne odświeżenie:

```text
zamknij Gowina
usuń cores/bija/rtl/impl
otwórz projekt
Synthesize → Place & Route → Programmer
```

Gowin potrafi trzymać stare artefakty, szczególnie gdy zmienił się tylko `program.hex`.

## Program ROM

W `brahma_bija_core.v` program jest ładowany przez:

```verilog
$readmemh("src/program.hex", imem);
```

Ścieżka jest względna względem projektu RTL Gowina. Nie dajemy ścieżki absolutnej, bo projekt ma być przenośny po rozpakowaniu w dowolnym katalogu.

## UART

```text
baud: 115200
format: 8N1
clock: 27 MHz
TX: pin69
```

Sutra:

```asm
move @uart_tx, 65
move b0, @uart_ready
```

`@uart_ready` w RTL zwraca rzeczywisty stan nadajnika UART.

## Bool/GPIO/LED

Aktualny rdzeń ma:

```text
bool_mem[0..127]
```

`@pinN` w Sutra oznacza **bool_mem[N]**. To nie jest automatyczne wyprowadzenie dowolnego fizycznego pinu FPGA. Fizyczne mapowanie jest zrobione w `brahma_bija_top.v`.

Na Tang Nano 20K obecny top mapuje:

```text
gpio_out[15] -> led[0] -> fizyczny pin15
gpio_out[16] -> led[1] -> fizyczny pin16
gpio_out[17] -> led[2] -> fizyczny pin17
gpio_out[18] -> led[3] -> fizyczny pin18
gpio_out[19] -> led[4] -> fizyczny pin19
gpio_out[20] -> led[5] -> fizyczny pin20
```

LED-y są aktywne niskim stanem:

```asm
move @led0, low    ; świeci
move @led0, high   ; zgaszona
```

## UART bootloader

Od v1.3.1 top-level zawiera `uart_rx`, `uart_tx`, `uart_rx.v` i `brahma_bija_bootloader.v`.

`program.hex` nadal jest inicjalnym fallbackiem przez `$readmemh("src/program.hex", imem)`, ale po uploadzie UART bootloader zapisuje nowe instrukcje do `imem` i resetuje CPU.

Upload bez Gowina:

```powershell
py tools\sutra_upload.py COM9 examples_fractals\julia_uart.sutra
```

Viewer z GUI wybierania portu i pliku:

```powershell
py apps\Adi.UartViewerdi_uart_viewer.py
```

Parametry UART/bootloadera są w `src/brahma_bija_top.v`:

```verilog
localparam [15:0] UART_CLKS_PER_BIT = 16'd234;
localparam [15:0] BOOT_MAX_WORDS = 16'd1024;
localparam [31:0] BOOT_BYTE_TIMEOUT_CLKS = 32'd27000000;
```

Piny w `.cst`:

```text
uart_tx = pin69
uart_rx = pin70
```

Jeśli TX działa, ale bootloader nie odpowiada `ADI_BOOT_READY`, najpierw zweryfikuj `uart_rx` w constraintach/schemacie płytki.
