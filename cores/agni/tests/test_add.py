from _v10_common import run_source

def test_iadd_and_32_registers():
    cpu = run_source('''
        move r1, 100
        iadd r31, r1, 23
        iadd r16, r31, 1
        halt
    ''')
    assert cpu.gpr[31] == 123
    assert cpu.gpr[16] == 124

if __name__ == '__main__':
    test_iadd_and_32_registers(); print('OK')
