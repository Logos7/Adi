# Brahma-Bija RTL

The RTL is intentionally written as simple **Verilog-2001** for Gowin / Tang Nano 20K. It does not require SystemVerilog mode.

The current `program.hex` is the initial Sutra program image.

## Changing the program image

To change the initial program image:

```powershell
py tools/sutra2hex.py examples/bija/fractals/mandelbrot.sutra cores/bija/rtl/src/program.hex
```

For programs that use `.data`, also write a data image:

```powershell
py tools/sutra2hex.py examples/bija/graphics_3d/wire_demos/wire_cube.sutra cores/bija/rtl/src/program.hex --data-output cores/bija/rtl/src/data.hex
```

Then, in Gowin, it is best to do a full refresh:

```text
Close Gowin
Delete cores/bija/rtl/impl
Open the project
Synthesize
Place & Route
Programmer
```

Gowin may keep old artifacts, especially when only `program.hex` or `data.hex` has changed.

## Program ROM

In `brahma_bija_core.v`, the program is loaded with:

```verilog
$readmemh("src/program.hex", imem);
```

The path is relative to the Gowin RTL project. Do not use an absolute path, because the project should remain portable after unpacking it into any directory.

## UART

```text
baud:   115200
format: 8N1
clock:  27 MHz
TX:     pin69
RX:     pin70
```

Sutra:

```asm
move @uart_tx, 65
move b0, @uart_ready
```

`@uart_ready` in RTL returns the real state of the UART transmitter.

## Bool / GPIO / LED

The current core has:

```text
bool_mem[0..127]
```

`@pinN` in Sutra means **bool_mem[N]**. It is not an automatic connection to any arbitrary physical FPGA pin. Physical pin routing is done in `brahma_bija_top.v`.

On the Tang Nano 20K, the current top maps:

```text
gpio_out[15] -> led[0] -> physical pin15
gpio_out[16] -> led[1] -> physical pin16
gpio_out[17] -> led[2] -> physical pin17
gpio_out[18] -> led[3] -> physical pin18
gpio_out[19] -> led[4] -> physical pin19
gpio_out[20] -> led[5] -> physical pin20
```

The board LEDs are active-low:

```asm
move @led0, low     ; LED is on
move @led0, high    ; LED is off
```

## UART bootloader

The top-level contains:

```text
uart_rx
uart_tx
uart_rx.v
brahma_bija_bootloader.v
```

`program.hex` is still the initial fallback loaded through:

```verilog
$readmemh("src/program.hex", imem);
```

After a UART upload, the bootloader writes new instructions into `imem` and resets the CPU.

## Upload without Gowin

Upload a Sutra program without rebuilding the bitstream:

```powershell
py tools/sutra_upload.py COM9 examples/bija/fractals/julia.sutra
```

Viewer with GUI port and file selection:

```powershell
py apps/bija/uart_viewer.py
```

Upload through the viewer:

```powershell
py apps/bija/uart_viewer.py COM9 --upload examples/bija/graphics_3d/wire_demos/wire_cube.sutra
```

## UART / bootloader parameters

The UART and bootloader parameters are in `src/brahma_bija_top.v`:

```verilog
localparam [15:0] UART_CLKS_PER_BIT = 16'd234;
localparam [15:0] BOOT_MAX_WORDS = 16'd1024;
localparam [15:0] BOOT_MAX_DATA_WORDS = 16'd512;
localparam [31:0] BOOT_BYTE_TIMEOUT_CLKS = 32'd270000000;
```

For a 27 MHz clock:

```text
115200 baud -> UART_CLKS_PER_BIT = 234
```

## Constraint pins

Pins in `.cst`:

```text
uart_tx = pin69
uart_rx = pin70
```

If TX works but the bootloader does not respond with `ADI_BOOT_READY`, verify `uart_rx` in the constraints and in the board schematic first.
