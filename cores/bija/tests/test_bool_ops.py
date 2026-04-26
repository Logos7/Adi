from _v10_common import run_source

def test_bool_ops_and_unified_load_save():
    cpu = run_source('''
        band b0, true, false
        bor  b1, true, false
        bxor b2, true, false
        bnot b3, false
        move @led0, b1
        move b4, @led0
        halt
    ''')
    assert cpu.bool_regs[0] == 0
    assert cpu.bool_regs[1] == 1
    assert cpu.bool_regs[2] == 1
    assert cpu.bool_regs[3] == 1
    assert cpu.bool_regs[4] == 1

if __name__ == '__main__':
    test_bool_ops_and_unified_load_save(); print('OK')
