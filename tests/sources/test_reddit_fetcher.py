from unittest.mock import MagicMock
from src.sources.reddit_fetcher import fetch_posts


def test_returns_high_score_posts(mocker):
    mock_post = MagicMock()
    mock_post.title = "FSD now available in Mexico"
    mock_post.permalink = "/r/teslamotors/comments/abc123"
    mock_post.selftext = "Great news for Mexican Tesla owners..."
    mock_post.created_utc = 1718445600.0
    mock_post.score = 500

    mock_low_post = MagicMock()
    mock_low_post.score = 10

    mock_sub = MagicMock()
    mock_sub.hot.return_value = [mock_post, mock_low_post]

    mock_reddit = MagicMock()
    mock_reddit.subreddit.return_value = mock_sub

    mocker.patch("praw.Reddit", return_value=mock_reddit)

    articles = fetch_posts(limit=5)

    assert any(a.title == "FSD now available in Mexico" for a in articles)
    assert all(a.source.startswith("r/") for a in articles)
