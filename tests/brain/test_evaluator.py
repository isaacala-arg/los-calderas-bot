import json
from datetime import datetime
from src.models import Article
from src.brain import evaluator as ev


def _make_article(title="Test article"):
    return Article(
        title=title,
        url="https://example.com",
        summary="Summary of the article",
        source="Test Source",
        published=datetime.utcnow(),
    )


def test_empty_articles_returns_empty_result():
    result = ev.evaluate([])
    assert result.top_articles == []
    assert result.urgent_article is None
    assert result.urgency_score == 0.0


def test_returns_top_articles(mocker):
    articles = [_make_article(f"Article {i}") for i in range(5)]

    gemini_response = json.dumps({
        "top_3_indices": [0, 2, 4],
        "urgency_score": 3.0,
        "urgency_index": None,
        "urgency_reasoning": "Nada urgente hoy",
    })

    mock_model = mocker.MagicMock()
    mock_model.generate_content.return_value.text = gemini_response
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    mocker.patch("google.generativeai.configure")
    ev._model = mock_model

    result = ev.evaluate(articles)

    assert len(result.top_articles) == 3
    assert result.urgency_score == 3.0
    assert result.urgent_article is None


def test_returns_urgent_article_when_score_high(mocker):
    articles = [_make_article("Tesla recall masivo en México")]

    gemini_response = json.dumps({
        "top_3_indices": [0],
        "urgency_score": 9.0,
        "urgency_index": 0,
        "urgency_reasoning": "Recall masivo afecta a dueños de Tesla en México",
    })

    mock_model = mocker.MagicMock()
    mock_model.generate_content.return_value.text = gemini_response
    ev._model = mock_model

    result = ev.evaluate(articles)

    assert result.urgency_score == 9.0
    assert result.urgent_article is not None
    assert result.urgent_article.title == "Tesla recall masivo en México"
