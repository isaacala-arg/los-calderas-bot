import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from src.brain.script_generator import generate, build_canal_context
from src.outputs.notion_writer import write_script
from src.outputs.notion_reader import get_recent_titles, get_approved_examples
from src.models import Article
from datetime import datetime

_SEARCH_CONFIG = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())]
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(60),
    retry=retry_if_exception_type(ServerError),
    reraise=True,
)
def _call_gemini(client, model: str, contents: str, config=None):
    return client.models.generate_content(model=model, contents=contents, config=config)


def research_topic(topic: str) -> Article:
    from src.config import settings
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = _call_gemini(
        client,
        "gemini-2.5-flash",
        f"""Investiga este tema buscando en internet para el canal automotriz mexicano "Los Calderas":

TEMA: {topic}

Busca información actual y proporciona un resumen factual que incluya:
- Qué pasó exactamente y cuándo (con fechas reales)
- Datos concretos: precios, velocidades, autonomía, dimensiones, fechas de lanzamiento, cifras de ventas
- Por qué es relevante para México y la industria automotriz
- Contexto: cómo se compara con otros productos similares
- Solo si aplica directamente: cómo afecta a dueños de Tesla, Mini o Suzuki Swift

Responde en español, 4-5 párrafos, tono informativo y preciso. Prioriza datos verificables sobre especulación.""",
        config=_SEARCH_CONFIG,
    )
    return Article(
        title=topic,
        url="",
        summary=response.text,
        source="investigación personalizada",
        published=datetime.utcnow(),
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
