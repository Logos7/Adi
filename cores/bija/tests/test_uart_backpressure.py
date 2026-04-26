from _v10_common import assemble, flatten_program, CPU


def test_uart_backpressure_stalls_save():
    words = flatten_program(assemble('''
        move r0, 65
        move @uart_tx, r0
        halt
    '''))
    cpu = CPU(uart_tx_ready=0)
    cpu.load_program(words)
    cpu.step()  # move r0, 65
    assert cpu.pc == 1
    cpu.step()  # move stalls because UART not ready
    assert cpu.pc == 1
    assert cpu.uart_tx_bytes == []
    cpu.uart_tx_ready = 1
    cpu.step()
    assert cpu.pc == 2
    assert cpu.uart_tx_bytes == [65]

if __name__ == '__main__':
    test_uart_backpressure_stalls_save(); print('OK')
