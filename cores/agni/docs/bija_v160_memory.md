# Brahma-Bija v1.6 memory profile

v1.6 expands the local CPU memories while keeping the v1.5 UART payload format.

## Limits

| Area | v1.5 | v1.6 |
|---|---:|---:|
| Program memory | 1024 x 32-bit | 2048 x 32-bit |
| Data memory | 512 x 32-bit | 2048 x 32-bit |
| Program address bits | 10 | 11 |
| Data address bits | 9 | 11 |
| Python code upload limit | 1024 words | 2048 words |
| Python data upload limit | 512 words | 2048 words |

## Notes

The UART boot protocol still uses version byte `2`, because the packet shape is unchanged:

```text
version:    u8
code_count: u16 little-endian
data_count: u16 little-endian
checksum:   u32 little-endian
code_words: code_count x u32 little-endian
data_words: data_count x u32 little-endian
```

Only the accepted maximum sizes and FPGA address widths changed.

## Suggested data map for larger graphics demos

```text
data_mem[0..255]       sin/cos LUTs
data_mem[256..511]     projected vertices / scratch / parameters
data_mem[512..1023]    mesh vertices, edge lists, curves
data_mem[1024..1535]   extra geometry or runtime tables
data_mem[1536..1663]   packed 64x64 1bpp framebuffer A
data_mem[1664..1791]   packed 64x64 1bpp framebuffer B, optional
data_mem[1792..2047]   reserved
```

Existing demos that still use framebuffer base `384` should keep working. New larger mesh demos can move the framebuffer to `1536` to avoid colliding with geometry data.
