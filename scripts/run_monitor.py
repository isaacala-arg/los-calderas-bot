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


# Máximo de URLs a recordar — evita que seen_urls.json crezca infinitamente.
# Se conservan las más recientes (orden de inserción).
MAX_SEEN_URLS = 500


def load_seen_urls() -> list:
    if os.path.exists(SEEN_URLS_PATH):
        with open(SEEN_URLS_PATH, encoding="utf-8") as f:
            return list(json.load(f))
    return []


def save_seen_urls(urls: list) -> None:
    os.makedirs(os.path.dirname(SEEN_URLS_PATH), exist_ok=True)
    # Conservar solo las últimas MAX_SEEN_URLS
    trimmed = urls[-MAX_SEEN_URLS:]
    with open(SEEN_URLS_PATH, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, indent=2)


def main():
    seen_list = load_seen_urls()
    seen = set(seen_list)
    articles = fetch_articles(max_per_feed=3) + fetch_posts(limit=5)
    new_articles = [a for a in articles if a.url not in seen]

    if not new_articles:
        print("No new articles since last run.")
        return

    result = evaluate(new_articles)

    # SIEMPRE marcar todo lo nuevo como visto — así no se re-evalúa en Gemini
    # en la siguiente corrida (antes solo se marcaba la urgente: gasto de tokens).
    for a in new_articles:
        if a.url not in seen:
            seen.add(a.url)
            seen_list.append(a.url)

    if result.urgency_score >= 7 and result.urgent_article:
        article = result.urgent_article
        send_alert(article, result.urgency_score, result.urgency_reasoning)
        print(f"Alert sent: {article.title}")
    else:
        print(f"No urgent news. Urgency score: {result.urgency_score}/10")

    save_seen_urls(seen_list)


if __name__ == "__main__":
    main()
