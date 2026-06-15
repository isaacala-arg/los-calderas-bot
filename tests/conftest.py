import pytest


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    env = {
        "GEMINI_API_KEY": "test-gemini-key",
        "YOUTUBE_API_KEY": "test-youtube-key",
        "NOTION_API_TOKEN": "test-notion-token",
        "NOTION_DATABASE_ID": "test-database-id",
        "GMAIL_USER": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "test-app-password",
        "ALERT_EMAIL": "test@outlook.com",
    }
    for key, val in env.items():
        monkeypatch.setenv(key, val)
