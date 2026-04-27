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