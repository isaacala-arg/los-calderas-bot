"""Genera carruseles (texto por slide, listo para pegar en Canva)."""
import json
import random
from src.brain import llm_client
from src.brain.script_generator import _load_voice_guide, _load_contexto_actual
from src.models import Carousel

_JSON_SCHEMA = """
Responde SOLO con JSON válido (sin markdown, sin ```):
{{
  "title": "título del carrusel (sin el prefijo 'Carrusel:')",
  "slides": [
    {{"titulo": "texto grande del slide", "bullets": ["bullet corto 1", "bullet corto 2"]}}
  ],
  "caption": "caption para el post (1-2 líneas, tono de Isaac)",
  "hashtags": ["5 hashtags"]
}}
Reglas de slides: 6 a 8 slides. Slide 1 = portada con gancho (bullets vacíos).
Último slide = cierre con continuidad implícita (nunca 'sígueme' literal).
Bullets de máximo 12 palabras — es para leerse en un carrusel, no un ensayo.
"""

_SEMANA_TECH_PROMPT = """{voice_guide}

---
{contexto}

Genera el carrusel semanal "Semana en tech: lo que pasó y por qué importa" para Los Calderas.

BUSCA EN LA WEB las 4-5 noticias de tecnología MÁS relevantes de los últimos 7 días
(prioriza: IA, autos eléctricos/tech automotriz, ciberseguridad, gadgets con impacto en México).
VERIFICACIÓN: usa SOLO noticias que encuentres con la búsqueda y cuya fecha confirmes dentro de
los últimos 7 días; si no puedes verificar una noticia, no la incluyas. Nunca inventes.

Formato por slide de noticia: titulo = la noticia dicha como Isaac la diría (con gancho),
bullets = ["qué pasó en 1 línea", "por qué te importa a ti en México"].
Es una SERIE SEMANAL: el cierre deja la expectativa de la próxima entrega sin decir "sígueme".
""" + _JSON_SCHEMA

_TEMA_PROMPT = """{voice_guide}

---
{contexto}

Genera un carrusel para Los Calderas sobre este tema:
TEMA: {title}
CONTEXTO: {context}

Enseña algo útil con la voz de Isaac (analogías cotidianas, humor, cero humo).
Todo dato debe ser real y verificable; si algo no se puede verificar, márcalo "DATO NO VERIFICADO".
""" + _JSON_SCHEMA

CAROUSEL_TOPICS = [
    {"title": "5 cosas que aprendí siendo becario que no te enseñan en la escuela", "context": "Lifestyle profesional, alto potencial de guardado. Lecciones reales de oficina/corporativo SIN información confidencial de la empresa y sin nombrarla."},
    {"title": "Cómo leer las especificaciones de un carro eléctrico sin que te vendan humo", "context": "Glosario visual: kWh (el tanque), autonomía WLTP vs real, tiempo de carga AC vs DC, con analogías cotidianas."},
    {"title": "3 filosofías de conducción autónoma: Tesla vs Waymo vs tu sentido común", "context": "Comparativa de enfoques (visión vs lidar vs humano), explicada simple y con humor."},
    {"title": "BYD, Tesla y el resto: quién fabrica qué de su propio carro", "context": "Integración vertical explicada con analogías (el taquero que hace sus propias tortillas)."},
]


def _parse(response, carousel_type: str) -> Carousel:
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON: {raw[:200]}") from e

    slides = []
    for s in data.get("slides", []):
        bullets = s.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        slides.append({"titulo": str(s.get("titulo", "")), "bullets": [str(b) for b in bullets]})

    return Carousel(
        title=str(data["title"]),
        slides=slides,
        caption=str(data.get("caption", "")),
        hashtags=[str(h) for h in data.get("hashtags", [])],
        carousel_type=carousel_type,
    )


def generate_semana_tech() -> Carousel:
    prompt = _SEMANA_TECH_PROMPT.format(
        voice_guide=_load_voice_guide(), contexto=_load_contexto_actual()
    )
    response = llm_client.heavy(prompt, search=True)
    return _parse(response, "semana_tech")


def generate_carousel_tema(topic: dict | None = None) -> Carousel:
    topic = topic or random.choice(CAROUSEL_TOPICS)
    prompt = _TEMA_PROMPT.format(
        voice_guide=_load_voice_guide(), contexto=_load_contexto_actual(),
        title=topic["title"], context=topic["context"],
    )
    response = llm_client.heavy(prompt, search=True)
    return _parse(response, "tema")
