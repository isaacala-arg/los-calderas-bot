"""Genera carruseles (texto por slide, listo para pegar en Canva)."""
import json
import random
from datetime import date, timedelta
from src.brain import llm_client
from src.brain.script_generator import _load_voice_guide, _load_contexto_actual
from src.models import Carousel

_JSON_SCHEMA = """
Responde SOLO con JSON válido (sin markdown, sin ```):
{
  "title": "título del carrusel (sin el prefijo 'Carrusel:')",
  "slides": [
    {"titulo": "texto grande del slide", "bullets": ["bullet corto 1", "bullet corto 2"], "fuente": "Medio — YYYY-MM-DD (solo slides de noticia; portada y cierre van sin fuente)"}
  ],
  "caption": "caption para el post (1-2 líneas, tono de Isaac)",
  "hashtags": ["5 hashtags"]
}
Reglas de slides: 6 a 8 slides. Slide 1 = portada con gancho (bullets vacíos, sin fuente).
Último slide = cierre con continuidad implícita (nunca 'sígueme' literal), sin fuente.
Bullets de máximo 12 palabras — es para leerse en un carrusel, no un ensayo.
"""

# Cuerpo de "Semana en tech". Recibe la ventana de fechas por concatenación
# (nunca .format() — los archivos de estilo pueden traer llaves).
_SEMANA_TECH_CUERPO = """Genera el carrusel semanal "Semana en tech: lo que pasó y por qué importa" para Los Calderas.

BÚSQUEDA AMPLIA (no te quedes con lo primero que salga): haz VARIAS búsquedas distintas —
noticias de IA de la semana, ciberseguridad, lanzamientos de gadgets, tech automotriz/EVs,
startups y empresas tech, y qué está EN TENDENCIA en redes esta semana. Junta al menos
10 noticias candidatas y de ahí ELIGE las 4-5 mejores. Enfócate en TECNOLOGÍA (IA,
ciberseguridad, gadgets, software, EVs); nada de política pura ni notas flojas de relleno.

PRIORIDAD GEOGRÁFICA al elegir: 1º noticias de/que afecten a MÉXICO, 2º LATAM,
3º las globales que de verdad importan (un lanzamiento mundial de IA sí; una nota local
de otro país no). El mix ideal: 1-2 de México/LATAM + 2-3 globales fuertes.

VERIFICACIÓN DE FECHA (no negociable): SOLO noticias PUBLICADAS dentro de la ventana de
fechas indicada abajo. Confirma la fecha de publicación en la fuente; si un tema suena
conocido, sospecha: puede ser noticia vieja recirculada (NO incluyas anuncios de hace
semanas o meses aunque sigan sonando). Si no puedes confirmar la fecha, descártala.

FUENTES (obligatorio): cada slide de noticia lleva su campo "fuente" con el MEDIO CONFIABLE
donde la verificaste + la fecha de publicación (formato "Medio — YYYY-MM-DD"). Medios
confiables: Reuters, AP, Bloomberg, The Verge, TechCrunch, Wired, Ars Technica, Xataka,
El País, Expansión, El Economista, DPL News, sitios oficiales de las empresas. NO uses
blogs random, agregadores ni redes sociales como fuente única.

Formato por slide de noticia: titulo = la noticia dicha como Isaac la diría (con gancho),
bullets = ["qué pasó en 1 línea", "por qué te importa / remate con humor"].
Es una SERIE SEMANAL: el cierre deja la expectativa de la próxima entrega sin decir "sígueme".
""" + _JSON_SCHEMA

_TEMA_CUERPO = """Genera un carrusel para Los Calderas sobre el tema indicado.

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
        slides.append({
            "titulo": str(s.get("titulo", "")),
            "bullets": [str(b) for b in bullets],
            "fuente": str(s.get("fuente", "") or ""),
        })

    return Carousel(
        title=str(data["title"]),
        slides=slides,
        caption=str(data.get("caption", "")),
        hashtags=[str(h) for h in data.get("hashtags", [])],
        carousel_type=carousel_type,
    )


def generate_semana_tech() -> Carousel:
    # La ventana de fechas va explícita: el modelo no sabe qué día es hoy,
    # y sin esto acepta noticias viejas recirculadas (feedback de Isaac).
    hoy = date.today()
    desde = hoy - timedelta(days=6)
    ventana = (
        f"HOY es {hoy.isoformat()}. Ventana válida de publicación: "
        f"del {desde.isoformat()} al {hoy.isoformat()} (últimos 7 días). "
        f"Cualquier noticia publicada antes del {desde.isoformat()} está PROHIBIDA.\n\n"
    )
    prompt = f"{_load_voice_guide()}\n\n---\n{_load_contexto_actual()}\n\n{ventana}{_SEMANA_TECH_CUERPO}"
    response = llm_client.heavy(prompt, search=True)
    return _parse(response, "semana_tech")


def generate_carousel_tema(topic: dict | None = None) -> Carousel:
    topic = topic or random.choice(CAROUSEL_TOPICS)
    tema_header = f"TEMA: {topic['title']}\nCONTEXTO: {topic['context']}\n\n"
    prompt = f"{_load_voice_guide()}\n\n---\n{_load_contexto_actual()}\n\n{tema_header}{_TEMA_CUERPO}"
    response = llm_client.heavy(prompt, search=True)
    return _parse(response, "tema")
