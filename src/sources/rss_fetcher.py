import re
import feedparser
from datetime import datetime, timezone
from src.models import Article

# Fuentes en español, enfocadas en México + tecnología (verificadas 2026-07).
# El canal es carros + tech y prioriza México, así que las fuentes también.
RSS_FEEDS = [
    ("Motorpasión México", "https://feeds.weblogssl.com/motorpasionmx"),  # carros MX
    ("Xataka", "https://feeds.weblogssl.com/xataka2"),                     # tech en español
    ("Unocero", "https://www.unocero.com/feed/"),                          # tech MX
    ("Hipertextual", "https://hipertextual.com/feed"),                     # tech LATAM/ES
    ("Wired en Español", "https://es.wired.com/feed/rss"),                 # tech en español
    ("Electrek", "https://electrek.co/feed/"),                             # autos eléctricos
    ("The Verge", "https://www.theverge.com/rss/index.xml"),               # tech global fuerte
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
