# Sutra v1.5 code + data image

Sutra v1.5 separates instruction memory from data memory.

Before v1.5, lookup tables had to be initialized by code like this:

```sutra
move @r23, 0.024541
inc r23
move @r23, 0.049068
inc r23
```

That wastes instruction memory. In v1.5, data is emitted as a bootloader-loaded data blob:

```sutra
.data
sin_lut:
 .sin_lut 256

.code
main:
 move r21, sin_lut
 move r0, @r21
```

## Directives

```sutra
.data          ; switch to data section
.code          ; switch to code section
.org 256       ; set data_mem output address
label:         ; define data label as current data_mem address
.word 1, 2, 3  ; raw 32-bit words
.q7_25 1.0     ; fixed Q7.25 values
.sin_lut 256   ; generate sine table as Q7.25
.zero 16       ; emit zero words
```

The current hardware loader uses one flat `data_mem[0..N-1]` blob. Sparse `.org` gaps are emitted as zeros.

## Bootloader v1.5 protocol

After the host receives `ADI_BOOT_READY\n`, it sends:

```text
u8  version = 2
u16 code_count_le
u16 data_count_le
u32 checksum_le       ; sum of all code/data payload bytes modulo 2^32
u32 code_words[code_count]
u32 data_words[data_count]
```

The bootloader writes `code_words` to instruction memory and `data_words` to `data_mem` starting at address 0, then releases CPU reset after `ADI_BOOT_OK\n`.
