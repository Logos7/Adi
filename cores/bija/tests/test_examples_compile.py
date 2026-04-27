from pathlib import Path
from sutra import assemble, flatten_program


ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / 'examples'


def test_all_examples_compile():
    files = sorted(EXAMPLES.rglob('*.sutra'))
    assert files
    for path in files:
        src = path.read_text(encoding='utf-8')
        words = flatten_program(assemble(src))
        assert words, str(path)


def test_examples_use_safe_uart_tx_macro():
    offenders = []
    for path in sorted(EXAMPLES.rglob('*.sutra')):
        text = path.read_text(encoding='utf-8')
        for no, line in enumerate(text.splitlines(), start=1):
            code = line.split(';', 1)[0].strip().lower()
            if code.startswith('move @uart_tx'):
                offenders.append(f'{path.relative_to(ROOT)}:{no}: {line.strip()}')
    assert offenders == []