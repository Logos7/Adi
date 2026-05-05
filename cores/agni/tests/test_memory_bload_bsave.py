from _v10_common import run_source

def test_memory_and_gpio():
    cpu = run_source('''
        move r1, 123
        move @7, r1
        move r2, @7
        move r3, 9
        move @r3, r2
        move r4, @r3
        move @led0, high
        move b0, @led0
        halt
    ''')
    assert cpu.gpr[2] == 123
    assert cpu.gpr[4] == 123
    assert cpu.bool_regs[0] == 1

if __name__ == '__main__':
    test_memory_and_gpio(); print('OK')
