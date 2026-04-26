from _v10_common import run_source
from sutra import Q

def test_fadd():
    cpu = run_source('fadd r1, 1.0, 1.0\nhalt')
    assert cpu.gpr[1] == (2 * Q) & 0xFFFFFFFF

if __name__ == '__main__':
    test_fadd(); print('OK')
