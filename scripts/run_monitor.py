import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sources.rss_fetcher import fetch_articles
from src.sources.reddit_fetcher import fetch_posts
from src.brain.evaluator import evaluate
from src.outputs.email_alerter import send_alert
from src.outputs.notion_writer import write_news

# Umbral para guardar una noticia en Notion. 6+ = notable/útil para contenido.
NOTICIA_THRESHOLD = 6.0

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

    # Salida PRINCIPAL: guardar la mejor noticia notable en Notion (donde Isaac
    # trabaja y el workflow SÍ tiene credenciales). El email quedó como bonus
    # opcional — antes era la única salida y nunca estaba configurado.
    top = result.urgent_article or (result.top_articles[0] if result.top_articles else None)
    if top and result.urgency_score >= NOTICIA_THRESHOLD:
        try:
            url = write_news(top, result.urgency_reasoning)
            print(f"Noticia guardada en Notion ({result.urgency_score}/10): {top.title} -> {url}")
        except Exception as e:
            print(f"No se pudo guardar la noticia en Notion: {e}")
        # Bonus: si está muy urgente Y el email está configurado, además avisa por correo.
        if result.urgency_score >= 8 and result.urgent_article:
            send_alert(result.urgent_article, result.urgency_score, result.urgency_reasoning)
    else:
        print(f"Sin noticias notables esta corrida. Score: {result.urgency_score}/10")

    save_seen_urls(seen_list)


if __name__ == "__main__":
    main()
