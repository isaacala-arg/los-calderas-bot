import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brain import gemini_client
from src.brain.script_generator import generate, build_canal_context
from src.outputs.notion_writer import write_script
from src.outputs.notion_reader import get_recent_titles, get_approved_examples
from src.models import Article
from datetime import datetime, timezone


def research_topic(topic: str) -> Article:
    response = gemini_client.call(
        f"""Investiga este tema buscando en internet para el canal automotriz mexicano "Los Calderas":

TEMA: {topic}

Busca información actual y proporciona un resumen factual que incluya:
- Qué pasó exactamente y cuándo (con fechas reales)
- Datos concretos: precios, velocidades, autonomía, dimensiones, fechas de lanzamiento, cifras de ventas
- Por qué es relevante para México y la industria automotriz
- Contexto: cómo se compara con otros productos similares
- Solo si aplica directamente: cómo afecta a dueños de Tesla, Mini o Suzuki Swift

Responde en español, 4-5 párrafos, tono informativo y preciso. Prioriza datos verificables sobre especulación.""",
        config=gemini_client.SEARCH_CONFIG,
    )
    return Article(
        title=topic,
        url="",
        summary=response.text,
        source="investigación personalizada",
        published=datetime.now(timezone.utc),
    )


def main():
    topic = os.environ.get("CUSTOM_TOPIC", "").strip()
    if not topic:
        print("ERROR: Variable CUSTOM_TOPIC no configurada")
        sys.exit(1)

    print(f"Investigando tema: {topic}")
    article = research_topic(topic)

    recent_titles = get_recent_titles(days=45)
    approved_examples = get_approved_examples(limit=4)
    canal_context = build_canal_context(recent_titles, approved_examples)

    print("Generando guión...")
    script = generate(article, script_type="trend", canal_context=canal_context)

    url = write_script(script)
    print(f"Guión guardado en Notion: {url}")


if __name__ == "__main__":
    main()
