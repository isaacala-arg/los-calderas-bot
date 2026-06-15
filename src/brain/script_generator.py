import json
import os
import random
from datetime import datetime
from google import genai
from src.models import Article, Script

_client = None

VOICE_GUIDE_PATH = os.path.join(os.path.dirname(__file__), "../../style/los-calderas-voice.md")

_PROMPT = """{voice_guide}

---

Genera un guión para Los Calderas. Video de 60-90 segundos.

TEMA: {title}
CONTEXTO: {context}
TIPO: {script_type}

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "title": "título de referencia para Notion",
  "topic_context": "por qué es relevante ahora (1-2 oraciones)",
  "hook": "lo que dices o muestras en los primeros 2 segundos — hablado, natural, como con un amigo",
  "body": "guión completo del cuerpo (40-75 segundos)",
  "cta": "cierre — no comenta SÍ o NO, algo que genere saves o sea memorable",
  "visual_idea": "setup visual concreto que detenga el scroll antes de hablar",
  "hashtags_tiktok": ["hasta 5 hashtags"],
  "hashtags_reels": ["hasta 5 hashtags"],
  "hashtags_shorts": ["hasta 5 hashtags"],
  "script_type": "{script_type}"
}}
Solo JSON, sin nada más.
"""

_EVERGREEN_TOPICS = [
    {"title": "Realidad del costo de tener un Tesla en México", "context": "Gastos reales: carga, seguro, mantenimiento vs gasolina"},
    {"title": "Por qué el Swift Sport es el carro más honesto del mercado", "context": "Comparativa valor vs diversión de manejo"},
    {"title": "Mini JCW vs Tesla Model Y: cuál te hace más feliz al manejar", "context": "Sensaciones puras vs tecnología"},
    {"title": "FSD en Ciudad de México: lo que nadie te dice", "context": "Prueba real en tráfico mexicano"},
    {"title": "El carro que más sorprende a la gente cuando digo el precio", "context": "Expectativas vs realidad de los 3 autos"},
]


def _get_client():
    global _client
    if _client is None:
        from src.config import settings
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate(article: Article, script_type: str = "trend") -> Script:
    with open(VOICE_GUIDE_PATH, "r", encoding="utf-8") as f:
        voice_guide = f.read()

    prompt = _PROMPT.format(
        voice_guide=voice_guide,
        title=article.title,
        context=article.summary,
        script_type=script_type,
    )

    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned non-JSON response: {raw[:200]}") from e

    return Script(
        title=data["title"],
        topic_context=data["topic_context"],
        hook=data["hook"],
        body=data["body"],
        cta=data["cta"],
        visual_idea=data["visual_idea"],
        hashtags_tiktok=data["hashtags_tiktok"],
        hashtags_reels=data["hashtags_reels"],
        hashtags_shorts=data["hashtags_shorts"],
        script_type=data["script_type"],
    )


def generate_evergreen() -> Script:
    topic = random.choice(_EVERGREEN_TOPICS)
    article = Article(
        title=topic["title"],
        url="",
        summary=topic["context"],
        source="evergreen",
        published=datetime.utcnow(),
    )
    return generate(article, script_type="evergreen")
