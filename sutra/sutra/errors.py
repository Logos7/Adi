"""Assembler exception types."""

from .constants import PRED_ALWAYS


class AssemblerError(Exception):
    pass


class _LabelReference(Exception):
    def __init__(self, opcode: int, label: str, pred: int = PRED_ALWAYS):
        self.opcode = opcode
        self.label = label
        self.pred = pred
