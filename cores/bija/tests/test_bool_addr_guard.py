import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, os.path.join(ROOT, 'sutra'))
from sutra import assemble, AssemblerError


def test_static_bool_address_guard():
    assemble('move b0, @uart_ready')
    assemble('move @pin127, true')
    try:
        assemble('move @128, true')
    except AssemblerError:
        pass
    else:
        raise AssertionError('move @128, true powinno być odrzucone')

if __name__ == '__main__':
    test_static_bool_address_guard(); print('OK')
