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

# ─── TREND PROMPT ────────────────────────────────────────────────────────────
# Para noticias y tecnología automotriz actual. Guión completo con teleprompter.
_TREND_PROMPT = """{voice_guide}

---

Genera un guión de NOTICIAS/TENDENCIAS para Los Calderas. Video de 60-90 segundos.

TEMA: {title}
CONTEXTO (verifica con búsqueda si puedes complementar con datos más recientes): {context}

## INSTRUCCIONES

GANCHO — elige UNA opción:
Opción A (texto visual, 5-10 palabras): aparece en pantalla antes de que el creador hable
  ✅ "¿Un Tesla mexicano?" | "El gobierno ya tiene su carro eléctrico" | "50 km/h. Es todo."
Opción B (frase hablada, ya estás en la situación):
  ✅ "Nambre... acabo de ver el carro que el gobierno quiere que manejemos."
  ❌ "Hoy les voy a hablar de..." — PROHIBIDO
  ❌ "¿Sabías que...?" — PROHIBIDO

CUERPO:
- Datos concretos y verificables: velocidad, precio, autonomía, fechas, cifras
- Traduce técnico a cotidiano: no "carece de sistemas de seguridad pasiva" sino "no tiene bolsas de aire"
- Humor específico y anclado en algo real mexicano (✅ "aprobado por SHEINbaum", referencias a Periférico, Oxxo, Uber Eats, el SAT, el IMSS, cibercafé de la secundaria; ❌ referencias inventadas o genéricas)
- Si la noticia es EV en México: puedes mencionar el Tesla del creador como contraste real y breve. Una sola referencia, no un párrafo.
- Para cualquier otro tema: menciona sus carros SOLO si la noticia los involucra directamente.

VOCABULARIO — SOLO español mexicano de CDMX:
✅ "nambre", "no manches", "o sea", "básicamente", "espérense", "la verdad es que", "wey"
❌ "candela" — NO es mexicano, es venezolano/caribeño. NUNCA en este canal.
❌ "chévere", "bacán", "parcero" — tampoco son mexicanos. Si tienes duda, no lo uses.

ANTI-PATRONES — estos arruinan el guión, evítalos siempre:
❌ NO repitas la misma expresión de impacto más de una vez. Si ya salió "nambre", ya no la uses de nuevo.
❌ NO hagas comparaciones con los carros del creador cuando hay algo más absurdo disponible. "En Periférico me rebasa una bici de Uber Eats" > "mi Mini JCW vs esto". El contraste más ridículo y específico gana.
❌ NO fuerces los 3 carros del creador en el mismo párrafo. Si el tema no es una comparativa entre ellos, no aparecen todos juntos.
❌ NO escribas el CTA como párrafo nuevo desconectado. Es el REMATE del chiste central del video.

CTA — es el remate del chiste que ya hiciste en el cuerpo:
El CTA tiene que hacer callback a algo específico que ya ocurrió en el guión.
  ✅ Si el video hizo chiste con "SHEINbaum" → el CTA lo cierra: "Mándale esto a tu familiar que se queja de los eléctricos pero bien que ya va a apoyar a Sheinbaum con su Olinia"
  ✅ Si el video mencionó que va a 50 km/h → CTA: "Guarda esto para cuando tu familiar llegue tarde en su Olinia porque fue a 50 en Periférico"
  ❌ "Mándale esto a tu familiar que jura que todos los eléctricos son como el Tesla" — demasiado genérico, no conecta con nada del video

CONSEJOS DE GRABACIÓN: 2-3 tips muy concretos para ESTE video específico
  ✅ "Empieza con texto 'El gobierno ya tiene su carro' en negro sobre blanco, 1.5 seg, luego corte a cara de duda"
  ❌ "Grábate hablando frente a la cámara" — demasiado genérico

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "title": "título corto para Notion (máx 60 caracteres)",
  "topic_context": "por qué es relevante ahora, 1-2 oraciones con dato específico",
  "hook": "el gancho exacto — texto visual O frase hablada, máximo 12 palabras",
  "body": "guión completo del cuerpo (40-75 segundos hablados), con datos reales y humor específico",
  "cta": "cierre que genere saves o que alguien mande a alguien específico",
  "visual_idea": "setup visual concreto que detenga el scroll antes de hablar",
  "filming_tips": ["tip 1 concreto para este video", "tip 2", "tip 3 opcional"],
  "hashtags_tiktok": ["hasta 5 hashtags"],
  "hashtags_reels": ["hasta 5 hashtags"],
  "hashtags_shorts": ["hasta 5 hashtags"],
  "script_type": "trend"
}}
Solo JSON, sin nada más.
"""

# ─── HOWTO PROMPT ─────────────────────────────────────────────────────────────
# Para guías prácticas con datos reales: costos, procesos, comparativas técnicas.
_HOWTO_PROMPT = """{voice_guide}

---

Genera un guión tipo HOW-TO / DATOS REALES para Los Calderas. Video de 60-90 segundos.

TEMA: {title}
CONTEXTO: {context}

Este tipo de video es el más útil para el espectador: resuelve una duda real con datos concretos.
El creador es estudiante de ingeniería en el Tec de Monterrey que tiene Tesla, Mini JCW y Swift Sport.

## INSTRUCCIONES

GANCHO — que revele un dato sorprendente o una pregunta que YA tienen:
  ✅ "Cuánto cuesta cargar el Tesla: el número real" (texto visual)
  ✅ "Oigan... acabo de calcular cuánto me cuesta el Tesla vs gasolina al mes." (hablado)
  ✅ Revelar el número o resultado al inicio, NO al final (anti-suspense)
  ❌ "Hoy les voy a explicar cómo..." — PROHIBIDO

CUERPO:
- Estructura: número o dato revelador → cómo funciona (simple, sin jerga) → qué significa para alguien como tú
- Cifras exactas o rangos reales: "$X al mes", "X km por carga", "X minutos para cargar al 80%"
- Si mencionas el Tesla/Mini/Swift, que sea con dato personal real ("yo pago X al mes en carga")
- Comparaciones cotidianas: "es lo mismo que llenar el Mini dos veces" o "menos que tu Spotify premium"

VOCABULARIO — SOLO español mexicano de CDMX:
✅ "nambre", "no manches", "o sea", "wey", "básicamente", "espérense"
❌ "candela", "chévere", "bacán" — no son mexicanos, no los uses nunca.

ANTI-PATRONES:
❌ NO repitas la misma expresión de impacto más de una vez en el mismo guión.
❌ El CTA no es un párrafo nuevo — es el remate del dato más sorprendente que acabas de dar.

CTA — callback al dato más impactante del video:
  ✅ Si dijiste que cuesta menos que Netflix → CTA: "Guarda esto para cuando te pregunten si los eléctricos son caros... mientras pagas tu Netflix sin chistar"
  ✅ Si dijiste X minutos de carga → CTA: "Mándale esto a tu familiar que dice que cargar es tardadísimo"
  ❌ CTAs genéricos desconectados del dato central — PROHIBIDO

CONSEJOS DE GRABACIÓN: 2-3 tips para hacer este video visual aunque sea informativo
  ✅ "Muestra la pantalla del carro o la app de carga mientras das el dato, no hables solo a la cámara"
  ✅ "Para el dato de pesos, saca la calculadora en pantalla y haz el cálculo en vivo"

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "title": "título corto para Notion (máx 60 caracteres)",
  "topic_context": "qué dato específico resuelve este video y por qué importa ahora",
  "hook": "el gancho exacto — revela el dato de entrada, máximo 12 palabras",
  "body": "guión completo (40-75 segundos), paso a paso pero casual, con cifras exactas",
  "cta": "cierre que genere saves porque es info útil",
  "visual_idea": "qué mostrar en pantalla mientras hablas (app, pantalla del carro, calculadora, etc.)",
  "filming_tips": ["tip 1 concreto para hacer visual el dato", "tip 2", "tip 3 opcional"],
  "hashtags_tiktok": ["hasta 5 hashtags"],
  "hashtags_reels": ["hasta 5 hashtags"],
  "hashtags_shorts": ["hasta 5 hashtags"],
  "script_type": "howto"
}}
Solo JSON, sin nada más.
"""

# ─── LIFESTYLE PROMPT ─────────────────────────────────────────────────────────
# Para contenido de día a día. NO es teleprompter — es un plan de escenas para improvisar.
_LIFESTYLE_PROMPT = """{voice_guide}

---

Genera una IDEA DE CONTENIDO LIFESTYLE para Los Calderas. Video de 30-90 segundos.

TEMA: {title}
CONTEXTO: {context}

El creador es estudiante de ingeniería en el Tec de Monterrey (CDMX), tiene Tesla/Mini/Swift.
Este tipo de video NO se lee desde teleprompter — el creador improvisa en cámara.
Tu trabajo es darle un PLAN DE ESCENAS claro y concreto para que sepa qué filmar.

## INSTRUCCIONES

GANCHO — algo visual que detenga el scroll antes de que hable:
  ✅ Una imagen inesperada o contraste visual (Tesla en estacionamiento del Tec junto a un Tsuru)
  ✅ Texto en pantalla que crea curiosidad inmediata ("¿Cuántos ingenieros del Tec tienen Tesla?")
  ❌ El creador hablando de frente a la cámara desde el inicio — demasiado genérico

PLAN DE ESCENAS (esto va en el campo "body"):
- Escribe 3-5 escenas concretas con: [qué filma] + [qué dice o hace] + [duración aproximada]
- Ejemplo:
  "ESCENA 1 (5 seg): Llega al estacionamiento del Tec, plano del Tesla entre otros carros. Sin hablar.
   ESCENA 2 (10 seg): Cara a cámara: 'Spoiler: soy el único con Tesla en mi semestre. Más o menos.'
   ESCENA 3 (20 seg): Muestra el interior del carro, explica qué usa mientras espera entre clases."
- El creador improvisa el diálogo — dale los puntos clave, no el guión exacto

CTA: algo casual que invite a seguir o compartir
  ✅ "Mándale esto a alguien que esté pensando en un eléctrico para ir a la uni"
  ✅ Terminar con algo que deja al espectador queriendo ver más (una pregunta genuina o un cliffhanger)
  ❌ "Comenta SÍ o NO" — PROHIBIDO

CONSEJOS DE GRABACIÓN: 2-3 tips para que se vea natural, no producido
  ✅ "Graba en vertical, modo foto + video alternado, nada de tripié visible"
  ✅ "El primer clip tiene que ser interesante sin audio — piensa en el feed con el sonido apagado"

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "title": "título corto para Notion (máx 60 caracteres)",
  "topic_context": "por qué este tema conecta con la audiencia ahora mismo",
  "hook": "el gancho visual o frase de apertura, máximo 12 palabras",
  "body": "PLAN DE ESCENAS: 3-5 escenas con qué filmar, qué decir/hacer y duración aproximada",
  "cta": "cómo terminar el video o qué caption usar",
  "visual_idea": "el primer frame o imagen que detiene el scroll — sé muy específico",
  "filming_tips": ["tip 1 para que se vea natural", "tip 2", "tip 3 opcional"],
  "hashtags_tiktok": ["hasta 5 hashtags"],
  "hashtags_reels": ["hasta 5 hashtags"],
  "hashtags_shorts": ["hasta 5 hashtags"],
  "script_type": "lifestyle"
}}
Solo JSON, sin nada más.
"""

# ─── OPINION PROMPT ───────────────────────────────────────────────────────────
# Para takes fuertes, comparativas y debates. Opinión clara del creador.
_OPINION_PROMPT = """{voice_guide}

---

Genera un guión de OPINIÓN / COMPARATIVA para Los Calderas. Video de 60-90 segundos.

TEMA: {title}
CONTEXTO: {context}

El creador tiene experiencia real con Tesla Model Y LR 2026, Mini Countryman JCW 2021 y Swift Sport 2021.
Este tipo de video requiere una POSTURA CLARA. No hay "depende" como respuesta — hay una opinión.

## INSTRUCCIONES

GANCHO — revela la postura desde el inicio, no construyas suspenso:
  ✅ "El Swift Sport gana. Y no está ni cerca." (texto visual directo)
  ✅ "Nambre... yo creía que el Mini era el más divertido. Estaba mal." (hablado, ya pasó)
  ❌ "Hoy vamos a comparar estos tres carros..." — PROHIBIDO
  ❌ "¿Cuál será el ganador?" — no generes suspense artificial

CUERPO:
- Opinión personal con evidencia real: "lo manejé X meses y esto es lo que descubrí"
- Estructura: postura clara → 2-3 razones con experiencia personal → reconocer lo que pierde el favorito
- Si es comparativa entre los 3 autos: usa los 3. Si es opinión sobre un solo auto: enfócate en ese.
- Sin falsa modestia: si el Mini es el mejor para manejar, dilo directo y explica por qué

VOCABULARIO — SOLO español mexicano de CDMX:
✅ "nambre", "no manches", "o sea", "wey", "básicamente", "espérense"
❌ "candela", "chévere", "bacán" — no son mexicanos, no los uses nunca.

ANTI-PATRONES:
❌ NO repitas la misma expresión de impacto más de una vez. "Nambre" una vez, no tres.
❌ NO uses los carros del creador como comparación cuando la comparación más ridícula sería con algo externo.
❌ El CTA no es un párrafo nuevo — es el remate de la postura que acabas de defender.

CTA — el remate de tu argumento, dirigido a alguien específico que no estaría de acuerdo:
  ✅ "Mándale esto a tu cuate que dice que los deportivos pequeños no sirven en México"
  ✅ "Guarda esto para cuando alguien te diga que tener un eléctrico en México es un error"
  ❌ "¿Tú con cuál te quedarías?" — PROHIBIDO
  ❌ CTAs que no conectan con ningún argumento del video — PROHIBIDO

CONSEJOS DE GRABACIÓN: 2-3 tips para que la opinión se vea auténtica y no producida
  ✅ "Di la postura mientras manejas uno de los carros, no parado mirando a la cámara"
  ✅ "Muestra el odómetro o una situación real que demuestre el uso real, no solo hables"

Responde SOLO con JSON (sin markdown, sin ```):
{{
  "title": "título corto para Notion (máx 60 caracteres)",
  "topic_context": "por qué este tema genera debate y por qué tu experiencia es relevante",
  "hook": "el gancho — revela la postura desde el primer segundo, máximo 12 palabras",
  "body": "guión completo (40-75 segundos): postura → evidencia personal → concesión honesta",
  "cta": "cierre que alguien mande a quien no estaría de acuerdo",
  "visual_idea": "setup visual que refuerce la opinión desde el primer frame",
  "filming_tips": ["tip 1 para que la opinión se vea auténtica", "tip 2", "tip 3 opcional"],
  "hashtags_tiktok": ["hasta 5 hashtags"],
  "hashtags_reels": ["hasta 5 hashtags"],
  "hashtags_shorts": ["hasta 5 hashtags"],
  "script_type": "opinion"
}}
Solo JSON, sin nada más.
"""

_PROMPT_BY_TYPE = {
    "trend": _TREND_PROMPT,
    "howto": _HOWTO_PROMPT,
    "lifestyle": _LIFESTYLE_PROMPT,
    "opinion": _OPINION_PROMPT,
    "evergreen": _TREND_PROMPT,  # fallback legacy
}

# ─── TOPIC BANKS ──────────────────────────────────────────────────────────────

_HOWTO_TOPICS = [
    {"title": "Cuánto cuesta cargar el Tesla en CDMX — el número real", "context": "Costo real por km en casa, SuperCharger y cargadores públicos. Comparación con gasolina."},
    {"title": "Cómo funciona el FSD y qué puede hacer en CDMX", "context": "Demo real: qué hace solo el FSD, qué requiere intervención, en condiciones de tráfico mexicano."},
    {"title": "¿El Tesla necesita aceite? Todo el mantenimiento real", "context": "Lista real de mantenimiento de un Tesla vs carro de gasolina: costos y frecuencia."},
    {"title": "¿Cuántos km da el Tesla Model Y LR en la ciudad?", "context": "Autonomía real en CDMX con AC, sin AC, en carretera. El número de la app vs. la realidad."},
    {"title": "Cuánto tarda en cargar el Tesla al 80% — en casa y en SuperCharger", "context": "Tiempos reales de carga en distintos escenarios, qué conviene según el uso."},
    {"title": "El seguro del Tesla: cuánto pago y qué cubre realmente", "context": "Comparativa de precio de seguro eléctrico vs convencional en México, coberturas reales."},
    {"title": "Viaje CDMX–Guadalajara en Tesla: cómo se planea la ruta", "context": "Planificación de SuperChargers, tiempos de parada, costo total vs avión y gasolina."},
    {"title": "¿Vale la pena el Mini JCW en México con el precio actual?", "context": "Precio, mantenimiento, refacciones, consumo — análisis honesto de costo total de posesión."},
    {"title": "Qué pasa si se te acaba la batería del Tesla en CDMX", "context": "El proceso real: qué hace el carro, cómo pedir ayuda, costo de asistencia."},
    {"title": "Swift Sport vs cualquier hatchback similar: tabla de costos reales", "context": "Precio, rendimiento, mantenimiento del Swift Sport vs Golf GTI vs Mazda 3 Turbo en México."},
]

_LIFESTYLE_TOPICS = [
    # Vida en el Tec
    {"title": "Llegando al Tec en Tesla — las reacciones de mis compañeros de ITC", "context": "Isaac estudia ITC en el Tec CEM. La reacción de compañeros de ingeniería cuando llega en Tesla, las preguntas técnicas que le hacen, lo que esperan vs la realidad."},
    {"title": "El Tesla como oficina entre clases — así estudio en el Tec", "context": "Usar el Tesla como espacio para estudiar, trabajar en CipherPath o llamadas de Nestlé entre clases. La pantalla, el silencio, el AC — por qué funciona mejor que la biblioteca."},
    {"title": "El estacionamiento del Tec CEM: una radiografía de la generación", "context": "Los carros de los compañeros de ingeniería — desde Tsurus hasta Mazda 3s. Lo que dice de la generación y el contraste con el Tesla del creador."},
    {"title": "Mi último semestre antes del Semestre Tec — cómo lo viví", "context": "Terminando el 6° semestre de ITC. Proyectos finales, CipherPath, las prácticas en Nestlé, y manejar los 3 carros según el mood del día."},
    # Nestlé + carros
    {"title": "Cómo llego al trabajo en Nestlé — y por qué cambié de carro", "context": "Isaac trabaja en innovación IT en Nestlé. La decisión de qué carro llevar al trabajo: Tesla para comodidad, Mini para viernes, Swift para tráfico corto. La lógica real."},
    {"title": "Un día de trabajo en Nestlé Innovation IT — con Tesla incluido", "context": "Rutina real: saliendo al trabajo, el estacionamiento de Nestlé, qué hace en Innovation IT, y el regreso. El Tesla como parte de la rutina laboral de alguien de 20 años."},
    # Proyectos personales
    {"title": "CipherPath: construyendo una startup desde el carro", "context": "Isaac co-funda CipherPath (plataforma de ciberseguridad estilo Duolingo) con ArgISec. Trabaja en ello en el Tesla entre reuniones. La vida de un emprendedor de 20 años con 3 carros."},
    {"title": "Ser becario en Nestlé y estudiar ingeniería al mismo tiempo", "context": "Balancear Tec CEM + Nestlé Innovation IT + CipherPath + entrenar + los 3 carros. Cómo organiza el tiempo, qué carro usa para qué."},
    # HyRox + fitness
    {"title": "Domingo de HyRox — del entrenamiento al carro", "context": "Isaac tiene clases de HyRox cada domingo. El contraste entre el entrenamiento extremo y meterse al Tesla o Mini JCW de regreso. Qué carro lleva al gym y por qué."},
    {"title": "Mi cambio físico desde abril — y cómo los carros cambiaron con eso", "context": "Empezó un cambio físico el 27 de abril de 2026: gym, HyRox, hábitos. La rutina de manejar cambió — más energía, diferentes horarios, escuchar podcasts de fitness en el Tesla."},
    # Videojuegos + carros
    {"title": "Assetto Corsa vs la realidad — manejé el Mini en el juego y en CDMX", "context": "Isaac juega Assetto Corsa (simulador de autos). Comparar la experiencia de manejar el Mini JCW virtual vs real en CDMX: los topes, el tráfico, los sonidos. Lo que el simulador no te prepara."},
    {"title": "Mis carros en BeamNG — qué tan reales son los daños vs la vida real", "context": "Isaac juega BeamNG Drive (simulador de choques). Comparativa humorística y técnica entre cómo responde el Tesla/Mini/Swift en el juego vs lo que sabe de ingeniería real."},
    # Amigos y social
    {"title": "Grabé los carros de mis cuates del Tec — el resultado honesto", "context": "Comparativa informal de los carros de amigos de ingeniería. Los carros de la generación vs el Tesla del creador — sin juicio pero con honestidad."},
    {"title": "¿Cuál de mis 3 carros llevo a una primera cita?", "context": "Análisis con puntos reales: qué transmite el Tesla (tecnológico, caro), el Mini JCW (apasionado, impráctica), el Swift Sport (honesto, divertido). Sin respuesta correcta, con honestidad."},
    # Vida cotidiana
    {"title": "Mi rutina de carga semanal — cuándo y dónde cargo el Tesla en CDMX", "context": "Rutina real: carga en casa, SuperCharger, cuándo lo hace entre Tec y Nestlé. Apps que usa, tiempo que espera, cómo aprovecha la carga."},
    {"title": "El carro de entre semana vs el carro del finde — mi lógica real", "context": "Por qué usa el Tesla de lunes a viernes y el Mini o Swift los fines de semana. La lógica real detrás de tener 3 opciones en CDMX."},
]

_OPINION_TOPICS = [
    {"title": "Cuál de mis 3 carros es mejor — respuesta honesta", "context": "Tesla vs Mini JCW vs Swift Sport: criterios de diversión, practicidad, costo y experiencia real."},
    {"title": "El Swift Sport es el carro más subestimado de México", "context": "Argumento real: precio de entrada, diversión de manejo, honestidad del carro — vs lo que la gente cree."},
    {"title": "¿Vale la pena el Tesla en México con la infraestructura actual?", "context": "Opinión directa después de meses de uso: cuándo sí y cuándo el eléctrico frustra en CDMX."},
    {"title": "El Mini JCW es el carro más impráctica que he tenido — y no lo cambiaría", "context": "Crítica honesta: consumo, topes, parqueo, refacciones caras — y por qué se queda con él."},
    {"title": "Los carros eléctricos en México: ¿para quién son realmente?", "context": "Opinión sin filtro: para quién tiene sentido un eléctrico en México hoy, para quién no."},
    {"title": "¿Por qué tengo 3 carros? La respuesta incómoda", "context": "La lógica real detrás de tener 3 autos: qué llena cada uno, costo real, crítica propia."},
    {"title": "El carro deportivo barato vs el eléctrico caro: cuál da más", "context": "Swift Sport vs Tesla Model Y: qué da más por tu dinero si lo que buscas es satisfacción."},
    {"title": "FSD en México: ¿promesa cumplida o marketing?", "context": "Opinión directa después de meses de uso real en CDMX — lo que sí y lo que no."},
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
        script_type=data.get("script_type", script_type),
    )


def _load_voice_guide() -> str:
    with open(VOICE_GUIDE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def generate(article: Article, script_type: str = "trend") -> Script:
    voice_guide = _load_voice_guide()
    prompt_template = _PROMPT_BY_TYPE.get(script_type, _TREND_PROMPT)
    prompt = prompt_template.format(
        voice_guide=voice_guide,
        title=article.title,
        context=article.summary,
    )
    client = _get_client()
    response = _call_gemini(client, "gemini-2.5-flash", prompt, config=_SEARCH_CONFIG)
    return _parse_response(response, script_type)


def generate_howto() -> Script:
    topic = random.choice(_HOWTO_TOPICS)
    article = Article(
        title=topic["title"],
        url="",
        summary=topic["context"],
        source="howto",
        published=datetime.utcnow(),
    )
    return generate(article, script_type="howto")


def generate_lifestyle() -> Script:
    topic = random.choice(_LIFESTYLE_TOPICS)
    article = Article(
        title=topic["title"],
        url="",
        summary=topic["context"],
        source="lifestyle",
        published=datetime.utcnow(),
    )
    return generate(article, script_type="lifestyle")


def generate_opinion() -> Script:
    topic = random.choice(_OPINION_TOPICS)
    article = Article(
        title=topic["title"],
        url="",
        summary=topic["context"],
        source="opinion",
        published=datetime.utcnow(),
    )
    return generate(article, script_type="opinion")


def generate_evergreen() -> Script:
    """Legacy: alternates between howto and opinion."""
    if random.random() < 0.5:
        return generate_howto()
    return generate_opinion()
