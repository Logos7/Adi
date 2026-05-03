# Bija examples

Clean example set for Brahma-Bija / Sutra.

The examples are grouped by what they demonstrate, not by release history.

## Groups

```text
basics       LED, UART, and small hardware sanity checks
fractals     fractal renderers for uart_viewer.py
graphics_2d  simple framebuffer and 2D graphics examples
graphics_3d  wireframe 3D examples
```

Current files:

```text
basics/alive_blink.sutra
basics/echo_rx.sutra
basics/fdiv_uart_test.sutra
basics/led_chaser.sutra

fractals/burning_ship.sutra
fractals/julia.sutra
fractals/julia_dynamic.sutra
fractals/mandelbrot.sutra
fractals/mandelbrot_zoom.sutra
fractals/sierpinski_1bit.sutra
fractals/tricorn.sutra

graphics_2d/checkerboard.sutra
graphics_2d/fb_pixel_test.sutra
graphics_2d/gradient_xy.sutra
graphics_2d/rings_int.sutra

graphics_3d/wire_cube_adi0.sutra
graphics_3d/wire_cube_adi1.sutra
graphics_3d/wire_cube_fine_adi1.sutra
```

## LED convention

Tang Nano 20K board LEDs are active-low:

```asm
move @led0, low     ; LED on
move @led0, high    ; LED off
```

Suggested meaning:

```text
@led0  alive / program started
@led1  loop heartbeat
@led2  UART RX/TX activity
@led3  computation active
@led4  frame/output active
@led5  error / unexpected path
```

Not every graphical example has to spend instructions on LED signalling. For visual demos the frame output itself is usually the primary liveness indicator.

## Tools

Text UART terminal:

```powershell
py apps\bija\uart_terminal.py COM9
```

Graphical UART viewer without upload:

```powershell
py apps\bija\uart_viewer.py COM9
```

Graphical UART viewer with upload:

```powershell
py apps\bija\uart_viewer.py COM9 --upload examples\bija\fractals\julia.sutra
py apps\bija\uart_viewer.py COM9 --upload examples\bija\graphics_3d\wire_cube_fine_adi1.sutra
```

Adjust `COM9` to match the board.

## Graphics formats

The viewer currently understands the frame formats used by the examples:

```text
ADI0 width height pixels...
ADI1 width height packed_1bpp_words...
```

Use **ADI0** for raw byte-per-pixel demos such as fractals and gradients.

Use **ADI1** for packed 1-bit framebuffer demos such as wireframes and monochrome patterns.

## Sutra v1.5 data image examples

Some examples use `.data` and require the v1.5 split code/data image upload path.

Normal upload through `sutra_upload.py` or `uart_viewer.py --upload` sends both code and data images.

For manual hex generation, include `--data-output`:

```powershell
py tools\sutra2hex.py examples\bija\graphics_3d\wire_cube_fine_adi1.sutra build\code.hex --data-output build\data.hex
```

## Example quality rules

Examples should:

- assemble cleanly,
- build through `assemble_image`,
- avoid direct `move @uart_tx, ...` writes and use `write_tx`,
- keep comments aligned with the actual frame format and memory map,
- use stable paths from the current folder layout,
- stay small enough to read and debug.
