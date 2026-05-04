"""Sutra — assembler for the Brahma-Bija processor."""

from . import constants as _constants
from . import errors as _errors
from . import parsing as _parsing
from . import encoding as _encoding
from . import macros as _macros
from . import assembler as _assembler
from . import image as _image

for _module in (
    _constants,
    _errors,
    _parsing,
    _encoding,
    _macros,
    _assembler,
    _image,
):
    for _name, _value in _module.__dict__.items():
        if not (_name.startswith("__") and _name.endswith("__")):
            globals()[_name] = _value

for _name in (
    "constants",
    "errors",
    "parsing",
    "encoding",
    "macros",
    "assembler",
    "image",
):
    globals().pop(_name, None)

del _constants, _errors, _parsing, _encoding, _macros, _assembler, _image
del _module, _name, _value
