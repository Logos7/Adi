from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GRAMMAR = ROOT / "tools" / "sutra-vscode" / "syntaxes" / "sutra.tmLanguage.json"


def test_vscode_grammar_knows_hdmi_and_uart_namespaces():
    text = GRAMMAR.read_text(encoding="utf-8")

    assert "hdmi\\\\.(?:size|clear|plot|erase)" in text
    assert "uart\\\\.present[01]" in text
    assert "domain-instructions" in text


def test_vscode_grammar_keeps_legacy_framebuffer_mnemonics():
    text = GRAMMAR.read_text(encoding="utf-8")

    for token in ("fbsize", "fbclear", "fbplot", "fberase", "fbpresent1?"):
        assert token in text
