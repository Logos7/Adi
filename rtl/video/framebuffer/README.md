# Video framebuffers

Reusable framebuffer storage modules.

The first planned framebuffer is 320x200 1bpp:

```text
320 * 200 = 64000 bits
64000 / 32 = 2000 words
10 words per scanline
```

`framebuffer_1bpp_dual_clock.v` stores two banks. The CPU port writes and reads
the back bank; the video port scans the front bank. A CPU `fbswap` request is
latched and applied on `video_frame_start`, then acknowledged back to the CPU
clock domain so drawing cannot race ahead into the buffer that is about to be
displayed.
