from pathlib import Path
from _v10_common import assemble, flatten_program

ROOT = Path(__file__).resolve().parents[3]

def test_mandelbrot_and_julia_assemble():
    for rel in [
        'examples/05_fractals/mandelbrot_uart.sutra',
        'examples/05_fractals/julia_uart.sutra',
        'examples/05_fractals/tricorn_uart.sutra',
        'examples/04_uart/diag_xy.sutra',
    ]:
        src = (ROOT / rel).read_text(encoding='utf-8')
        words = flatten_program(assemble(src))
        assert len(words) > 0

if __name__ == '__main__':
    test_mandelbrot_and_julia_assemble(); print('OK')
