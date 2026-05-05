from _v10_common import run_source
from sutra import Q

def test_mul_fmul_fadd():
    cpu = run_source('''
        imul r1, -6, 7
        fmul r2, 0.5, 2.0
        fadd r3, 1.0, 1.0
        fsub r4, 2.0, 0.5
        halt
    ''')
    assert cpu.gpr[1] == 0xFFFFFFD6
    assert cpu.gpr[2] == (1 * Q) & 0xFFFFFFFF
    assert cpu.gpr[3] == (2 * Q) & 0xFFFFFFFF
    assert cpu.gpr[4] == int(round(1.5 * Q)) & 0xFFFFFFFF

if __name__ == '__main__':
    test_mul_fmul_fadd(); print('OK')
