from agent import _detect_language


def test_detect_portuguese():
    assert _detect_language("Me fale sobre sua trajetória e projetos") == "pt-BR"


def test_detect_english():
    assert _detect_language("Tell me about your career and projects") == "en"
