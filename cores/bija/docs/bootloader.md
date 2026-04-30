# Brahma-Bija UART Bootloader

Since v1.3.2, Sutra programs can be loaded over UART without pressing reset and without using Gowin.

## Idea

The bitstream contains:

    UART RX → bootloader FSM → program RAM → Brahma-Bija CPU

After FPGA configuration, the bootloader keeps the CPU in reset by default and waits for the first upload. This prevents the old program from flooding UART with frames before you have time to start the uploader. After a successful upload, the CPU starts at `pc = 0`.

Once the CPU is running, the bootloader still listens for `ADI!` on UART RX in parallel with the program. A later upload should therefore take over the CPU without reprogramming the FPGA.

## Workflow

Gowin is only needed after changing the RTL/CPU:

    Synthesize → Place & Route → Program

Then upload the program:

    py tools\sutra_upload.py COM9 examples\bija\05_fractals\julia_uart.sutra

Or use the viewer with upload support:

    py apps\bija\uart_viewer.py COM9 --upload examples\bija\05_fractals\julia_uart.sutra --scale 4

Most convenient: run it without arguments and select the port and file in the window:

    py apps\bija\uart_viewer.py

## Protocol v1.3.2

The host first spams:

    "ADI!"

until the FPGA responds with:

    ADI_BOOT_READY

Only then does the host send:

    version   1 byte     0x01
    count     2 bytes    number of 32-bit words, little-endian
    checksum  4 bytes    payload byte sum modulo 2^32, little-endian
    payload   N*4 bytes  uint32 instruction words, little-endian

The FPGA responds with:

    ADI_BOOT_OK

or:

    ADI_BOOT_ERR

This solves the problem of having to hit the reset timing during the first upload: after a fresh bitstream load, the FPGA waits in the bootloader, LED0 is on, and the CPU does not transmit frames.

If, despite v1.3.2, you still only see small bytes such as `\x01`, `\x02`, `\x03` in the terminal, then most likely an old bitstream is still running or the bootloader cannot see the RX line.

## Parameters

In `cores/bija/rtl/src/brahma_bija_top.v`, the local parameters are:

    localparam [15:0] UART_CLKS_PER_BIT = 16'd234;
    localparam [15:0] BOOT_MAX_WORDS = 16'd1024;
    localparam [31:0] BOOT_BYTE_TIMEOUT_CLKS = 32'd27000000;

For a 27 MHz clock:

    115200 baud → UART_CLKS_PER_BIT = 234

`BOOT_BYTE_TIMEOUT_CLKS` defines how many clock cycles without a byte are allowed before the bootloader aborts an incomplete upload and releases the CPU.

## LED0 status

The LEDs on the Tang Nano 20K are active-low. In v1.3.2, only `LED0` is used as the bootloader status indicator:

    LED0 on          → bootloader holds the CPU and waits for/receives an upload
    LED0 by program  → after a successful upload, when the CPU is already running

The remaining LEDs are controlled normally by the Sutra program.

## Limitations

The current program memory has:

    1024 words × 32 bit = 4 KiB of instructions

If the program is larger, the uploader aborts before sending it.

## UART pins

In `constraints/brahma_bija.cst`:

    uart_tx = pin69
    uart_rx = pin70

`uart_tx` has been verified in practice because the viewer receives data. `uart_rx` is set to `pin70`, but if the bootloader does not respond with `ADI_BOOT_READY`, the first thing to verify is the RX pin for your Tang Nano 20K / Dock revision.

## Diagnostics

After loading the v1.3.2 bitstream and refreshing the Gowin project:

    LED0 should turn on immediately after FPGA configuration.
    The CPU should not send Mandelbrot/Julia frames before the first upload.

If the viewer/uploader still receives a pixel stream before the upload, it means that Gowin programmed an old bitstream or you did not do a full clean.

If LED0 is on but the uploader does not receive `ADI_BOOT_READY`, the most suspicious point is the `uart_rx` pin.