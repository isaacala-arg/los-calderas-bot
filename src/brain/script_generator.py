import json
import os
import random
from datetime import datetime, timezone
from src.brain import gemini_client
from src.models import Article, Script

_STYLE_DIR = os.path.join(os.path.dirname(__file__), "../../style")
VOICE_GUIDE_PATH = os.path.join(_STYLE_DIR, "los-calderas-voice.md")
CONTEXTO_ACTUAL_PATH = os.path.join(_STYLE_DIR, "contexto-actual.md")

# ─── INSTRUCCIONES COMUNES (DRY — se inyectan en todos los tipos) ──────────────
_COMMON = """
FORMATO: Reel vertical de 30 a 60 segundos. El campo "body" es el guión natural
(lo que Isaac diría platicando, no un ensayo) y debe tener entre 90 y 170 palabras.
Si tiene menos de 80 palabras, está incompleto.

REGLA DE ORO: el video tiene que ENSEÑAR algo útil Y dar risa. Si no cumple ambas, reescríbelo.

ENCUADRE DE CARROS (obligatorio, ver voice guide):
- Swift = de Isaac, el protagonista, el que maneja a diario.
- Tesla = de su PAPÁ, apodo "el Caldermóvil", tiene FSD, se carga en plazas (cargar cuesta pero menos que gasolina — NUNCA "gratis").
- Mini = de su MAMÁ.
- NUNCA escribas "mi Tesla" o "mi Mini" como si Isaac fuera el dueño.

ADÁPTALO AL CONTEXTO ACTUAL (abajo): recrea el tema para que sea filmable HOY, en un
lugar que Isaac tenga disponible ahora. Si el tema asume un lugar que no tiene (p.ej. la
escuela en vacaciones), cámbialo a algo que sí pueda grabar (home office, manejando el Swift, gym, plaza, casa).

MODO DIRECTOR (estilo plática, fácil de grabar y editar):
- "spot": un lugar concreto y FÁCIL, de su contexto actual.
- "como_grabar": equipo + setup de UNA sola toma continua. Cel + DJI Mic SIEMPRE. Tripie sobre el tablero si maneja; dron Neo solo si la toma es fácil. Nada de producción complicada.
- "puntos": 2 a 4 puntos para que Isaac improvise con sus palabras (NO teleprompter palabra por palabra).
- "arranque": las primeras palabras TEXTUALES + qué hace en cámara los primeros 3 segundos.

VOCABULARIO: solo español mexicano de CDMX (nambre, no manches, o sea, la neta, te explico, te lo chismeo, wey). NUNCA candela/chévere/bacán.

Responde SOLO con JSON válido (sin markdown, sin ```):
{{
  "title": "título corto para Notion (máx 60 caracteres)",
  "topic_context": "qué enseña y por qué importa ahora, 1-2 oraciones",
  "hook": "los primeros 2 segundos, máximo 12 palabras, que pare el scroll",
  "body": "guión natural completo, 90-170 palabras, con un momento de risa y algo que enseñe",
  "cta": "cierre que sea el remate del chiste o invite a guardar/compartir; nunca 'dale like'",
  "spot": "lugar concreto y fácil donde grabarlo (de su contexto actual)",
  "como_grabar": "equipo + setup de una sola toma fácil (cel/DJI Mic/tripie/dron Neo)",
  "puntos": ["punto 1 a tocar", "punto 2", "punto 3 opcional"],
  "arranque": "primeras palabras textuales + qué hace en cámara los primeros 3 seg",
  "hashtags_tiktok": ["hasta 5 hashtags"],
  "hashtags_reels": ["hasta 5 hashtags"],
  "hashtags_shorts": ["hasta 5 hashtags"],
  "script_type": "{script_type}"
}}
Solo JSON, sin nada más.
"""

# ─── GUÍA POR TIPO (corta — lo específico de cada formato) ─────────────────────
_TYPE_GUIDANCE = {
    "trend": (
        "TIPO: NOTICIAS / TENDENCIAS. Reacciona a una noticia real de carros o tecnología con la "
        "perspectiva de Isaac (ingeniero, usuario real). Datos concretos traducidos a lo cotidiano. "
        "Gancho que te mete en la situación, no que la anuncia. Si puedes, verifica datos con búsqueda."
    ),
    "howto": (
        "TIPO: HOW-TO / DATOS REALES. Resuelve una duda real con cifras concretas. Revela el dato o "
        "número AL INICIO (anti-suspenso). Estructura estilo Cristian: la duda real → cómo funciona simple → qué significa para ti."
    ),
    "lifestyle": (
        "TIPO: LIFESTYLE BECARIO. Un pedazo real de la vida de Isaac (home office, gym, manejar el Swift, "
        "su proyecto). Autoburla y honestidad. No es teleprompter: dale los puntos para improvisar."
    ),
    "opinion": (
        "TIPO: OPINIÓN. Postura CLARA desde el primer segundo (nada de 'depende'). Evidencia real de su "
        "experiencia → reconocer lo que pierde su favorito. El CTA es el remate de la postura."
    ),
    "tech": (
        "TIPO: TECNOLOGÍA. Isaac es ingeniero/ciberseguridad: enseña algo de tech útil (usar Claude/IA, "
        "una app, un truco, seguridad básica) con autoridad real y sin tecnicismos. Si puedes, mete el puente con "
        "los carros (p.ej. lo enseña mientras el Tesla maneja con FSD). Termina con un remate seco."
    ),
    "fsd": (
        "TIPO: FSD + LISTICLE/STORYTELLING. El Tesla (Caldermóvil) maneja solo con FSD mientras Isaac "
        "cuenta algo en formato lista (5 datos, 5 rolas, 5 marcas, etc.) o una historia. Muestra que el carro maneja "
        "solo al inicio. Recuerda: FSD es supervisado (manos cerca del volante, solo lo enseña un momento)."
    ),
    "evergreen": (
        "TIPO: HOW-TO o OPINIÓN atemporal de carros/tech con datos reales."
    ),
}

# ─── BANCOS DE TEMAS ──────────────────────────────────────────────────────────
_HOWTO_TOPICS = [
    {"title": "Cuánto cuesta de verdad cargar un Tesla en CDMX", "context": "Costo real de cargar el Caldermóvil (Tesla de su papá) en cargadores de plaza vs lo que costaría de gasolina. Números reales."},
    {"title": "Cómo funciona el FSD y qué puede hacer en CDMX", "context": "Qué hace solo el FSD del Tesla de su papá, qué requiere que tomes el volante, en tráfico mexicano. Honesto sobre topes y baches."},
    {"title": "¿Un eléctrico necesita aceite? El mantenimiento real", "context": "Lista real de mantenimiento de un Tesla vs un carro de gasolina como el Swift: costos y frecuencia."},
    {"title": "¿Cuántos km da de verdad un Tesla en la ciudad?", "context": "Autonomía real del Caldermóvil en CDMX con y sin AC. El número de la app vs la realidad."},
    {"title": "Lo que de verdad cuesta tener un Swift Sport en México", "context": "Precio, gasolina, mantenimiento, refacciones del Swift de Isaac. Por qué es el más honesto de los 3."},
    {"title": "Qué pasa si se te acaba la batería de un eléctrico", "context": "El proceso real: qué hace el carro, cómo pides ayuda, cuánto cuesta. Sin drama."},
]

_LIFESTYLE_TOPICS = [
    {"title": "Un día de becario en vacaciones (spoiler: trabajo)", "context": "Home office desde las 8, café recalentado, gym a las 3 (a veces caminando, a veces en el Swift), proyecto en la noche. El chiste becario/precario."},
    {"title": "Por qué ando en mi Swift teniendo un Tesla en casa", "context": "El Tesla es de su papá (nave, relajado); el Swift es suyo y se siente vivo. Por qué a propósito prefiere el Swift en CDMX."},
    {"title": "Mi media hora de terapia: manejar al gym", "context": "El trayecto al gym en el Swift con su música es lo único del día donde nadie le escribe. Cambio físico, hábitos."},
    {"title": "Simulador vs realidad: manejar en Assetto Corsa y en CDMX", "context": "Isaac juega Assetto Corsa. Qué te prepara el simulador y qué NO (los topes, el tráfico real). Humor de ingeniero."},
    {"title": "El carro del día según mi mood", "context": "Swift para diario, y de vez en cuando el Caldermóvil (de papá) o el Mini (de mamá). La lógica real, con humor de que pide permiso."},
]

_OPINION_TOPICS = [
    {"title": "El Swift Sport es el carro más subestimado de México", "context": "Por qué el Swift de Isaac da más diversión por peso que carros que cuestan el triple. Evidencia de manejarlo a diario."},
    {"title": "¿Vale la pena un Tesla en México hoy?", "context": "Opinión honesta desde la experiencia con el Caldermóvil: cuándo sí brilla y cuándo el eléctrico frustra en CDMX."},
    {"title": "FSD en México: ¿promesa cumplida o marketing?", "context": "Opinión directa tras usar el FSD del Tesla de su papá en calles mexicanas: lo que sí y lo que no."},
    {"title": "El carro divertido y barato le gana al caro y aburrido", "context": "Swift vs Tesla: qué da más satisfacción real por tu dinero. Postura clara."},
]

_TECH_TOPICS = [
    {"title": "La app de IA que uso para todo (no es ChatGPT)", "context": "Cómo Isaac usa Claude para resumir documentos, estudiar y organizarse. Puente: lo cuenta mientras el Tesla maneja con FSD. Visión de ingeniero."},
    {"title": "3 trucos de ciberseguridad que todos deberían usar", "context": "Isaac es de ciberseguridad: contraseñas, 2FA, no picarle a links raros. Fácil, sin tecnicismos, con humor."},
    {"title": "Cómo uso la IA para no batallar en la chamba", "context": "Trucos reales de IA para productividad de un becario de tecnología. Útil y aterrizado."},
    {"title": "El FSD explicado como lo que es: tecnología, no magia", "context": "Isaac, como ingeniero, explica qué hace por dentro el FSD del Tesla (cámaras, IA) sin tecnicismos. El puente carro+tech."},
    {"title": "Apps que de verdad uso como estudiante de ingeniería", "context": "Stack real de apps de Isaac para estudiar/trabajar/organizarse. Honesto, nada patrocinado."},
]

_FSD_TOPICS = [
    {"title": "5 rolas de dolido para tu terapia en el carro", "context": "El Tesla maneja solo con FSD mientras Isaac da su playlist de canciones de dolido con un comentario chistoso de cada una. Deja las rolas como [tu rola] para que Isaac las ponga."},
    {"title": "Dejé que el Tesla me llevara a cualquier lado por un café", "context": "Isaac aburrido le pide a Grok/FSD que lo lleve por un café y mientras cuenta 5 datos curiosos de él. Formato storytelling + FSD."},
    {"title": "5 marcas de autos que te recomiendo (y por qué)", "context": "Mientras el Tesla maneja solo, Isaac da 5 marcas que recomienda con una razón corta y honesta de cada una."},
    {"title": "Las monerías del Tesla que nadie te muestra así", "context": "Mostrar features cool del Caldermóvil (modo centinela, sonidos, front, pantalla) de forma creativa y divertida, no como reseña aburrida."},
]


def _to_str(value) -> str:
    """Gemini a veces devuelve listas en vez de strings — las une."""
    if isinstance(value, list):
        return "\n\n".join(str(item) for item in value)
    return str(value) if value is not None else ""


def _to_list(value) -> list:
    """Normaliza a lista de strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _parse_response(response, script_type: str) -> Script:
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
        title=_to_str(data["title"]),
        topic_context=_to_str(data["topic_context"]),
        hook=_to_str(data["hook"]),
        body=_to_str(data["body"]),
        cta=_to_str(data["cta"]),
        spot=_to_str(data.get("spot", "")),
        como_grabar=_to_str(data.get("como_grabar", "")),
        puntos=_to_list(data.get("puntos", [])),
        arranque=_to_str(data.get("arranque", "")),
        hashtags_tiktok=_to_list(data.get("hashtags_tiktok", [])),
        hashtags_reels=_to_list(data.get("hashtags_reels", [])),
        hashtags_shorts=_to_list(data.get("hashtags_shorts", [])),
        script_type=data.get("script_type", script_type),
    )


_file_cache = {}


def _load_file(path: str) -> str:
    """Lee un archivo de estilo, cacheado por ruta (no cambia durante una corrida)."""
    if path not in _file_cache:
        try:
            with open(path, "r", encoding="utf-8") as f:
                _file_cache[path] = f.read()
        except FileNotFoundError:
            _file_cache[path] = ""
    return _file_cache[path]


def _load_voice_guide() -> str:
    return _load_file(VOICE_GUIDE_PATH)


def _load_contexto_actual() -> str:
    return _load_file(CONTEXTO_ACTUAL_PATH)


_IMPACT_EXPRESSIONS = ["nambre", "no manches", "o sea", "la neta", "te lo chismeo", "wey", "básicamente"]


def build_canal_context(recent_titles: list[str], approved_examples: list[dict]) -> str:
    """Arma el bloque de contexto del canal: temas recientes (para no repetir),
    expresiones ya usadas (para variar) y guiones aprobados (para imitar estilo)."""
    parts = []
    if recent_titles:
        titles_text = "\n".join(f"- {t}" for t in recent_titles)
        parts.append(
            "TEMAS RECIENTES EN EL CANAL — NO repitas exactamente estos temas. "
            "Si el tema es similar, busca un ángulo completamente distinto:\n" + titles_text
        )

    recent_hooks = [ex.get("hook", "").lower() for ex in approved_examples if ex.get("hook")]
    used_expressions = [e for e in _IMPACT_EXPRESSIONS if any(e in h for h in recent_hooks)]
    if used_expressions:
        parts.append(
            "EXPRESIONES YA USADAS EN GUIONES RECIENTES — usa una DIFERENTE esta vez:\n"
            + ", ".join(f'"{e}"' for e in used_expressions)
        )

    if approved_examples:
        lines = []
        for ex in approved_examples:
            line = f'- "{ex["title"]}" ({ex["type"]})'
            if ex.get("hook"):
                line += f' — Hook aprobado por Isaac: "{ex["hook"]}"'
            lines.append(line)
        parts.append(
            "GUIONES QUE ISAAC APROBÓ — estudia su estilo de título y gancho para replicarlo:\n"
            + "\n".join(lines)
        )
    if not parts:
        return ""
    return "\n\n".join(parts)


def _build_prompt(script_type: str, title: str, context: str, canal_context: str) -> str:
    voice_guide = _load_voice_guide()
    contexto_actual = _load_contexto_actual()
    guidance = _TYPE_GUIDANCE.get(script_type, _TYPE_GUIDANCE["trend"])

    sections = [
        voice_guide,
        "---",
        guidance,
        f"TEMA SEMILLA: {title}\nCONTEXTO DEL TEMA: {context}",
    ]
    if contexto_actual:
        sections.append("---\nCONTEXTO ACTUAL DE ISAAC (adapta el tema a esto):\n" + contexto_actual)
    if canal_context:
        sections.append("---\nCONTEXTO DEL CANAL:\n" + canal_context)
    sections.append(_COMMON.format(script_type=script_type))
    return "\n\n".join(sections)


def generate(article: Article, script_type: str = "trend", canal_context: str = "") -> Script:
    prompt = _build_prompt(script_type, article.title, article.summary, canal_context)
    # Grounding (búsqueda en Google) solo para noticias/tendencias y tech, que
    # se benefician de datos actuales. Los demás usan temas del banco.
    config = gemini_client.SEARCH_CONFIG if script_type in ("trend", "tech", "evergreen") else None
    # Guiones = tarea creativa → modelo PRO (más inteligente para humor y tono).
    response = gemini_client.call(prompt, config=config, model=gemini_client.MODEL_PRO)
    return _parse_response(response, script_type)


def _generate_from_bank(bank: list, script_type: str, canal_context: str) -> Script:
    topic = random.choice(bank)
    article = Article(
        title=topic["title"],
        url="",
        summary=topic["context"],
        source=script_type,
        published=datetime.now(timezone.utc),
    )
    return generate(article, script_type=script_type, canal_context=canal_context)


def generate_howto(canal_context: str = "") -> Script:
    return _generate_from_bank(_HOWTO_TOPICS, "howto", canal_context)


def generate_lifestyle(canal_context: str = "") -> Script:
    return _generate_from_bank(_LIFESTYLE_TOPICS, "lifestyle", canal_context)


def generate_opinion(canal_context: str = "") -> Script:
    return _generate_from_bank(_OPINION_TOPICS, "opinion", canal_context)


def generate_tech(canal_context: str = "") -> Script:
    return _generate_from_bank(_TECH_TOPICS, "tech", canal_context)


def generate_fsd(canal_context: str = "") -> Script:
    return _generate_from_bank(_FSD_TOPICS, "fsd", canal_context)


def generate_evergreen(canal_context: str = "") -> Script:
    """Legacy: alterna entre howto y opinion."""
    if random.random() < 0.5:
        return generate_howto(canal_context=canal_context)
    return generate_opinion(canal_context=canal_context)
