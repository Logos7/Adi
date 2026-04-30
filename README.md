# Adi

Adi is a small FPGA CPU / virtual machine project for Tang Nano 20K, written in Verilog, with a tiny Sutra assembler, UART bootloader, graphics UART viewer and text UART terminal.

## Current status

- FPGA target: Sipeed Tang Nano 20K / Gowin GW2AR
- UART bootloader works
- Programs can be uploaded without rebuilding the bitstream
- Runtime UART RX is available through `@uart_rx` and `@uart_rx_ready`
- Text UART terminal is separated from the graphics viewer
- Text and framebuffer-style UART examples are supported
- Sutra macro pack is available for branches, UART waits, min/max and convenience operations

## Project layout

```text
Adi/
  apps/
    bija/
      uart_viewer.py
      uart_terminal.py

    indra/

  cores/
    bija/
      docs/
        isa.md

      rtl/
        brahma_bija.gprj
        src/
          *.v

      sim/
        __init__.py

      tests/
        test_v14_macros_uart_rx.py

  examples/
    bija/
      00_basics/
      01_memory/
      02_math/
      03_complex/
      04_uart/
      05_fractals/

  sutra/
    sutra/
      __init__.py

  tools/
    sutra_upload.py
    sutra-vscode/

  README.md
  .gitignore
  .gitattributes
```

## Build FPGA bitstream

Open in Gowin:

```text
cores/bija/rtl/brahma_bija.gprj
```

Then run:

```text
Synthesize
Place & Route
Generate Bitstream
Programmer
```

Before rebuilding, it is usually safest to remove the old Gowin implementation output:

```powershell
Remove-Item .\cores\bija\rtl\impl -Recurse -Force -ErrorAction SilentlyContinue
```

## Tools

### Graphics viewer

Use this for framebuffer/fractal examples that emit `ADI0` frames:

```powershell
py apps/bija/uart_viewer.py
```

This tool is intended for graphical UART output and resolution/iteration controls.

Use it for programs such as:

```text
examples/bija/05_fractals/*.sutra
```

### Text UART terminal

Use this for normal text-based Sutra programs:

```powershell
py apps/bija/uart_terminal.py
```

Upload and open terminal:

```powershell
py apps/bija/uart_terminal.py COM9 examples/bija/04_uart/echo_rx.sutra
```

The text terminal does not parse `ADI0` graphics frames and does not patch width/height/iteration constants.

Use it for programs such as:

```text
examples/bija/04_uart/echo_rx.sutra
examples/bija/04_uart/command_led.sutra
examples/bija/00_basics/*.sutra
```

## Upload program manually

Text program:

```powershell
py tools/sutra_upload.py COM9 examples/bija/04_uart/echo_rx.sutra --graphics off
```

Graphics/fractal program:

```powershell
py tools/sutra_upload.py COM9 examples/bija/05_fractals/julia_uart.sutra --width 96 --height 64 --max-iter 80 --graphics auto
```

## UART bootloader behavior

After programming the FPGA bitstream, the bootloader waits for the PC uploader.

Expected behavior:

```text
FPGA configured
LED0 stays on
PC sends ADI!
FPGA replies ADI_BOOT_READY
PC uploads program
FPGA replies ADI_BOOT_OK
CPU starts program
```

If the upload fails, the CPU should remain held by the bootloader instead of starting an old program.

## Runtime UART RX

Runtime UART RX allows a Sutra program to receive bytes from the PC while it is already running.

Important symbols:

```asm
@uart_rx
@uart_rx_ready
@uart_tx
@uart_ready
```

Minimal echo example:

```asm
loop:
    read_rx r0
    write_tx r0
    jump loop
```

Expanded manually:

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

## Sutra v1.4 macro pack

Convenience UART macros:

```asm
wait_rx
read_rx r0
wait_uart
write_tx r0
```

Branch macros:

```asm
jump_if b0, label
jump_if_not b0, label

beq r0, r1, label
bne r0, r1, label
blt r0, r1, label
ble r0, r1, label
bgt r0, r1, label
bge r0, r1, label
```

Convenience arithmetic macros:

```asm
inc r0
dec r0
neg r0, r1
fneg r0, r1
```

Min/max macros:

```asm
imin r0, r1, r2
imax r0, r1, r2
fmin r0, r1, r2
fmax r0, r1, r2
```

Indexed memory syntax:

```asm
move r0, @r1+4
move @r1+4, r0
```

## Examples

### Echo RX

```powershell
py apps/bija/uart_terminal.py COM9 examples/bija/04_uart/echo_rx.sutra
```

Type text into the terminal input field. The FPGA should echo received characters back.

### Command LED

```powershell
py apps/bija/uart_terminal.py COM9 examples/bija/04_uart/command_led.sutra
```

This example is intended for simple runtime command control over UART.

### Fractal viewer

```powershell
py apps/bija/uart_viewer.py
```

Use the graphics viewer for programs that emit `ADI0` framebuffer frames.

## Development workflow

Work on a feature branch:

```powershell
git switch -c feature/some-change
```

Check changes:

```powershell
git status
git diff --stat
```

Commit changes:

```powershell
git add .
git commit -m "Describe the change"
```

Merge after testing:

```powershell
git switch main
git merge feature/some-change
```

Tag stable versions:

```powershell
git tag v1.4.1
git push
git push origin v1.4.1
```

## Notes

Generated Gowin implementation files are intentionally not committed.

Do not commit:

```text
cores/**/impl/
*.fs
*.bit
*.bin
*.rpt
*.log
```

Bitstreams should be published separately as release artifacts, not stored directly in the repository history.
