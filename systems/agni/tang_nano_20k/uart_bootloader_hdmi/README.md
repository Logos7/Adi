# Agni UART bootloader + HDMI framebuffer

Experimental combined system for Tang Nano 20K.

This variant keeps the working Agni UART bootloader path and adds an HDMI scanout path driven by a separate dual-clock 1bpp framebuffer.

Display modes are selected with the board key:

- `0` - Agni external 320x200 framebuffer, mirrored from `fbclear` / `fbplot` / `fberase`
- `1..7` - built-in HDMI patterns preserved from the standalone HDMI experiment

Useful HDMI-only upload demos:

- `examples/agni/hdmi/fb_diag_hdmi.sutra`
- `examples/agni/hdmi/fb_checker_320x200_hdmi.sutra`

Both use `fbsize 320, 200` and do not transmit UART frames.

Open `agni_hdmi.gprj` in Gowin. UART upload should still work through the BL616 bridge; HDMI mode `0` shows the framebuffer, while the other modes are useful for confirming that the video path itself is alive.
