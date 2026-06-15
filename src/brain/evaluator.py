import json
import google.generativeai as genai
from src.models import EvaluationResult

_model = None

_PROMPT = """
Eres el asistente de contenido para "Los Calderas", canal mexicano de autos (TikTok/Reels/Shorts).
El creador tiene: Tesla Model Y LR 2026, Mini Countryman JCW 2021, Suzuki Swift Sport 2021.
Audiencia: mexicanos millennials, casual, situaciones reales.

Noticias recientes:
{articles_text}

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "top_3_indices": [0, 1, 2],
  "urgency_score": 0,
  "urgency_index": null,
  "urgency_reasoning": "explicación"
}}

urgency_score 7+ si: anuncio oficial Tesla, recall masivo, noticia viral >50k interacciones, o involucra directamente los autos del creador.
Solo JSON, sin nada más.
"""


def _get_model():
    global _model
    if _model is None:
        from src.config import settings
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-1.5-flash")
    return _model


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

    model = _get_model()
    response = model.generate_content(_PROMPT.format(articles_text=articles_text))
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
