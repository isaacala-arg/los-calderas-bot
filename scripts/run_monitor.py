import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sources.rss_fetcher import fetch_articles
from src.sources.reddit_fetcher import fetch_posts
from src.brain.evaluator import evaluate
from src.outputs.email_alerter import send_alert

SEEN_URLS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "state", "seen_urls.json"
)


def load_seen_urls() -> set:
    if os.path.exists(SEEN_URLS_PATH):
        with open(SEEN_URLS_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_urls(urls: set) -> None:
    os.makedirs(os.path.dirname(SEEN_URLS_PATH), exist_ok=True)
    with open(SEEN_URLS_PATH, "w", encoding="utf-8") as f:
        json.dump(list(urls), f, indent=2)


def main():
    seen = load_seen_urls()
    articles = fetch_articles(max_per_feed=3) + fetch_posts(limit=5)
    new_articles = [a for a in articles if a.url not in seen]

    if not new_articles:
        print("No new articles since last run.")
        return

    result = evaluate(new_articles)

    if result.urgency_score >= 7 and result.urgent_article:
        article = result.urgent_article
        if article.url not in seen:
            send_alert(article, result.urgency_score, result.urgency_reasoning)
            seen.add(article.url)
            save_seen_urls(seen)
            print(f"Alert sent: {article.title}")
        else:
            print("Urgent article already alerted — skipping.")
    else:
        seen.update(a.url for a in new_articles)
        save_seen_urls(seen)
        print(f"No urgent news. Urgency score: {result.urgency_score}/10")


if __name__ == "__main__":
    main()
