from _v10_common import run_source
from sutra import assemble, AssemblerError

def test_alu_cmp_pred():
    cpu = run_source('''
        move r1, 10
        isub r2, r1, 3
        iand r3, r1, 0b1100
        ior  r4, r1, 0b0101
        ixor r5, r1, 0b1111
        inot r6, r1
        shl r7, r1, 1
        sar r8, -8, 1
        cmp.eq b0, r2, 7
        cmp.eq b1, r3, 8
        (b0)  move r9, 111
        (!b1) move r10, 222
        halt
    ''')
    assert cpu.gpr[2] == 7
    assert cpu.gpr[3] == 8
    assert cpu.gpr[4] == 15
    assert cpu.gpr[5] == 5
    assert cpu.gpr[7] == 20
    assert cpu.gpr[8] == 0xFFFFFFFC
    assert cpu.gpr[9] == 111
    assert cpu.gpr[10] == 0

def test_old_syntax_is_rejected():
    for src in ('move r0, #7', 'move r0, [7]', 'load r0, 7', 'save @7, r0', 'move @led0, 1', 'move b0, 1'):
        try:
            assemble(src)
            assert False, src
        except AssemblerError:
            pass

if __name__ == '__main__':
    test_alu_cmp_pred(); test_old_syntax_is_rejected(); print('OK')
