import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val


GEMINI_API_KEY = _require("GEMINI_API_KEY")
YOUTUBE_API_KEY = _require("YOUTUBE_API_KEY")
NOTION_API_TOKEN = _require("NOTION_API_TOKEN")
NOTION_DATABASE_ID = _require("NOTION_DATABASE_ID")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
