import praw
from datetime import datetime
from src.models import Article

SUBREDDITS = ["cars", "teslamotors", "electricvehicles", "Autos", "CarTalk"]


def fetch_posts(limit: int = 10) -> list:
    from src.config import settings

    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        return []

    reddit = praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent="los-calderas-bot/1.0",
    )
    articles = []
    for sub_name in SUBREDDITS:
        sub = reddit.subreddit(sub_name)
        for post in sub.hot(limit=limit):
            if post.score > 100:
                articles.append(Article(
                    title=post.title,
                    url=f"https://reddit.com{post.permalink}",
                    summary=(post.selftext[:500] if post.selftext else post.title),
                    source=f"r/{sub_name}",
                    published=datetime.utcfromtimestamp(post.created_utc),
                ))
    return articles
