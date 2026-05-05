# Sutra VS Code Extension

Syntax highlighting for Sutra v1.6, the Brahma-Bija assembler language used by Adi.

## Covered syntax

- comments with `;`
- labels and label references
- predicate prefixes: `(b0)` and `(!b0)`
- sections and data directives: `.data`, `.code`, `.org`, `.word`, `.u32`, `.q7_25`, `.sin_lut`, `.zero`, `.include`
- registers: `r0..r31`, `t0..t7`, `b0..b7`, `z0..z15`
- memory and address operands: `@100`, `@r1`, `@r1+4`, `@uart_tx`, `@led0`, `&uart_tx`, `&pin15`
- instructions and macros from Sutra v1.6, including framebuffer, UART, branches, complex macros, and min/max macros

## Example

```asm
.include "lib/bija/graphics_3d/wire_mesh_runtime.sutra"

.data
.org 0
.sin_lut 256

.code
main:
    move @273, 1
    move r20, 384
    fbsize 64, 64

loop:
    fbclear r20
    cmp.eq b0, r1, 10
    jump_if b0, done
    fbplot r20, r2, r3
    fbpresent1 r20
    wait 4200
    jump loop

done:
    halt
```

## Installation from the project directory

```powershell
powershell -ExecutionPolicy Bypass -File .	ools\install_sutra_vscode.ps1
```

Then close all VS Code/Cursor windows and reopen the repository.

You can also test the extension without installing it:

```powershell
code --extensionDevelopmentPath "D:\Adi	ools\sutra-vscode" "D:\Adi"
```
