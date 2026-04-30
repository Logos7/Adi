# Bija examples

Clean example set for Brahma-Bija / Sutra.

## Groups

```text
00_led       small LED-only tests; safe sanity checks
01_text      text UART examples for uart_terminal.py
02_graphics  ADI0 framebuffer examples for uart_viewer.py
03_fractals  ADI0 fractal examples for uart_viewer.py
```

## LED convention

Tang Nano 20K board LEDs are active-low:

```asm
move @led0, low     ; LED on
move @led0, high    ; LED off
```

Every example sets at least `@led0` to `low` so the board shows that the program is alive.

Suggested meaning:

```text
@led0  alive / program started
@led1  loop heartbeat
@led2  UART RX/TX activity
@led3  computation active
@led4  frame/output active
@led5  error / unexpected path
```

## Tools

Text UART examples:

```powershell
py apps\bija\uart_terminal.py COM9 examples\bija\01_text\00_hello_loop.sutra
```

Graphics/fractal examples:

```powershell
py apps\bija\uart_viewer.py COM9 --upload examples\bija\03_fractals\00_mandelbrot.sutra --width 64 --height 64 --max-iter 64 --scale 4
```

Graphics examples emit exactly this frame format:

```text
'A' 'D' 'I' '0' width height pixels...
```
