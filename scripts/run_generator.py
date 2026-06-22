import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sources.rss_fetcher import fetch_articles
from src.sources.reddit_fetcher import fetch_posts
from src.sources.youtube_fetcher import fetch_trending
from src.sources.trends_fetcher import fetch_trends
from src.brain.evaluator import evaluate
from src.brain.script_generator import (
    generate, generate_howto, generate_lifestyle, generate_opinion,
    generate_tech, generate_fsd, build_canal_context, append_avoid_hooks,
)
from src.outputs.notion_writer import write_script
from src.outputs.notion_reader import get_recent_titles, get_approved_examples


def _safe(label, fn, default):
    """Ejecuta un fetcher sin que un fallo (RSS caído, pytrends bloqueado)
    tumbe toda la generación. Devuelve `default` si truena."""
    try:
        return fn()
    except Exception as e:
        print(f"  ⚠️  {label} falló ({type(e).__name__}: {e}) — continuando sin eso")
        return default


def main():
    # Load canal context first so the generator avoids repeating topics
    # and learns from scripts Isaac has already approved
    print("Cargando contexto del canal desde Notion...")
    recent_titles = _safe("Notion títulos", lambda: get_recent_titles(days=45), [])
    approved_examples = _safe("Notion aprobados", lambda: get_approved_examples(limit=4), [])
    canal_context = build_canal_context(recent_titles, approved_examples)
    if recent_titles:
        print(f"  {len(recent_titles)} temas recientes cargados (para no repetir)")
    if approved_examples:
        print(f"  {len(approved_examples)} guiones aprobados como referencia de estilo")

    print("Fetching articles from all sources...")
    articles = (
        _safe("RSS", lambda: fetch_articles(max_per_feed=5), [])
        + _safe("Reddit", lambda: fetch_posts(limit=10), [])
        + _safe("YouTube", lambda: fetch_trending(max_results=5), [])
    )

    trends = _safe("Google Trends", fetch_trends, [])
    if trends:
        print(f"Top trends: {[t['keyword'] for t in trends[:3]]}")
    print(f"Total articles collected: {len(articles)}")

    # Trends alimentan al evaluador para priorizar lo que se busca en México ahora
    result = evaluate(articles, trends=trends)

    # Ganchos ya usados hoy, para que los 3 guiones no arranquen igual.
    used_hooks = []

    # Script 1: trend — from the top news article of the day
    if result.top_articles:
        top = result.top_articles[0]
        print(f"Generating trend script for: {top.title}")
        script1 = generate(top, script_type="trend", canal_context=canal_context)
    else:
        print("No top articles found, generating opinion instead")
        script1 = generate_opinion(canal_context=canal_context)
    used_hooks.append(script1.hook)
    url1 = write_script(script1)
    print(f"[1/3] Trend script saved: {url1}")

    # Script 2: pilar "enseña" — rota entre how-to, opinión y tech según el día.
    # Así el contenido no es solo carros: también tecnología (Claude, IA, ciberseguridad).
    teach_rotation = [generate_howto, generate_tech, generate_opinion]
    ctx2 = append_avoid_hooks(canal_context, used_hooks)
    script2 = teach_rotation[date.today().weekday() % len(teach_rotation)](canal_context=ctx2)
    used_hooks.append(script2.hook)
    url2 = write_script(script2)
    print(f"[2/3] {script2.script_type.capitalize()} script saved: {url2}")

    # Script 3: pilar "personal/formato" — rota entre lifestyle y FSD+listicle.
    personal_rotation = [generate_lifestyle, generate_fsd]
    ctx3 = append_avoid_hooks(canal_context, used_hooks)
    script3 = personal_rotation[date.today().weekday() % len(personal_rotation)](canal_context=ctx3)
    url3 = write_script(script3)
    print(f"[3/3] {script3.script_type.capitalize()} script saved: {url3}")

    print(f"\nListo! 3 guiones generados:")
    print(f"  1. Trend     → {url1}")
    print(f"  2. {script2.script_type.capitalize():<9} → {url2}")
    print(f"  3. {script3.script_type.capitalize():<9} → {url3}")


if __name__ == "__main__":
    main()
