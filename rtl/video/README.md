# Video RTL

Reusable video output and framebuffer building blocks.

Planned first target:

```text
320x200 1bpp logical framebuffer
640x480 HDMI/DVI scanout
2x horizontal scale
2x vertical scale
40-pixel top/bottom border
```

Keep physical board pins and constraints in `boards/`, and keep CPU memory-map integration in core/system-specific wrappers.
