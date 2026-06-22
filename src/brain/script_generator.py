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
FORMATO: Reel vertical de 60 a 100 segundos. El campo "body" es el guión natural
(lo que Isaac diría platicando, no un ensayo) y debe tener entre 200 y 320 palabras —
suficiente material para que Isaac corte y adapte lo que quiera. Si tiene menos de 180
palabras, está incompleto: desarrolla más el tema, agrega otro ejemplo, dato o remate.
No lo rellenes con paja: cada oración debe enseñar algo o dar risa.

REGLA DE ORO: el video tiene que ENSEÑAR algo útil Y dar risa. Si no cumple ambas, reescríbelo.

CREATIVIDAD (lo más importante — los guiones aburridos se rechazan):
El TEMA SEMILLA es solo un punto de partida. Tu trabajo es encontrar el ángulo MÁS CREATIVO e
inesperado, NO el obvio de reseñero. Un creador aburrido hace la pregunta predecible; tú haces algo
que pare el scroll. Compara:
- ❌ ABURRIDO: "¿Qué pasa si se te acaba la batería del Tesla?" → ✅ CREATIVO: "Le pedí a la IA del Tesla que me dijera la neta de los eléctricos y se puso conspiranoica."
- ❌ ABURRIDO: "¿Vale la pena un Tesla en México?" → ✅ CREATIVO: "Probé si el FSD del Tesla sobrevive a los topes de mi colonia."
- ❌ ABURRIDO: "El Swift es subestimado" → ✅ CREATIVO: "Reté a mi Swift contra el Tesla en lo único donde el Tesla no puede ganar."
Formatos que SÍ jalan (inspirados en creadores reales): el experimento/reto, la prueba en vivo con el
resultado revelado, "le pregunté a la IA", el dato escondido que nadie muestra, el POV/situación
("POV: eres becario y el único carro libre es el Tesla de tu papá"), el ranking con giro inesperado.

ANTI-COPIA Y ANTI-REPETICIÓN (crítico):
- Los guiones de referencia del voice guide son SOLO para captar el TONO y el RITMO. PROHIBIDO reusar
  su tema, su gancho o sus frases. Si tu guión se parece a uno de ellos, recházalo y haz otro distinto.
- PROHIBIDO empezar con clichés ya usados: "En mi casa hay un Tesla...", "Nambre...", "La pregunta del millón...".
  VARÍA la apertura cada vez (una afirmación tajante, una pregunta filosa, una acción ya empezada, un dato brutal).
- "nambre" está PROHIBIDO como muletilla (ya se sobreusó). Si necesitas una expresión, usa otra y una sola vez.

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

VOCABULARIO: solo español mexicano de CDMX (no manches, o sea, la neta, te explico, te lo chismeo, wey, a ver). EVITA "nambre" (sobreusado). NUNCA candela/chévere/bacán.

Responde SOLO con JSON válido (sin markdown, sin ```):
{{
  "title": "título corto para Notion (máx 60 caracteres)",
  "topic_context": "qué enseña y por qué importa ahora, 1-2 oraciones",
  "hook": "los primeros 2 segundos, máximo 12 palabras, que pare el scroll",
  "body": "guión natural completo, 200-320 palabras, con varios momentos de risa y algo que enseñe; material de sobra para recortar",
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
# Los temas son SEMILLAS con ángulo creativo. El prompt obliga a llevarlos aún
# más lejos. Cada uno tiene un FORMATO (experimento, reto, POV, reveal, "le pregunté a la IA").
_HOWTO_TOPICS = [
    {"title": "Le pedí a la IA del Tesla que me dijera la neta de los eléctricos", "context": "REVELACIÓN: Isaac le pregunta a Grok (la IA dentro del Caldermóvil) las dudas reales de un eléctrico en México (carga, costo, autonomía) y traduce las respuestas con humor. Enseña datos reales en formato divertido."},
    {"title": "Probé si el FSD sobrevive a los topes de mi colonia", "context": "EXPERIMENTO: Isaac pone el FSD del Tesla de su papá y muestra honestamente qué hace bien y dónde sufre con los topes/baches mexicanos. Enseña cómo funciona el FSD de verdad."},
    {"title": "Cuánto me cuesta el Swift al mes vs lo que cree la gente", "context": "REVEAL con número: Isaac calcula en vivo el costo real mensual de su Swift (gasolina, mantenimiento) y lo compara con lo que la gente asume. Revela el número al inicio."},
    {"title": "El truco para cargar un Tesla casi sin que lo sientas en la cartera", "context": "HOW-TO con dato: cómo y dónde carga su papá el Caldermóvil en plazas, cuánto cuesta de verdad vs gasolina. Práctico y con el chiste de hacer el súper por el cargador."},
    {"title": "Hice que el Tesla planeara un viaje y esto me dijo", "context": "DEMO en vivo: Isaac le pide al Tesla una ruta larga (con paradas de carga) y muestra cómo lo calcula. Enseña que la ansiedad de autonomía es un mito, con humor."},
]

_LIFESTYLE_TOPICS = [
    {"title": "POV: eres becario y el único carro libre es el de tu papá", "context": "POV/situación: el dilema de agarrar el Caldermóvil (Tesla de papá) vs su Swift. Humor becario/precario, pedir permiso, la presión de no rayarlo."},
    {"title": "Mi rutina de becario en vacaciones que nadie pidió ver", "context": "Día real con autoburla: home office desde las 8 en pijama, café recalentado 3 veces, gym a las 3 (a veces caminando), proyecto de ciber en la noche. El chiste becario/precario."},
    {"title": "Manejar al gym es mi terapia más barata", "context": "Pedazo honesto: el trayecto al gym con su música es lo único del día sin notificaciones. Conecta cambio físico + carro + salud mental, con humor."},
    {"title": "Lo que Assetto Corsa NO te prepara para manejar en CDMX", "context": "Comparación con giro: Isaac juega el simulador y muestra qué sí y qué definitivamente NO te prepara (topes, microbuses, el tío en sentido contrario). Humor de ingeniero gamer."},
    {"title": "Ranking de los 3 carros de mi familia según para qué sirven", "context": "Ranking con giro: Swift (suyo), Caldermóvil (de papá), Mini (de mamá), cada uno gana en una categoría inesperada. Honesto y divertido, sin decir 'mi Tesla'."},
]

_OPINION_TOPICS = [
    {"title": "El carro más caro de mi casa no es el que quiero manejar", "context": "POSTURA con gancho: por qué prefiere su Swift al Caldermóvil de su papá. Diversión vs comodidad. Postura clara desde el inicio, evidencia real, sin copiar fórmulas previas."},
    {"title": "La verdad incómoda del FSD que los fans no quieren oír", "context": "OPINIÓN filosa: Isaac, como ingeniero, da su postura honesta sobre el FSD en México: dónde es genial y dónde es marketing. Con datos de uso real."},
    {"title": "Comprar un deportivo barato es más inteligente que un eléctrico caro", "context": "TESIS provocadora: argumento de por qué un Swift Sport da más satisfacción por peso/precio que gastar el triple. Postura tajante con concesión honesta."},
    {"title": "Manejar un eléctrico te cambia algo que nadie te dice", "context": "OPINIÓN inesperada: el cambio mental real de manejar el Caldermóvil (silencio, no gasolineras, planear) — lo bueno y lo que extrañas de un carro 'normal'."},
]

_TECH_TOPICS = [
    {"title": "Uso esta IA en el carro y me hace ver más listo de lo que soy", "context": "DEMO + puente: cómo Isaac usa Claude (resumir, estudiar, organizarse) mientras el Tesla maneja con FSD. Autoburla + enseña algo útil de IA. Remate seco."},
    {"title": "3 cosas de ciberseguridad que haces mal sin saber", "context": "REVEAL útil: Isaac (de ciber) expone 3 errores comunes (contraseñas, 2FA, links) con ejemplos y humor, sin tecnicismos. Enseña algo que la gente sí puede aplicar hoy."},
    {"title": "Le pregunté a la IA cuál de los 3 carros de mi familia es mejor", "context": "EXPERIMENTO tech+carro: Isaac le da los datos de los 3 carros a una IA y muestra su veredicto vs su propia opinión de ingeniero. Divertido y revelador."},
    {"title": "El FSD no es magia, es esto (te lo explica un ingeniero)", "context": "EXPLICA simple: qué hace por dentro el FSD (cámaras + IA) en lenguaje de banqueta, mientras lo usa. El puente carro+tech, autoridad real sin presumir."},
    {"title": "Hackeé mi rutina con IA: chamba + gym + proyecto sin morir", "context": "HOW-TO de productividad: cómo Isaac usa IA para organizar su día de becario/estudiante/emprendedor. Concreto, aplicable, con el toque de que parece de hacker pero es legal."},
]

_FSD_TOPICS = [
    {"title": "5 rolas de dolido para tu media hora de terapia en el carro", "context": "FSD + listicle: el Tesla maneja solo mientras Isaac da su playlist de dolido con un comentario chistoso de cada una. Deja las rolas como [tu rola] para que Isaac las ponga."},
    {"title": "Dejé que el Tesla me llevara a cualquier lado por un café", "context": "FSD + storytelling: Isaac aburrido le pide a Grok/FSD que lo lleve por un café y mientras cuenta 5 datos curiosos de él. Muestra que el carro maneja solo."},
    {"title": "Califiqué a los conductores de CDMX mientras el Tesla manejaba solo", "context": "FSD + bit: con las manos libres (supervisado), Isaac narra y califica con humor las maniobras locas del tráfico de CDMX que el FSD tiene que esquivar."},
    {"title": "Las monerías del Tesla que nadie te muestra así", "context": "Reveal creativo: features cool del Caldermóvil (modo centinela, bocina, front, juegos) mostrados de forma divertida y rápida, no como reseña aburrida."},
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


def append_avoid_hooks(canal_context: str, used_hooks: list) -> str:
    """Agrega al contexto los ganchos ya usados en la misma corrida, para que
    los 3 guiones del día no arranquen igual ni repitan el mismo chiste."""
    used = [h for h in (used_hooks or []) if h]
    if not used:
        return canal_context
    block = (
        "GANCHOS YA GENERADOS HOY — usa una apertura y un ángulo COMPLETAMENTE distintos, "
        "no arranques parecido a estos:\n" + "\n".join(f'- "{h}"' for h in used)
    )
    return f"{canal_context}\n\n{block}" if canal_context else block


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
