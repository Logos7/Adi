from pathlib import Path
from _v10_common import assemble, flatten_program

ROOT = Path(__file__).resolve().parents[3]

def test_blink_assembles():
    src = (ROOT / 'examples/00_basics/blink_led.sutra').read_text(encoding='utf-8')
    words = flatten_program(assemble(src))
    assert len(words) > 0

if __name__ == '__main__':
    test_blink_assembles(); print('OK')
