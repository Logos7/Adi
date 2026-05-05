from _v10_common import run_source

def test_uart_tx_bytes():
    cpu = run_source('''
        move @uart_tx, 65
        move @uart_tx, 68
        move @uart_tx, 73
        move @uart_tx, 10
        halt
    ''')
    assert bytes(cpu.uart_tx_bytes) == b'ADI\n'

if __name__ == '__main__':
    test_uart_tx_bytes(); print('OK')
