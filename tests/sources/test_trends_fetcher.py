import pandas as pd
from src.sources.trends_fetcher import fetch_trends


def test_returns_sorted_trends(mocker):
    mock_df = pd.DataFrame(
        {"Tesla México": [80], "autos eléctricos México": [60], "FSD México": [20]},
        index=[pd.Timestamp("2026-06-15")],
    )
    mock_pytrends = mocker.MagicMock()
    mock_pytrends.interest_over_time.return_value = mock_df
    mocker.patch("pytrends.request.TrendReq", return_value=mock_pytrends)

    results = fetch_trends()

    assert len(results) > 0
    assert results[0]["interest"] >= results[-1]["interest"]
    assert "keyword" in results[0]


def test_returns_empty_list_when_no_data(mocker):
    mock_pytrends = mocker.MagicMock()
    mock_pytrends.interest_over_time.return_value = pd.DataFrame()
    mocker.patch("pytrends.request.TrendReq", return_value=mock_pytrends)

    results = fetch_trends()
    assert results == []
