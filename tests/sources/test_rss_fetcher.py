from unittest.mock import MagicMock
from src.sources.rss_fetcher import fetch_articles


def test_returns_articles_from_feeds(mocker):
    entry = MagicMock()
    entry.title = "Tesla anuncia Model Y actualizado para México"
    entry.link = "https://motortrend.com/tesla"
    entry.summary = "El nuevo modelo llega con mejoras de batería..."
    entry.published_parsed = (2026, 6, 15, 10, 0, 0, 0, 0, 0)

    mock_feed = MagicMock()
    mock_feed.entries = [entry]
    mocker.patch("feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(max_per_feed=1)

    assert len(articles) > 0
    assert articles[0].title == "Tesla anuncia Model Y actualizado para México"
    assert articles[0].source == "Motor Trend"


def test_truncates_summary_to_500_chars(mocker):
    entry = MagicMock()
    entry.title = "Test"
    entry.link = "https://example.com"
    entry.summary = "x" * 1000
    entry.published_parsed = (2026, 6, 15, 10, 0, 0, 0, 0, 0)

    mock_feed = MagicMock()
    mock_feed.entries = [entry]
    mocker.patch("feedparser.parse", return_value=mock_feed)

    articles = fetch_articles(max_per_feed=1)
    assert len(articles[0].summary) <= 500
