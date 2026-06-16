import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from src.brain.script_generator import generate
from src.outputs.notion_writer import write_script
from src.models import Article
from datetime import datetime


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(60),
    retry=retry_if_exception_type(ServerError),
    reraise=True,
)
def _call_gemini(client, model: str, contents: str):
    return client.models.generate_content(model=model, contents=contents)


def research_topic(topic: str) -> Article:
    from src.config import settings
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = _call_gemini(
        client,
        "gemini-2.5-flash",
        f"""Investiga este tema para el canal automotriz mexicano "Los Calderas":

TEMA: {topic}

Proporciona un resumen factual y detallado que incluya:
- Qué pasó exactamente y cuándo
- Por qué es relevante para México y la industria automotriz
- Datos, cifras o estadísticas relevantes si las conoces
- Contexto de la industria automotriz
- Si aplica: cómo afecta a dueños de Tesla, Mini o Suzuki Swift

Responde en español, 4-5 párrafos, tono informativo y preciso.""",
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

    print("Generando guión...")
    script = generate(article, script_type="trend")

    url = write_script(script)
    print(f"Guión guardado en Notion: {url}")


if __name__ == "__main__":
    main()
