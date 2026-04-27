from _v10_common import run_source
from sutra import assemble, flatten_program
from sim import CPU


def test_inc_dec_neg_minmax_and_offset():
    cpu = run_source('''
        move r0, 7
        move r1, 3
        inc r1
        dec r0
        neg r2, r1
        imin r3, r0, r1
        imax r4, r0, r1
        move r5, 10
        move @r5+4, 55
        move r6, @r5+4
        halt
    ''')
    assert cpu.gpr[0] == 6
    assert cpu.gpr[1] == 4
    assert cpu.gpr[2] == 0xFFFFFFFC
    assert cpu.gpr[3] == 4
    assert cpu.gpr[4] == 6
    assert cpu.gpr[6] == 55


def test_uart_rx_echo_macro():
    words = flatten_program(assemble('''
        read_rx r0
        write_tx r0
        halt
    '''))
    cpu = CPU()
    cpu.load_program(words)
    cpu.push_uart_rx(ord('Z'))
    cpu.run(1000)
    assert cpu.gpr[0] == ord('Z')
    assert bytes(cpu.uart_tx_bytes) == b'Z'


def test_branch_macros():
    cpu = run_source('''
        move r0, 5
        beq r0, 5, ok
        move r1, 99
    ok:
        inc r1
        halt
    ''')
    assert cpu.gpr[1] == 1


if __name__ == '__main__':
    test_inc_dec_neg_minmax_and_offset()
    test_uart_rx_echo_macro()
    test_branch_macros()
    print('OK')
