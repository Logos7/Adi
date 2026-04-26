from _v10_common import run_source
from sutra import Q

def test_complex_macros():
    cpu = run_source('''
        move r0, 1.0
        move r1, 2.0
        move r2, 3.0
        move r3, 4.0
        cmul z2, z0, z1
        cabs2 r8, z0
        halt
    ''')
    assert cpu.gpr[4] == (-5 * Q) & 0xFFFFFFFF
    assert cpu.gpr[5] == (10 * Q) & 0xFFFFFFFF
    assert cpu.gpr[8] == (5 * Q) & 0xFFFFFFFF

if __name__ == '__main__':
    test_complex_macros(); print('OK')
