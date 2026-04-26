import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, os.path.join(ROOT, "sutra"))
sys.path.insert(0, os.path.join(ROOT, "cores", "bija"))
from sutra import assemble, flatten_program, AssemblerError
from sim import CPU, disassemble

def run_source(source: str, max_cycles: int = 5000) -> CPU:
    cpu = CPU()
    cpu.load_program(flatten_program(assemble(source)))
    cpu.run(max_cycles=max_cycles)
    return cpu
