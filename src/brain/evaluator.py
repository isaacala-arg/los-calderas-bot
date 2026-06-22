import json
from src.brain import gemini_client
from src.models import EvaluationResult

_PROMPT = """
Eres el curador de contenido para "Los Calderas", canal mexicano de autos y tecnología (TikTok/Reels/Shorts).
El creador es Isaac: 20 años, estudiante de ITC en el Tec de Monterrey, becario de Innovación IT en Nestlé.
Sus autos: Tesla Model Y LR 2026, Mini Countryman JCW 2021, Suzuki Swift Sport 2021.
Audiencia: mexicanos millennials/Gen Z, casual, que entienden de tech pero no son mecánicos.

Tu trabajo: elegir las 3 noticias con más potencial de video viral para México.
{trends_block}
CRITERIOS DE SELECCIÓN (en este orden de prioridad):
1. RELEVANCIA PARA MÉXICO primero — noticias que impactan directamente a conductores mexicanos (precios MXN, regulaciones SEP/SEMARNAT/SCT, marcas con presencia en México, tendencias virales en redes mexicanas)
2. LATAM / NORTEAMÉRICA — noticias relevantes para la región que afecten a México próximamente
3. GLOBAL — solo si el impacto es tan grande que México no puede ignorarlo (recall masivo, quiebra de marca, cambio tecnológico disruptivo)

BONUS — elevar la puntuación si la noticia:
- Coincide con una de las tendencias de búsqueda en México listadas arriba
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


def _build_trends_block(trends: list | None) -> str:
    """Formatea las tendencias de Google México para inyectar al prompt."""
    if not trends:
        return ""
    lines = "\n".join(f"- {t['keyword']} (interés: {t['interest']})" for t in trends[:5])
    return (
        "\nTENDENCIAS DE BÚSQUEDA EN MÉXICO AHORA MISMO (úsalas para priorizar):\n"
        f"{lines}\n"
    )


def evaluate(articles: list, trends: list | None = None) -> EvaluationResult:
    if not articles:
        return EvaluationResult(
            top_articles=[], urgent_article=None,
            urgency_score=0.0, urgency_reasoning="No articles"
        )

    articles_text = "\n".join(
        f"[{i}] {a.source} — {a.title}\n    {a.summary[:200]}"
        for i, a in enumerate(articles)
    )

    prompt = _PROMPT.format(
        articles_text=articles_text,
        trends_block=_build_trends_block(trends),
    )
    response = gemini_client.call(prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned non-JSON response: {raw[:200]}") from e

    top_articles = [articles[i] for i in data["top_3_indices"] if i is not None and i < len(articles)]
    idx = data.get("urgency_index")
    urgent_article = articles[idx] if (idx is not None and idx < len(articles)) else None

    return EvaluationResult(
        top_articles=top_articles,
        urgent_article=urgent_article,
        urgency_score=float(data["urgency_score"]),
        urgency_reasoning=data["urgency_reasoning"],
    )
