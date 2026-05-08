# Clock RTL

Clock generation and clocking wrappers.

Vendor-specific clock primitives should stay in vendor subdirectories:

```text
rtl/clock/gowin/
rtl/clock/xilinx/
rtl/clock/lattice/
rtl/clock/sim/
```

Shared modules should instantiate a small wrapper instead of instantiating vendor primitives directly inside a CPU core.
