from unittest.mock import MagicMock
from src.sources.youtube_fetcher import fetch_trending


def test_returns_articles_from_search(mocker):
    mock_item = {
        "id": {"videoId": "abc123"},
        "snippet": {
            "title": "Nuevo Tesla Model Y 2026 review en México",
            "description": "Probamos el nuevo Tesla...",
            "channelTitle": "AutosChannel",
            "publishedAt": "2026-06-15T10:00:00Z",
        },
    }
    mock_response = {"items": [mock_item]}

    mock_search = MagicMock()
    mock_search.list.return_value.execute.return_value = mock_response

    mock_youtube = MagicMock()
    mock_youtube.search.return_value = mock_search

    mocker.patch("googleapiclient.discovery.build", return_value=mock_youtube)

    articles = fetch_trending(max_results=1)

    assert len(articles) > 0
    assert "Tesla" in articles[0].title
    assert "youtube.com/watch" in articles[0].url
