from src.sources.rss_fetcher import _clean_summary


def test_strips_html_tags():
    raw = "<p>El nuevo Tesla llega a <a href='x'>México</a></p>"
    assert _clean_summary(raw) == "El nuevo Tesla llega a México"


def test_collapses_whitespace():
    raw = "Línea uno\n\n   Línea dos\t\tfin"
    assert _clean_summary(raw) == "Línea uno Línea dos fin"


def test_handles_entities():
    raw = "Autos&nbsp;eléctricos &amp; híbridos"
    assert _clean_summary(raw) == "Autos eléctricos & híbridos"


def test_truncates_to_400():
    raw = "a" * 1000
    assert len(_clean_summary(raw)) == 400


def test_non_string_returns_empty():
    assert _clean_summary(None) == ""
    assert _clean_summary(123) == ""
