from _v10_common import run_source
from sutra import Q

def test_itof_ftoi():
    cpu = run_source('''
        itof r1, 2
        ftoi r2, 2.0
        ftoi r3, -1.0
        halt
    ''')
    assert cpu.gpr[1] == (2 * Q) & 0xFFFFFFFF
    assert cpu.gpr[2] == 2
    assert cpu.gpr[3] == 0xFFFFFFFF

if __name__ == '__main__':
    test_itof_ftoi(); print('OK')
