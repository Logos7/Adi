# Brahma-Bija UART Bootloader

Od v1.3.2 program Sutra można ładować przez UART **bez przycisku reset i bez Gowina**.

## Idea

Bitstream zawiera:

```text
UART RX → bootloader FSM → program RAM → Brahma-Bija CPU
```

Po konfiguracji FPGA bootloader domyślnie trzyma CPU w resecie i czeka na pierwszy upload. Dzięki temu stary program nie zalewa UART-a ramkami zanim zdążysz uruchomić uploader. Po udanym uploadzie CPU startuje od `pc = 0`.

Gdy CPU już działa, bootloader nadal podsłuchuje `ADI!` na UART RX równolegle z programem. Kolejny upload powinien więc przejąć CPU bez przeprogramowywania FPGA.

## Workflow

Gowin jest potrzebny tylko po zmianie RTL/procka:

```text
Synthesize → Place & Route → Program
```

Potem upload programu:

```powershell
py tools\sutra_upload.py COM9 examples\05_fractals\julia_uart.sutra
```

Albo viewer z uploadem:

```powershell
py apps\Adi.UartViewer\adi_uart_viewer.py COM9 --upload examples\05_fractals\julia_uart.sutra --scale 4
```

Najwygodniej: odpal bez argumentów i wybierz port oraz plik w okienku:

```powershell
py apps\Adi.UartViewer\adi_uart_viewer.py
```

## Protokół v1.3.2

Host najpierw spamuje:

```text
"ADI!"
```

aż FPGA odpowie:

```text
ADI_BOOT_READY

```

Dopiero wtedy host wysyła:

```text
version   1 bajt    0x01
count     2 bajty   liczba słów 32-bit, little-endian
checksum  4 bajty   suma bajtów payloadu modulo 2^32, little-endian
payload   N*4 bajty słowa instrukcji uint32 little-endian
```

FPGA odpowiada:

```text
ADI_BOOT_OK

```

albo:

```text
ADI_BOOT_ERR

```

To rozwiązuje problem trafiania w reset przy pierwszym uploadzie: po świeżym wgraniu bitstreamu FPGA czeka w bootloaderze, LED0 świeci, a CPU nie nadaje ramek.

Jeżeli mimo v1.3.2 dalej widzisz w terminalu same małe bajty typu `\x01`, `\x02`, `\x03`, to najpewniej działa jeszcze stary bitstream albo bootloader nie widzi linii RX.

## Parametry

W `cores/bija/rtl/src/brahma_bija_top.v` są lokalne parametry:

```verilog
localparam [15:0] UART_CLKS_PER_BIT = 16'd234;
localparam [15:0] BOOT_MAX_WORDS = 16'd1024;
localparam [31:0] BOOT_BYTE_TIMEOUT_CLKS = 32'd27000000;
```

Dla zegara 27 MHz:

```text
115200 baud → UART_CLKS_PER_BIT = 234
```

`BOOT_BYTE_TIMEOUT_CLKS` określa, po ilu cyklach bez bajtu bootloader porzuca niepełny upload i oddaje CPU.

## LED0 status

LED-y na Tang Nano 20K są aktywne niskim stanem. W v1.3.2 tylko `LED0` jest używany jako status bootloadera:

```text
LED0 świeci → bootloader trzyma CPU i czeka/odbiera upload
LED0 wg programu → po udanym uploadzie, gdy CPU już działa
```

Pozostałe LED-y są normalnie sterowane przez program Sutra.

## Ograniczenia

Aktualna pamięć programu ma:

```text
1024 słowa × 32 bit = 4 KiB instrukcji
```

Jeśli program jest większy, uploader przerwie przed wysłaniem.

## Piny UART

W `constraints/brahma_bija.cst`:

```text
uart_tx = pin69
uart_rx = pin70
```

`uart_tx` jest sprawdzony u nas praktycznie, bo viewer odbiera dane. `uart_rx` jest ustawiony na `pin70`, ale jeśli bootloader nie odpowiada `ADI_BOOT_READY`, to pierwszą rzeczą do weryfikacji jest właśnie pin RX dla Twojej rewizji Tang Nano 20K / Dock.


## Diagnostyka

Po wgraniu bitstreamu v1.3.2 i odświeżeniu projektu Gowin:

```text
LED0 powinien świecić od razu po konfiguracji FPGA.
CPU nie powinien wysyłać ramek Mandelbrota/Julii przed pierwszym uploadem.
```

Jeżeli viewer/uploader nadal odbiera strumień pikseli przed uploadem, to znaczy, że Gowin zaprogramował stary bitstream albo nie zrobiłeś pełnego cleanu.

Jeżeli LED0 świeci, ale uploader nie dostaje `ADI_BOOT_READY`, najbardziej podejrzany jest pin `uart_rx`.
