$root = Resolve-Path (Join-Path $PSScriptRoot "..")

$utf8 = New-Object System.Text.UTF8Encoding($false)

function W($path, $text) {
    $full = Join-Path $root $path
    $dir = Split-Path $full -Parent
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    [System.IO.File]::WriteAllText($full, $text, $utf8)
}

W "examples/04_uart/hello_loop.sutra" @'
; Sutra v1.4 — UART hello loop
; Wysyła "ADI\n" co chwilę i mruga LED0.

start:
    move @led0, high

    move r0, 65
    write_tx r0
    move r0, 68
    write_tx r0
    move r0, 73
    write_tx r0
    move r0, 10
    write_tx r0

    wait 27000000
    move @led0, low
    wait 27000000
    jump start
'@

W "examples/04_uart/diag_x.sutra" @'
; Sutra v1.4 — UART frame 64x64, pixel = x

start:
    move r0, 65
    write_tx r0
    move r0, 68
    write_tx r0
    move r0, 73
    write_tx r0
    move r0, 48
    write_tx r0
    move r0, 64
    write_tx r0
    move r0, 64
    write_tx r0

    move r5, 0
row_loop:
    move r4, 0
col_loop:
    move r0, r4
    write_tx r0

    inc r4
    blt r4, 64, col_loop

    inc r5
    blt r5, 64, row_loop

    jump start
'@

W "examples/04_uart/diag_y.sutra" @'
; Sutra v1.4 — UART frame 64x64, pixel = y

start:
    move r0, 65
    write_tx r0
    move r0, 68
    write_tx r0
    move r0, 73
    write_tx r0
    move r0, 48
    write_tx r0
    move r0, 64
    write_tx r0
    move r0, 64
    write_tx r0

    move r5, 0
row_loop:
    move r4, 0
col_loop:
    move r0, r5
    write_tx r0

    inc r4
    blt r4, 64, col_loop

    inc r5
    blt r5, 64, row_loop

    jump start
'@

W "examples/04_uart/diag_xy.sutra" @'
; Sutra v1.4 — UART frame 64x64, pixel = x + y

start:
    move r0, 65
    write_tx r0
    move r0, 68
    write_tx r0
    move r0, 73
    write_tx r0
    move r0, 48
    write_tx r0
    move r0, 64
    write_tx r0
    move r0, 64
    write_tx r0

    move r5, 0
row_loop:
    move r4, 0
col_loop:
    iadd r0, r4, r5
    write_tx r0

    inc r4
    blt r4, 64, col_loop

    inc r5
    blt r5, 64, row_loop

    jump start
'@

W "examples/04_uart/echo_rx.sutra" @'
; Sutra v1.4 — Echo UART RX -> TX.
; W terminalu wpisz tekst i naciśnij Wyślij.

loop:
    read_rx r0
    write_tx r0
    jump loop
'@

W "examples/04_uart/command_led.sutra" @'
; Sutra v1.4 — sterowanie LED0 po UART.
; '1' zapala LED0, '0' gasi LED0, inne znaki są odsyłane echem.

loop:
    read_rx r0

    beq r0, 49, led_on
    beq r0, 48, led_off

    write_tx r0
    jump loop

led_on:
    move @led0, low
    write_tx r0
    jump loop

led_off:
    move @led0, high
    write_tx r0
    jump loop
'@

W "examples/04_uart/rx_counter.sutra" @'
; Sutra v1.4 — licznik znaków z UART RX.
; Każdy odebrany znak zwiększa licznik i odsyła jego najniższy bajt.

start:
    move r1, 0

loop:
    read_rx r0
    inc r1
    write_tx r1
    jump loop
'@

W "examples/02_math/macro_pack.sutra" @'
; Sutra v1.4 — test makr: inc/dec/neg/fneg/min/max/offset/branch.
; Sukces zapala LED0..LED5, czyli ustawia je na low.

start:
    move r0, 7
    move r1, 3

    dec r0
    inc r1
    neg r2, r1
    fneg r3, 1.5

    imin r4, r0, r1
    imax r5, r0, r1
    fmin r6, 1.25, -2.5
    fmax r7, 1.25, -2.5

    move r8, 20
    move @r8+4, r4
    move r9, @r8+4

    cmp.eq b0, r0, 6
    cmp.eq b1, r1, 4
    cmp.eq b2, r2, -4
    cmp.feq b3, r3, -1.5, 0.0001
    cmp.eq b4, r9, 4

    move r10, 0
    bne r4, 4, fail
    bne r5, 6, fail
    cmp.feq b5, r6, -2.5, 0.0001
    jump_if_not b5, fail
    cmp.feq b5, r7, 1.25, 0.0001
    jump_if_not b5, fail
    move r10, 1

fail:
    cmp.eq b5, r10, 1

    (b0) move @led0, low
    (!b0) move @led0, high
    (b1) move @led1, low
    (!b1) move @led1, high
    (b2) move @led2, low
    (!b2) move @led2, high
    (b3) move @led3, low
    (!b3) move @led3, high
    (b4) move @led4, low
    (!b4) move @led4, high
    (b5) move @led5, low
    (!b5) move @led5, high

    wait 27000000
    jump start
'@

W "examples/05_fractals/mandelbrot_uart.sutra" @'
; Sutra v1.4 — Mandelbrot 64x64, maxIter=64
; z0 = z, z1 = c. cmul/cadd/cabs2 używają t0..t3 jako scratch.

start:
    move r0, 65
    write_tx r0
    move r0, 68
    write_tx r0
    move r0, 73
    write_tx r0
    move r0, 48
    write_tx r0
    move r0, 64
    write_tx r0
    move r0, 64
    write_tx r0

    move r5, 0
    move r3, -1.5

row_loop:
    move r4, 0
    move r2, -2.0

col_loop:
    move r0, 0.0
    move r1, 0.0
    move r11, 0

iter_loop:
    cabs2 r8, z0
    bgt r8, 4.0, pixel_done
    bge r11, 64, pixel_done

    cmul z0, z0, z0
    cadd z0, z0, z1

    inc r11
    jump iter_loop

pixel_done:
    write_tx r11

    fadd r2, r2, 0.046875
    inc r4
    blt r4, 64, col_loop

    fadd r3, r3, 0.046875
    inc r5
    blt r5, 64, row_loop

    jump start
'@

W "examples/05_fractals/julia_uart.sutra" @'
; Sutra v1.4 — Julia set 64x64, maxIter=64
; z0 = aktualne z = r0:r1
; z1 = stałe c   = r2:r3

start:
    move r0, 65
    write_tx r0
    move r0, 68
    write_tx r0
    move r0, 73
    write_tx r0
    move r0, 48
    write_tx r0
    move r0, 64
    write_tx r0
    move r0, 64
    write_tx r0

    move r2, -0.8
    move r3, 0.156

    move r5, 0
    move r7, -1.5

row_loop:
    move r4, 0
    move r6, -1.5

col_loop:
    fadd r0, r6, 0.0
    fadd r1, r7, 0.0
    move r11, 0

iter_loop:
    cabs2 r8, z0
    bgt r8, 4.0, pixel_done
    bge r11, 64, pixel_done

    cmul z0, z0, z0
    cadd z0, z0, z1

    inc r11
    jump iter_loop

pixel_done:
    write_tx r11

    fadd r6, r6, 0.046875
    inc r4
    blt r4, 64, col_loop

    fadd r7, r7, 0.046875
    inc r5
    blt r5, 64, row_loop

    jump start
'@

W "examples/05_fractals/tricorn_uart.sutra" @'
; Sutra v1.4 — Tricorn / Mandelbar 64x64, maxIter=64
; z = conjugate(z)^2 + c

start:
    move r0, 65
    write_tx r0
    move r0, 68
    write_tx r0
    move r0, 73
    write_tx r0
    move r0, 48
    write_tx r0
    move r0, 64
    write_tx r0
    move r0, 64
    write_tx r0

    move r5, 0
    move r3, -1.5

row_loop:
    move r4, 0
    move r2, -2.0

col_loop:
    move r0, 0.0
    move r1, 0.0
    move r11, 0

iter_loop:
    cabs2 r8, z0
    bgt r8, 4.0, pixel_done
    bge r11, 64, pixel_done

    fneg r1, r1
    cmul z0, z0, z0
    cadd z0, z0, z1

    inc r11
    jump iter_loop

pixel_done:
    write_tx r11

    fadd r2, r2, 0.046875
    inc r4
    blt r4, 64, col_loop

    fadd r3, r3, 0.046875
    inc r5
    blt r5, 64, row_loop

    jump start
'@

W "cores/bija/tests/test_v14_macros_uart_rx.py" @'
from sutra import assemble, flatten_program
from sim import CPU


def run(src: str, cycles: int = 10000) -> CPU:
    cpu = CPU()
    cpu.load_program(flatten_program(assemble(src)))
    cpu.run(cycles)
    return cpu


def test_inc_dec_neg_fneg():
    cpu = run('''
        move r0, 7
        move r1, 3
        dec r0
        inc r1
        neg r2, r1
        fneg r3, 1.5
        halt
    ''')
    assert cpu.gpr[0] == 6
    assert cpu.gpr[1] == 4
    assert cpu.gpr[2] == 0xFFFFFFFC
    assert cpu.gpr[3] == 0xFD000000


def test_minmax_integer_and_fixed():
    cpu = run('''
        imin r0, 6, 4
        imax r1, 6, 4
        fmin r2, 1.25, -2.5
        fmax r3, 1.25, -2.5
        halt
    ''')
    assert cpu.gpr[0] == 4
    assert cpu.gpr[1] == 6
    assert cpu.gpr[2] == 0xFB000000
    assert cpu.gpr[3] == 0x02800000


def test_offset_load_save_positive_and_negative():
    cpu = run('''
        move r0, 20
        move @r0+4, 55
        move @r0-1, 77
        move r1, @r0+4
        move r2, @r0-1
        halt
    ''')
    assert cpu.gpr[1] == 55
    assert cpu.gpr[2] == 77


def test_jump_if_and_jump_if_not():
    cpu = run('''
        move b0, true
        move b1, false
        jump_if b0, a
        move r0, 99
    a:
        jump_if_not b1, b
        move r1, 99
    b:
        move r2, 7
        halt
    ''')
    assert cpu.gpr[0] == 0
    assert cpu.gpr[1] == 0
    assert cpu.gpr[2] == 7


def test_branch_macros_all_directions():
    cpu = run('''
        move r0, 5
        move r1, 7
        move r10, 0
        blt r0, r1, a
        move r10, 99
    a:
        bgt r1, r0, b
        move r10, 99
    b:
        ble r0, 5, c
        move r10, 99
    c:
        bge r1, 7, d
        move r10, 99
    d:
        beq r0, 5, e
        move r10, 99
    e:
        bne r0, r1, f
        move r10, 99
    f:
        inc r10
        halt
    ''')
    assert cpu.gpr[10] == 1


def test_wait_uart_and_write_tx():
    cpu = CPU()
    cpu.load_program(flatten_program(assemble('''
        move r0, 65
        write_tx r0
        move r0, 66
        write_tx r0
        halt
    ''')))
    cpu.run(1000)
    assert bytes(cpu.uart_tx_bytes) == b'AB'


def test_read_rx_echo_macro():
    cpu = CPU()
    cpu.load_program(flatten_program(assemble('''
        read_rx r0
        write_tx r0
        halt
    ''')))
    cpu.push_uart_rx(ord('Z'))
    cpu.run(1000)
    assert cpu.gpr[0] == ord('Z')
    assert bytes(cpu.uart_tx_bytes) == b'Z'


def test_wait_rx_blocks_until_data():
    words = flatten_program(assemble('''
        wait_rx
        move r0, @uart_rx
        halt
    '''))
    cpu = CPU()
    cpu.load_program(words)
    cpu.run(20)
    assert not cpu.halted
    cpu.push_uart_rx(123)
    cpu.run(1000)
    assert cpu.halted
    assert cpu.gpr[0] == 123


if __name__ == '__main__':
    test_inc_dec_neg_fneg()
    test_minmax_integer_and_fixed()
    test_offset_load_save_positive_and_negative()
    test_jump_if_and_jump_if_not()
    test_branch_macros_all_directions()
    test_wait_uart_and_write_tx()
    test_read_rx_echo_macro()
    test_wait_rx_blocks_until_data()
    print('OK')
'@

W "cores/bija/tests/test_examples_compile.py" @'
from pathlib import Path
from sutra import assemble, flatten_program


ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / 'examples'


def test_all_examples_compile():
    files = sorted(EXAMPLES.rglob('*.sutra'))
    assert files
    for path in files:
        src = path.read_text(encoding='utf-8')
        words = flatten_program(assemble(src))
        assert words, str(path)


def test_examples_use_safe_uart_tx_macro():
    offenders = []
    for path in sorted(EXAMPLES.rglob('*.sutra')):
        text = path.read_text(encoding='utf-8')
        for no, line in enumerate(text.splitlines(), start=1):
            code = line.split(';', 1)[0].strip().lower()
            if code.startswith('move @uart_tx'):
                offenders.append(f'{path.relative_to(ROOT)}:{no}: {line.strip()}')
    assert offenders == []
'@

Write-Host "v1.4.2 examples/tests written."
