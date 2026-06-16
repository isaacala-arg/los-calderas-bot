import json
from google import genai
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from src.models import EvaluationResult

_client = None

_PROMPT = """
Eres el curador de contenido para "Los Calderas", canal mexicano de autos y tecnología (TikTok/Reels/Shorts).
El creador es Isaac: 20 años, estudiante de ITC en el Tec de Monterrey, becario de Innovación IT en Nestlé.
Sus autos: Tesla Model Y LR 2026, Mini Countryman JCW 2021, Suzuki Swift Sport 2021.
Audiencia: mexicanos millennials/Gen Z, casual, que entienden de tech pero no son mecánicos.

Tu trabajo: elegir las 3 noticias con más potencial de video viral para México.

CRITERIOS DE SELECCIÓN (en este orden de prioridad):
1. RELEVANCIA PARA MÉXICO primero — noticias que impactan directamente a conductores mexicanos (precios MXN, regulaciones SEP/SEMARNAT/SCT, marcas con presencia en México, tendencias virales en redes mexicanas)
2. LATAM / NORTEAMÉRICA — noticias relevantes para la región que afecten a México próximamente
3. GLOBAL — solo si el impacto es tan grande que México no puede ignorarlo (recall masivo, quiebra de marca, cambio tecnológico disruptivo)

BONUS — elevar la puntuación si la noticia:
- Involucra vehículos eléctricos o híbridos en México → útil para comparar con el Tesla del creador
- Es sobre tecnología automotriz (FSD, autonomía, carga) → perspectiva del creador como usuario real
- Es viral en redes mexicanas o tiene >50k interacciones en México
- Involucra directamente alguno de los 3 autos del creador (Tesla, Mini, Swift)

Noticias disponibles:
{articles_text}

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "top_3_indices": [0, 1, 2],
  "urgency_score": 0,
  "urgency_index": null,
  "urgency_reasoning": "explicación de por qué estas 3 y qué tan urgente es la principal"
}}

urgency_score 7+ si: anuncio oficial de Tesla/Mini/Swift, recall masivo, noticia viral >50k en México, o tema que el creador puede comentar desde experiencia propia directa.
Solo JSON, sin nada más.
"""


def _get_client():
    global _client
    if _client is None:
        from src.config import settings
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(60),
    retry=retry_if_exception_type(ServerError),
    reraise=True,
)
def _call_gemini(client, model: str, contents: str):
    return client.models.generate_content(model=model, contents=contents)


def evaluate(articles: list) -> EvaluationResult:
    if not articles:
        return EvaluationResult(
            top_articles=[], urgent_article=None,
            urgency_score=0.0, urgency_reasoning="No articles"
        )

    articles_text = "\n".join(
        f"[{i}] {a.source} — {a.title}\n    {a.summary[:200]}"
        for i, a in enumerate(articles)
    )

    client = _get_client()
    response = _call_gemini(
        client, "gemini-2.5-flash", _PROMPT.format(articles_text=articles_text)
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

    top_articles = [articles[i] for i in data["top_3_indices"] if i < len(articles)]
    idx = data.get("urgency_index")
    urgent_article = articles[idx] if (idx is not None and idx < len(articles)) else None

    return EvaluationResult(
        top_articles=top_articles,
        urgent_article=urgent_article,
        urgency_score=float(data["urgency_score"]),
        urgency_reasoning=data["urgency_reasoning"],
    )
