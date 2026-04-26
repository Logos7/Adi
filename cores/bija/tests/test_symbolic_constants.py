from _v10_common import run_source
from sutra import Q
import math

def test_symbolic_constants_and_roots():
    cpu = run_source('''
        move r1, π
        move r2, tau
        move r3, sqrt2
        move r4, φ
        move r5, √500
        move r6, sqrt(0.5)
        move r7, ln2
        move r8, &uart_tx
        halt
    ''')
    assert cpu.gpr[1] == int(round(math.pi * Q)) & 0xFFFFFFFF
    assert cpu.gpr[2] == int(round(2 * math.pi * Q)) & 0xFFFFFFFF
    assert cpu.gpr[3] == int(round(math.sqrt(2) * Q)) & 0xFFFFFFFF
    assert cpu.gpr[4] == int(round(((1 + math.sqrt(5)) / 2) * Q)) & 0xFFFFFFFF
    assert cpu.gpr[5] == int(round(math.sqrt(500) * Q)) & 0xFFFFFFFF
    assert cpu.gpr[6] == int(round(math.sqrt(0.5) * Q)) & 0xFFFFFFFF
    assert cpu.gpr[7] == int(round(math.log(2) * Q)) & 0xFFFFFFFF
    assert cpu.gpr[8] == 0xF0

if __name__ == '__main__':
    test_symbolic_constants_and_roots(); print('OK')
