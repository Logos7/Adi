# Brahma-Bija v1.6 memory overlay

Copy this package over the repository root.

This overlay increases the hardware/program upload limits:

- `imem`: 1024 -> 2048 words
- `data_mem`: 512 -> 2048 words
- code address path: 10 -> 11 bits
- data address path: 9 -> 11 bits
- Python upload limits: 1024/512 -> 2048/2048 words

Changed files:

```text
cores/bija/rtl/src/brahma_bija_core.v
cores/bija/rtl/src/brahma_bija_top.v
cores/bija/rtl/src/brahma_bija_bootloader.v
tools/sutra_upload.py
cores/bija/docs/bija_v160_memory.md
```

After copying, rebuild and flash the FPGA bitstream before uploading larger images.

Suggested check:

```powershell
cd D:\Adi
py -m compileall -q sutra tools apps/bija cores/bija/sim
py -m pytest -q cores/bija/tests
```

Then rebuild in Gowin and test upload again.
