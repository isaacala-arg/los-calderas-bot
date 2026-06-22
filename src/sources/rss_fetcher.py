import re
import feedparser
from datetime import datetime, timezone
from src.models import Article

RSS_FEEDS = [
    ("Motor Trend", "https://www.motortrend.com/rss/"),
    ("Electrek", "https://electrek.co/feed/"),
    ("The Drive", "https://www.thedrive.com/feed"),
    ("Car and Driver", "https://www.caranddriver.com/rss/"),
    ("Top Gear", "https://www.topgear.com/rss.xml"),
]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean_summary(text: str) -> str:
    """Quita etiquetas HTML y normaliza espacios. Los feeds traen <p>, <a>,
    imágenes y notas de copyright que solo gastan tokens en el evaluador."""
    if not isinstance(text, str):
        return ""
    text = _TAG_RE.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = _WS_RE.sub(" ", text).strip()
    return text[:400]


def fetch_articles(max_per_feed: int = 5) -> list:
    articles = []
    for source_name, url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_per_feed]:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            else:
                published = datetime.now(timezone.utc)

            articles.append(Article(
                title=getattr(entry, "title", ""),
                url=getattr(entry, "link", ""),
                summary=_clean_summary(getattr(entry, "summary", "")),
                source=source_name,
                published=published,
            ))
    return articles
