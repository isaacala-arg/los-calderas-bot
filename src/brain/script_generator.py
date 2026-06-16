import json
import os
import random
from datetime import datetime
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from src.models import Article, Script

_SEARCH_CONFIG = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

_client = None

VOICE_GUIDE_PATH = os.path.join(os.path.dirname(__file__), "../../style/los-calderas-voice.md")

_PROMPT = """{voice_guide}

---

Genera un guión para Los Calderas. Video de 60-90 segundos.

TEMA: {title}
CONTEXTO (úsalo como base real; si tienes acceso a búsqueda, verifica y complementa con datos actuales): {context}
TIPO: {script_type}

## INSTRUCCIONES CRÍTICAS — lee antes de escribir cualquier cosa

### GANCHO — los primeros 2-3 segundos (lo más importante)
Tienes dos opciones. Elige la que más detenga el scroll:

**Opción A — Texto visual (5-10 palabras en pantalla, luego el creador habla):**
✅ "¿Un Tesla mexicano?" → luego el creador dice algo gracioso/opinionado
✅ "50 km/h. Es todo." → corte a cara de duda
✅ "El gobierno ya tiene su carro eléctrico" → dato sorprendente
❌ "¿Ustedes ya escucharon de X?" — no detiene nada

**Opción B — Ya estás en la situación (frase hablada, ya pasó algo):**
✅ "Nambre... acabo de ver el carro que el gobierno quiere que manejemos."
✅ "Oigan... ¿esto es un carro o un carrito de golf con techo?"
❌ "Hoy les voy a hablar de..." — PROHIBIDO
❌ "¿Sabías que...?" — PROHIBIDO

En el campo "hook": escribe el texto visual O la frase hablada. Máximo 12 palabras.

### CUERPO — datos reales, humor específico
- Usa DATOS CONCRETOS del contexto: velocidad, precio, autonomía, fechas, cifras exactas.
- Traduce técnico a cotidiano: no "carece de sistemas de seguridad pasiva" sino "no tiene bolsas de aire, y el gobierno dice que está bien porque técnicamente no es un carro".
- El humor debe ser específico y anclado en algo real mexicano:
  ✅ "aprobado por SHEINbaum" (juego con nombre de presidenta real)
  ✅ "el carro que pides por SHEIN y llega en bolsa de plástico"
  ❌ referencias inventadas o aleatorias (grupos de WhatsApp de Jetta A4, etc.)
  ❌ chistes que funcionarían en cualquier canal, no solo Los Calderas
- Menciona el Tesla/Mini/Swift del creador SOLO si el tema los involucra directamente. Si no aplica, NO los menciones.

### CTA — cierre que genere saves o shares
Piensa: ¿a quién específicamente le va a mandar esto el espectador?
✅ "Mándale esto a tu familiar que dice que el gobierno sí se preocupa por el medio ambiente"
✅ "Guarda esto para cuando te pregunten si los carros eléctricos ya llegaron a México"
❌ "Comenta SÍ o NO" — PROHIBIDO
❌ "Dale like" — PROHIBIDO
❌ "¿Tú qué opinas?" — PROHIBIDO

### CONSEJOS DE GRABACIÓN (filming_tips)
Da 2-3 tips MUY concretos para ESTE video específico — no consejos genéricos:
✅ "Empieza con texto '¿Un Tesla mexicano?' en negro sobre blanco, 1.5 seg, luego corte a tu cara con expresión de duda"
✅ "Para el dato del precio, saca la calculadora del teléfono en pantalla mientras lo mencionas"
✅ "El chiste de SHEIN dilo mientras muestras el carro en tu teléfono, no hablando a la cámara"
❌ "Grábate hablando frente a la cámara" — demasiado genérico, no sirve

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "title": "título corto para Notion (máx 60 caracteres)",
  "topic_context": "por qué es relevante ahora, 1-2 oraciones con datos específicos",
  "hook": "el gancho exacto — texto visual O frase hablada, máximo 12 palabras",
  "body": "guión completo del cuerpo (40-75 segundos hablados), con datos reales y humor específico al canal",
  "cta": "cierre que genere saves o que alguien mande a alguien específico",
  "visual_idea": "setup visual concreto que detenga el scroll antes de hablar",
  "filming_tips": ["tip 1 concreto para este video", "tip 2", "tip 3 opcional"],
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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(60),
    retry=retry_if_exception_type(ServerError),
    reraise=True,
)
def _call_gemini(client, model: str, contents: str, config=None):
    return client.models.generate_content(model=model, contents=contents, config=config)


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
    response = _call_gemini(client, "gemini-2.5-flash", prompt, config=_SEARCH_CONFIG)
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
        filming_tips=data.get("filming_tips", []),
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
