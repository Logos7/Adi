# HDMI 320x200 1bpp v2

Standalone HDMI test for Tang Nano 20K.

This project is intentionally independent from Adi, Agni, Sutra and UART.

## Output

The physical HDMI mode is the official Sipeed 1280x720 mode.

Inside that signal this project draws a logical 320x200 1-bit image:

- logical resolution: 320x200
- scale: 2x2
- visible area on HDMI: 640x400
- centered in 1280x720
- black border around it
- white/black pixels only

The default mode is a diagnostic pattern. Press `KEY` to cycle modes:

0. diagnostic grid / border / diagonals
1. Sierpinski: `(x & y) == 0`
2. XOR blocks
3. XOR dense
4. radial bit pattern
5. Sierpinski with border
6. full white
7. black

## Folder

Put it here:

```text
D:\Adi\experimental\hdmi_320x200_1bpp_v2
```

Open:

```text
D:\Adi\experimental\hdmi_320x200_1bpp_v2\hdmi_320x200_1bpp_v2.gprj
```

## Important

Before synthesis, the current top module must be:

```text
video_top
```

The good log line is:

```text
NOTE (EX0101) : Current top module is "video_top"
```

If Gowin shows anything else:

```text
Hierarchy -> Update
right-click video_top -> Set As Top Module
```

or:

```text
Process -> Synthesize -> Configuration -> Top Module = video_top
```

## Why 720p?

This v2 deliberately uses the official Sipeed HDMI clocking path:

```text
27 MHz -> TMDS_rPLL -> serial clock -> CLKDIV /5 -> pixel clock
```

That avoids the PLL/clock experiments from the earlier broken versions.

## Source basis

The DVI transmitter, PLL wrapper, pin constraints and timing constraints are based on the official Sipeed TangNano-20K HDMI example.
