# Brahma-Bija RTL

RTL rdzenia Brahma-Bija jest celowo napisany jako prosty Verilog-2001 pod Gowin/Tang Nano 20K. Nie wymaga trybu SystemVerilog.

Projekt Gowina:

```text
cores/bija/rtl/brahma_bija.gprj
```

Aktualny `program.hex` jest obrazem fallbackowym. Domyślnie jest to teraz program echo UART RX -> TX z:

```text
examples/bija/04_uart/echo_rx.sutra
```

Normalnie program Sutra można wgrywać przez UART bootloader bez przebudowy bitstreamu.

## Szybka przebudowa fallbackowego ROM

Jeżeli chcesz zmienić `program.hex` i przebudować bitstream:

```powershell
py tools\sutra2hex.py examples\bija\04_uart\echo_rx.sutra cores\bija\rtl\src\program.hex
```

Potem w Gowin najlepiej zrobić pełne odświeżenie:

```text
zamknij Gowina
usuń cores/bija/rtl/impl
otwórz cores/bija/rtl/brahma_bija.gprj
Synthesize
Place & Route
Generate Bitstream
Programmer
```

Gowin potrafi trzymać stare artefakty, szczególnie gdy zmienił się tylko `program.hex`.

## Program ROM

W `brahma_bija_core.v` program fallbackowy jest ładowany przez:

```verilog
$readmemh("src/program.hex", imem);
```

Ścieżka jest względna względem projektu RTL Gowina. Nie używamy ścieżek absolutnych, żeby projekt był przenośny.

## UART

```text
baud: 115200
format: 8N1
clock: 27 MHz
uart_tx: pin69
uart_rx: pin70
```

Dla zegara 27 MHz i 115200 baud:

```text
27000000 / 115200 ~= 234
```

W `brahma_bija_top.v` ustawione są obecnie:

```verilog
localparam [15:0] UART_CLKS_PER_BIT = 16'd234;
localparam [15:0] BOOT_MAX_WORDS = 16'd1024;
localparam [31:0] BOOT_BYTE_TIMEOUT_CLKS = 32'd270000000;
localparam [31:0] BOOT_BLINK_HALF_PERIOD_CLKS = 32'd3375000;
```

`BOOT_BLINK_HALF_PERIOD_CLKS` daje LED0 cztery pełne mrugnięcia na sekundę podczas oczekiwania bootloadera.

## UART bootloader

Po konfiguracji FPGA bootloader czeka na upload przez UART. Typowy przebieg:

```text
FPGA configured
LED0 szybko mruga
PC wysyła ADI!
FPGA odpowiada ADI_BOOT_READY
PC wysyła program
FPGA odpowiada ADI_BOOT_OK
CPU startuje program
```

Jeżeli upload się nie uda, CPU powinien pozostać zatrzymany przez bootloader zamiast uruchamiać stary program.

Upload bez Gowina:

```powershell
py tools\sutra_upload.py COM9 examples\bija\05_fractals\julia_uart.sutra --width 96 --height 64 --max-iter 80 --graphics auto
```

Viewer graficzny:

```powershell
py apps\bija\uart_viewer.py
```

Terminal tekstowy:

```powershell
py apps\bija\uart_terminal.py COM9 examples\bija\04_uart\echo_rx.sutra
```

## Runtime UART RX

Program Sutra może odbierać bajty z PC podczas działania CPU.

Ważne symbole:

```text
@uart_rx
@uart_rx_ready
@uart_tx
@uart_ready
```

Minimalne echo:

```asm
loop:
    read_rx r0
    write_tx r0
    jump loop
```

Rozwinięte ręcznie:

```asm
loop:
    move b0, @uart_rx_ready
    (!b0) jump loop

    move r0, @uart_rx

wait_tx:
    move b0, @uart_ready
    (!b0) jump wait_tx

    move @uart_tx, r0
    jump loop
```

## Bool/GPIO/LED

Rdzeń ma:

```text
bool_mem[0..127]
```

`@pinN` w Sutra oznacza `bool_mem[N]`. To nie jest automatyczne wyprowadzenie dowolnego fizycznego pinu FPGA.

Fizyczne mapowanie LED-ów jest w `brahma_bija_top.v`:

```text
gpio_out[15] -> led[0] -> fizyczny pin15
gpio_out[16] -> led[1] -> fizyczny pin16
gpio_out[17] -> led[2] -> fizyczny pin17
gpio_out[18] -> led[3] -> fizyczny pin18
gpio_out[19] -> led[4] -> fizyczny pin19
gpio_out[20] -> led[5] -> fizyczny pin20
```

LED-y na Tang Nano 20K są aktywne niskim stanem:

```asm
move @led0, low
move @led0, high
```

`low` świeci, `high` gasi.

## Diagnostyka

Jeżeli TX działa, ale bootloader nie odpowiada `ADI_BOOT_READY`, sprawdź kolejno:

```text
1. Czy PC używa właściwego COM.
2. Czy baud to 115200.
3. Czy uart_rx jest poprawnie przypięty w .cst.
4. Czy pin70 faktycznie trafia do RX FPGA na Twojej płytce.
5. Czy LED0 szybko mruga po konfiguracji FPGA.
6. Czy uploader spamuje ADI! do czasu odpowiedzi.
```

## Pliki RTL

Najważniejsze pliki:

```text
cores/bija/rtl/src/brahma_bija_top.v
cores/bija/rtl/src/brahma_bija_core.v
cores/bija/rtl/src/brahma_bija_bootloader.v
cores/bija/rtl/src/uart_rx.v
cores/bija/rtl/src/uart_tx.v
cores/bija/rtl/src/program.hex
```

Nie commitujemy artefaktów Gowina:

```text
cores/**/impl/
*.fs
*.bit
*.bin
*.rpt
*.log
```
