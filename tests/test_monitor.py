"""El monitor debe GUARDAR la noticia notable en Notion (no depender del email,
que nunca estuvo configurado en el workflow)."""
import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.run_monitor as rm
from src.models import Article, EvaluationResult


def _article(url):
    return Article(title="Noticia tech MX", url=url, summary="s", source="Unocero",
                   published=datetime.now(timezone.utc))


def test_monitor_guarda_noticia_notable_en_notion(mocker, tmp_path):
    mocker.patch.object(rm, "SEEN_URLS_PATH", str(tmp_path / "seen.json"))
    mocker.patch.object(rm, "fetch_articles", return_value=[_article("https://x/1")])
    mocker.patch.object(rm, "fetch_posts", return_value=[])
    mocker.patch.object(rm, "evaluate", return_value=EvaluationResult(
        top_articles=[_article("https://x/1")], urgent_article=None,
        urgency_score=7.0, urgency_reasoning="notición",
    ))
    write = mocker.patch.object(rm, "write_news", return_value="https://notion.so/n1")

    rm.main()

    write.assert_called_once()
    assert write.call_args[0][0].url == "https://x/1"


def test_monitor_no_guarda_si_score_bajo(mocker, tmp_path):
    mocker.patch.object(rm, "SEEN_URLS_PATH", str(tmp_path / "seen.json"))
    mocker.patch.object(rm, "fetch_articles", return_value=[_article("https://x/2")])
    mocker.patch.object(rm, "fetch_posts", return_value=[])
    mocker.patch.object(rm, "evaluate", return_value=EvaluationResult(
        top_articles=[_article("https://x/2")], urgent_article=None,
        urgency_score=3.0, urgency_reasoning="nada",
    ))
    write = mocker.patch.object(rm, "write_news", return_value="x")

    rm.main()

    write.assert_not_called()


def test_monitor_no_reevalua_lo_ya_visto(mocker, tmp_path):
    """Lo ya guardado en seen no se vuelve a mandar a Gemini (ahorro de tokens)."""
    seen = tmp_path / "seen.json"
    seen.write_text('["https://x/3"]', encoding="utf-8")
    mocker.patch.object(rm, "SEEN_URLS_PATH", str(seen))
    mocker.patch.object(rm, "fetch_articles", return_value=[_article("https://x/3")])
    mocker.patch.object(rm, "fetch_posts", return_value=[])
    ev = mocker.patch.object(rm, "evaluate")

    rm.main()

    ev.assert_not_called()
