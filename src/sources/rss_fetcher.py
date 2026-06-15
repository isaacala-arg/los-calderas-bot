import feedparser
from datetime import datetime
from src.models import Article

RSS_FEEDS = [
    ("Motor Trend", "https://www.motortrend.com/rss/"),
    ("Electrek", "https://electrek.co/feed/"),
    ("The Drive", "https://www.thedrive.com/feed"),
    ("Car and Driver", "https://www.caranddriver.com/rss/"),
    ("Top Gear", "https://www.topgear.com/rss.xml"),
]


def fetch_articles(max_per_feed: int = 5) -> list:
    articles = []
    for source_name, url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_per_feed]:
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            else:
                published = datetime.utcnow()

            # Extract summary and truncate to 500 chars
            summary = getattr(entry, "summary", "")
            if isinstance(summary, str):
                summary = summary[:500]

            articles.append(Article(
                title=getattr(entry, "title", ""),
                url=getattr(entry, "link", ""),
                summary=summary,
                source=source_name,
                published=published,
            ))
    return articles
