from _v10_common import run_source
from sutra import Q


def test_fabs_and_cmp_feq():
    cpu = run_source('''
        fabs r1, -1.5
        cmp.feq b0, r1, 1.5, 0.0001
        fmul r2, √2, √2
        cmp.feq b1, r2, 2.0, 0.0001
        halt
    ''')
    assert cpu.gpr[1] == int(round(1.5 * Q)) & 0xFFFFFFFF
    assert cpu.bool_regs[0] == 1
    assert cpu.bool_regs[1] == 1

if __name__ == '__main__':
    test_fabs_and_cmp_feq(); print('OK')
