# Content Manager Fase 1 (Repo) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el bot de guiones en un content manager: voz real de Isaac como few-shot, ganchos/CTAs por familias con rotación, pilar vlog (sin videojuegos), carruseles semanales a Notion y serie "Semana en tech" cada viernes, con router de LLM intercambiable (light/heavy).

**Architecture:** Se agrega un router `llm_client` (light=flash, heavy=pro, proveedor por env var) del que cuelgan todos los generadores. Los 3 MD de Isaac entran a `style/` y se inyectan en los prompts. Un nuevo `carousel_generator` produce texto por slide que `notion_writer.write_carousel` sube con Tipo="carrusel". Workflow nuevo corre viernes 7am CDMX.

**Tech Stack:** Python 3.11, google-genai (gemini-2.5-pro/flash), notion-client, pytest+pytest-mock, GitHub Actions.

## Global Constraints

- Python 3.11; tests con `python -m pytest tests/ -q` desde la raíz del repo (`C:\Users\Isaac\Documents\los-calderas-bot`).
- Modelos: heavy=`gemini-2.5-pro`, light=`gemini-2.5-flash` (ya definidos en `gemini_client.py`).
- Español mexicano CDMX; NUNCA "candela/chévere/bacán"; EVITAR "nambre".
- Sin videojuegos como tema principal (spec 2C).
- Solo escenarios grabables reales: Swift propio, Tesla del papá ("Caldermóvil") ocasional, Mini de la mamá, trabajo actual — nada inventado (spec 2C/4).
- Datos/noticias SIEMPRE verificados por búsqueda; si no se puede verificar, decirlo explícito en el output (spec 4). Noticias de últimos 7-14 días.
- CTA nunca "sígueme" literal (spec 5). Ganchos decibles en máx 2-3 segundos (spec 3).
- Ganchos/CTAs: nunca la misma familia dos veces seguidas (spec 3 y banco §6).
- Cron en UTC: 7am CDMX = 13:00 UTC (CDMX ya no tiene DST).
- El cron sube directo a Notion con Estado="Pendiente" (decisión de Isaac 2026-07-02).
- Commits con mensaje en español + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: Router de LLM (light/heavy, proveedor intercambiable)

**Files:**
- Create: `src/brain/llm_client.py`
- Modify: `src/brain/evaluator.py:73` (línea `response = gemini_client.call(prompt)`)
- Modify: `src/brain/script_generator.py` (función `generate`, líneas del config/model)
- Modify: `scripts/run_custom_topic.py` (función `research_topic`)
- Test: `tests/brain/test_llm_client.py`

**Interfaces:**
- Consumes: `gemini_client.call(contents, config=None, model=MODEL)`, `gemini_client.MODEL_FLASH/MODEL_PRO/SEARCH_CONFIG` (existentes).
- Produces: `llm_client.light(prompt: str, search: bool = False)` y `llm_client.heavy(prompt: str, search: bool = False)` — devuelven el response del proveedor (con `.text`). Tasks 5 usa `heavy`.

- [ ] **Step 1: Write the failing test**

```python
# tests/brain/test_llm_client.py
from src.brain import llm_client, gemini_client


def test_light_uses_flash_sin_search(mocker):
    mock = mocker.patch("src.brain.gemini_client.call", return_value="r")
    llm_client.light("hola")
    kwargs = mock.call_args[1]
    assert kwargs["model"] == gemini_client.MODEL_FLASH
    assert kwargs["config"] is None


def test_heavy_uses_pro_con_search(mocker):
    mock = mocker.patch("src.brain.gemini_client.call", return_value="r")
    llm_client.heavy("hola", search=True)
    kwargs = mock.call_args[1]
    assert kwargs["model"] == gemini_client.MODEL_PRO
    assert kwargs["config"] is gemini_client.SEARCH_CONFIG


def test_proveedor_desconocido_truena(mocker):
    mocker.patch.object(llm_client, "PROVIDER", "openai")
    try:
        llm_client.light("hola")
        assert False, "debió tronar"
    except NotImplementedError as e:
        assert "openai" in str(e)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/brain/test_llm_client.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.brain.llm_client'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/brain/llm_client.py
"""Router de LLM — un solo punto para cambiar de proveedor y de modelos.

light() = tareas mecánicas/baratas (evaluar noticias, research, historias).
heavy() = tareas creativas (guiones, carruseles).
Para cambiar de proveedor: setear env LLM_PROVIDER y agregar su adapter aquí.
"""
import os
from src.brain import gemini_client

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")


def _call_gemini(prompt: str, tier: str, search: bool):
    model = gemini_client.MODEL_PRO if tier == "heavy" else gemini_client.MODEL_FLASH
    config = gemini_client.SEARCH_CONFIG if search else None
    return gemini_client.call(prompt, config=config, model=model)


def _dispatch(prompt: str, tier: str, search: bool):
    if PROVIDER == "gemini":
        return _call_gemini(prompt, tier, search)
    raise NotImplementedError(
        f"Proveedor LLM '{PROVIDER}' no implementado — agrega su adapter en llm_client.py"
    )


def light(prompt: str, search: bool = False):
    return _dispatch(prompt, "light", search)


def heavy(prompt: str, search: bool = False):
    return _dispatch(prompt, "heavy", search)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/brain/test_llm_client.py -v`
Expected: 3 PASS

- [ ] **Step 5: Migrar los 3 consumidores**

En `src/brain/evaluator.py`: agregar `from src.brain import llm_client` y cambiar
`response = gemini_client.call(prompt)` → `response = llm_client.light(prompt)`.
(El import de `gemini_client` puede quedarse si ya no se usa, quitarlo.)

En `src/brain/script_generator.py`, en `generate()`, reemplazar:

```python
    config = gemini_client.SEARCH_CONFIG if script_type in ("trend", "tech", "evergreen") else None
    response = gemini_client.call(prompt, config=config, model=gemini_client.MODEL_PRO)
```

por:

```python
    response = llm_client.heavy(prompt, search=script_type in ("trend", "tech", "evergreen"))
```

y cambiar el import `from src.brain import gemini_client` → `from src.brain import llm_client`.

En `scripts/run_custom_topic.py`, en `research_topic()`: cambiar
`gemini_client.call(..., config=gemini_client.SEARCH_CONFIG)` → `llm_client.light(<mismo prompt>, search=True)`
y el import correspondiente.

- [ ] **Step 6: Run full suite**

Run: `python -m pytest tests/ -q`
Expected: 40 passed (37 previos + 3 nuevos). Nota: `test_generate_uses_pro_model` sigue pasando porque heavy() delega en `gemini_client.call` con `model=MODEL_PRO`.

- [ ] **Step 7: Commit**

```bash
git add src/brain/llm_client.py src/brain/evaluator.py src/brain/script_generator.py scripts/run_custom_topic.py tests/brain/test_llm_client.py
git commit -m "feat: router llm_client light/heavy con proveedor intercambiable

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Voz real de Isaac como few-shot (guiones publicados)

**Files:**
- Create: `style/guiones-publicados.md` (copia de `C:\Users\Isaac\Downloads\guiones_publicados_isaac.md`)
- Create: `style/banco-ganchos.md` (copia de `C:\Users\Isaac\Downloads\banco_ganchos_ctas.md`, referencia humana)
- Modify: `src/brain/script_generator.py` (constantes de paths y `_build_prompt`)
- Modify: `style/los-calderas-voice.md` (línea de frases prohibidas)
- Test: `tests/brain/test_script_generator.py` (agregar test)

**Interfaces:**
- Consumes: `_load_file(path)` y `_build_prompt(...)` existentes en `script_generator.py`.
- Produces: constante `GUIONES_PUBLICADOS_PATH`; el prompt de generación contiene la sección `GUIONES YA PUBLICADOS POR ISAAC`.

- [ ] **Step 1: Copiar los archivos fuente al repo**

```bash
cp "C:/Users/Isaac/Downloads/guiones_publicados_isaac.md" style/guiones-publicados.md
cp "C:/Users/Isaac/Downloads/banco_ganchos_ctas.md" style/banco-ganchos.md
```

- [ ] **Step 2: Write the failing test**

Agregar a `tests/brain/test_script_generator.py`:

```python
def test_guiones_publicados_en_prompt(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "howto")
    pub = tmp_path / "pub.md"
    pub.write_text("MARCA-VOZ-PUBLICADA nutriologo tacos", encoding="utf-8")
    mocker.patch("src.brain.script_generator.GUIONES_PUBLICADOS_PATH", str(pub))
    sg._file_cache = {}
    voice_file = tmp_path / "los-calderas-voice.md"
    mocker.patch("src.brain.script_generator.VOICE_GUIDE_PATH", str(voice_file))
    prompt = sg._build_prompt("howto", "t", "c", "")
    assert "MARCA-VOZ-PUBLICADA" in prompt
    assert "GUIONES YA PUBLICADOS" in prompt
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/brain/test_script_generator.py::test_guiones_publicados_en_prompt -v`
Expected: FAIL con `AttributeError: ... has no attribute 'GUIONES_PUBLICADOS_PATH'`

- [ ] **Step 4: Write minimal implementation**

En `src/brain/script_generator.py`, junto a las otras constantes de path:

```python
GUIONES_PUBLICADOS_PATH = os.path.join(_STYLE_DIR, "guiones-publicados.md")
```

y en `_build_prompt`, después de agregar `voice_guide` a `sections`:

```python
    guiones_publicados = _load_file(GUIONES_PUBLICADOS_PATH)
    if guiones_publicados:
        sections.append(
            "---\nGUIONES YA PUBLICADOS POR ISAAC (voz real — imita el tono, el ritmo y los "
            "patrones; PROHIBIDO copiar frases o temas):\n" + guiones_publicados
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/brain/test_script_generator.py -v`
Expected: todos PASS

- [ ] **Step 6: Ajustar frase prohibida en voice guide**

En `style/los-calderas-voice.md`, sección "Frases PROHIBIDAS", cambiar `"¿Tú qué opinas?"` por
`"¿Tú qué opinas?" (suelto; SÍ se permite pregunta directa si es específica al contenido del video)`
— resuelve el conflicto con el banco de CTAs §2.2.

- [ ] **Step 7: Commit**

```bash
git add style/guiones-publicados.md style/banco-ganchos.md src/brain/script_generator.py style/los-calderas-voice.md tests/brain/test_script_generator.py
git commit -m "feat: guiones publicados de Isaac como few-shot de voz real

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Ganchos y CTAs por familias con rotación

**Files:**
- Create: `src/brain/ganchos.py`
- Modify: `src/brain/script_generator.py` (`_build_prompt`)
- Test: `tests/brain/test_ganchos.py`

**Interfaces:**
- Consumes: nada externo (datos embebidos, curados del banco de Isaac).
- Produces: `ganchos.build_ganchos_block(script_type: str) -> str` — bloque de prompt con familias aplicables + reglas de rotación. `script_generator._build_prompt` lo inyecta antes de `_COMMON`.

- [ ] **Step 1: Write the failing test**

```python
# tests/brain/test_ganchos.py
from src.brain import ganchos


def test_howto_incluye_familias_educativas():
    block = ganchos.build_ganchos_block("howto")
    assert "principiantes" in block
    assert "hacks" in block
    assert "choque_real" not in block  # es para trend/tech/fsd


def test_trend_prioriza_choque_real():
    block = ganchos.build_ganchos_block("trend")
    assert "choque_real" in block
    assert "PRIORIDAD ALTA" in block


def test_incluye_reglas_de_rotacion_y_ctas():
    block = ganchos.build_ganchos_block("lifestyle")
    assert "misma familia dos veces seguidas" in block
    assert "CTA" in block
    assert "sígueme" in block  # la regla de nunca decirlo literal
    assert "2-3 segundos" in block


def test_tipo_desconocido_usa_instantaneo():
    block = ganchos.build_ganchos_block("loquesea")
    assert "instantaneo" in block
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/brain/test_ganchos.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/brain/ganchos.py
"""Familias de ganchos y CTAs (curadas del banco de Isaac, style/banco-ganchos.md).

El LLM elige la familia y adapta el ___ al tema; la rotación se logra
instruyéndolo a comparar contra los ganchos recientes que ya van en el
CONTEXTO DEL CANAL (notion_reader) y los del mismo día (append_avoid_hooks).
"""

FAMILIAS = {
    "reflexion": {
        "tipos": ["lifestyle", "vlog", "opinion"],
        "ejemplos": [
            "Esto nadie te lo dice, pero todos lo piensan...",
            "¿Qué pasaría si te dijera que ___?",
            "Nadie te ha contado esto de ___...",
        ],
    },
    "principiantes": {
        "tipos": ["howto", "tech"],
        "ejemplos": [
            "Cómo empezar con ___ sin sentirte abrumado",
            "El error que comete todo principiante en ___",
            "Mi flujo de trabajo exacto para ___ (puedes copiarlo)",
            "Las 5 cosas que me hubiera gustado saber antes de empezar ___",
        ],
    },
    "hacks": {
        "tipos": ["howto", "tech"],
        "ejemplos": [
            "3 herramientas que uso a diario para ___",
            "Si siempre olvidas ___, prueba esto",
            "La forma perezosa en la que organizo mi ___ (y funciona)",
        ],
    },
    "instantaneo": {
        "tipos": ["trend", "howto", "lifestyle", "opinion", "tech", "fsd", "vlog"],
        "ejemplos": [
            "Probablemente estás haciendo ___ mal (y ni siquiera te das cuenta)",
            "Por qué tu ___ no está funcionando (y cómo solucionarlo)",
            "Cometí este error durante meses; no hagas lo mismo",
        ],
    },
    "choque_real": {
        "tipos": ["trend", "tech", "fsd"],
        "prioridad": True,  # la que mejor le ha funcionado a Isaac
        "ejemplos": [
            "Vi que [noticia real verificada] y como futuro ingeniero me pregunté...",
            "Puse a [herramienta/IA] a decidir ___. El resultado ofendió a media familia.",
            "[Cifra específica]. Eso es lo que me cuesta/tarda ___.",
        ],
    },
    "vlog": {
        "tipos": ["vlog"],
        "ejemplos": [
            "Abrir con la escena más visual del día SIN explicar; la explicación va en voz en off",
            "Hoy pasé el día [haciendo X]. Esto fue lo que aprendí.",
            "No planeaba grabar esto, pero pasó algo que quiero compartir.",
        ],
    },
}

CTAS = {
    "utilidad": 'El favorito de Isaac: "Guarda esto para cuando [situación específica del tema]" / "Mándale esto al que [situación, con humor]"',
    "pregunta_especifica": 'Pregunta que SOLO quien vio el video puede responder — nunca "¿qué opinas?" suelto',
    "indirecto_seguir": 'NUNCA "sígueme" literal. Implicar continuidad: "Esto lo voy a seguir documentando, se viene la segunda parte"',
    "reflexivo": "Solo para contenido personal: dejar la reflexión sin pedir nada",
    "feedback": '"¿Les gustaría que les cuente más de [tema]?"',
}


def build_ganchos_block(script_type: str) -> str:
    aplicables = {
        name: fam for name, fam in FAMILIAS.items() if script_type in fam["tipos"]
    }
    if not aplicables:
        aplicables = {"instantaneo": FAMILIAS["instantaneo"]}

    lines = ["LIBRERÍA DE GANCHOS — elige UNA familia y adapta el ___ al tema:"]
    for name, fam in aplicables.items():
        tag = " (PRIORIDAD ALTA — la que mejor le funciona a Isaac)" if fam.get("prioridad") else ""
        lines.append(f"- Familia '{name}'{tag}:")
        lines += [f'    · "{e}"' for e in fam["ejemplos"]]

    lines.append(
        "\nREGLAS DE GANCHO: debe poder decirse/leerse en máximo 2-3 segundos. "
        "NUNCA uses la misma familia dos veces seguidas — compara contra los ganchos "
        "recientes del CONTEXTO DEL CANAL y los ya generados hoy, y si la familia se "
        "repite, elige otra."
    )
    lines.append("\nFAMILIAS DE CTA — elige la que corresponda al contenido:")
    lines += [f"- {name}: {desc}" for name, desc in CTAS.items()]
    lines.append(
        'REGLA DE CTA: jamás "sígueme" literal; si es pregunta, específica al contenido.'
    )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/brain/test_ganchos.py -v`
Expected: 4 PASS

- [ ] **Step 5: Inyectar en el prompt**

En `src/brain/script_generator.py`: `from src.brain.ganchos import build_ganchos_block` y en `_build_prompt`, justo antes de `sections.append(_COMMON...)`:

```python
    sections.append("---\n" + build_ganchos_block(script_type))
```

Agregar test en `tests/brain/test_script_generator.py`:

```python
def test_ganchos_block_en_prompt(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "trend")
    prompt = sg._build_prompt("trend", "t", "c", "")
    assert "LIBRERÍA DE GANCHOS" in prompt
    assert "choque_real" in prompt
```

- [ ] **Step 6: Run full suite**

Run: `python -m pytest tests/ -q`
Expected: todos PASS

- [ ] **Step 7: Commit**

```bash
git add src/brain/ganchos.py src/brain/script_generator.py tests/brain/test_ganchos.py tests/brain/test_script_generator.py
git commit -m "feat: libreria de ganchos y CTAs por familias con rotacion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Pilar vlog, fuera videojuegos, regla de verificación

**Files:**
- Modify: `src/brain/script_generator.py` (`_TYPE_GUIDANCE`, `_LIFESTYLE_TOPICS`, nuevo `_VLOG_TOPICS`, `generate_vlog`, `_COMMON`)
- Modify: `scripts/run_generator.py` (rotación script 3)
- Test: `tests/brain/test_script_generator.py`

**Interfaces:**
- Consumes: `_generate_from_bank(bank, script_type, canal_context)` existente.
- Produces: `generate_vlog(canal_context: str = "") -> Script` con `script_type="vlog"`. `run_generator` rota `[generate_lifestyle, generate_vlog, generate_fsd]`.

- [ ] **Step 1: Write the failing test**

```python
def test_generate_vlog_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "vlog")
    script = sg.generate_vlog()
    assert script.script_type == "vlog"
    assert script.hook != ""


def test_sin_videojuegos_en_bancos():
    todos = sg._LIFESTYLE_TOPICS + sg._OPINION_TOPICS + sg._HOWTO_TOPICS + sg._TECH_TOPICS + sg._FSD_TOPICS + sg._VLOG_TOPICS
    texto = " ".join(t["title"] + t["context"] for t in todos).lower()
    for palabra in ["assetto", "beamng", "videojuego", "simulador"]:
        assert palabra not in texto, f"'{palabra}' sigue en un banco de temas"


def test_regla_verificacion_en_prompt(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "trend")
    prompt = sg._build_prompt("trend", "t", "c", "")
    assert "NO VERIFICADO" in prompt
    assert "7-14 días" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/brain/test_script_generator.py -v -k "vlog or videojuegos or verificacion"`
Expected: 3 FAIL (`generate_vlog` no existe, tema Assetto presente, regla ausente)

- [ ] **Step 3: Implementar**

En `_TYPE_GUIDANCE` agregar:

```python
    "vlog": (
        "TIPO: VLOG con VOZ EN OFF sobre clips reales del día de Isaac. El campo 'body' es el "
        "guion de la VOZ EN OFF (se graba encima de los clips, tono reflexivo pero con humor). "
        "El gancho es la escena más visual/emotiva del día SIN explicarla aún. El campo 'puntos' "
        "es la LISTA DE CLIPS que Isaac debe grabar durante el día (cortos, fáciles: llegando a la "
        "oficina, el gym, manejando el Swift). Cierre con pregunta/reflexión que invite a comentar."
    ),
```

Nuevo banco (después de `_FSD_TOPICS`):

```python
_VLOG_TOPICS = [
    {"title": "Un día real de becario de tecnología (voz en off)", "context": "Clips del día: despertarse, home office u oficina, gym, noche trabajando en su proyecto. Voz en off honesta sobre lo que nadie cuenta de ser becario a los 20."},
    {"title": "Del gym a la chamba: así se ve mi cambio físico", "context": "Clips de entreno + rutina diaria. Voz en off sobre disciplina vs motivación ('tu cincuenta tiene que ser tu cien'), sin sermón."},
    {"title": "Grabé todo lo que hice un viernes (y por qué el Swift es parte)", "context": "Clips del viernes: oficina, tráfico en el Swift, gym, noche. Voz en off con humor de ingeniero sobre la rutina real."},
    {"title": "Lo que aprendí esta semana (recap personal)", "context": "Clips sueltos de la semana. Voz en off: 2-3 aprendizajes concretos de chamba/gym/proyecto con remate de humor."},
]
```

Quitar de `_LIFESTYLE_TOPICS` el dict de Assetto Corsa (título "Lo que Assetto Corsa NO te prepara para manejar en CDMX") — eliminarlo completo.

Nueva función junto a las demás:

```python
def generate_vlog(canal_context: str = "") -> Script:
    return _generate_from_bank(_VLOG_TOPICS, "vlog", canal_context)
```

En `_COMMON`, después de la línea de REGLA DE ORO, agregar:

```
VERIFICACIÓN (no negociable): cualquier dato o noticia debe venir de la búsqueda web o del
contexto dado — NUNCA lo inventes. Si un dato no se puede verificar, escríbelo explícito en
"topic_context" con la marca "DATO NO VERIFICADO". Para noticias, usa solo de los últimos
7-14 días; nunca recicles anuncios viejos como nuevos.
```

En `scripts/run_generator.py`: importar `generate_vlog` y cambiar
`personal_rotation = [generate_lifestyle, generate_fsd]` →
`personal_rotation = [generate_lifestyle, generate_vlog, generate_fsd]`.

- [ ] **Step 4: Run full suite**

Run: `python -m pytest tests/ -q`
Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add src/brain/script_generator.py scripts/run_generator.py tests/brain/test_script_generator.py
git commit -m "feat: pilar vlog voz en off, fuera videojuegos, regla de verificacion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Generador de carruseles (Semana en tech + temas)

**Files:**
- Modify: `src/models.py` (dataclass `Carousel`)
- Create: `src/brain/carousel_generator.py`
- Test: `tests/brain/test_carousel_generator.py`

**Interfaces:**
- Consumes: `llm_client.heavy(prompt, search=True)` (Task 1), `_load_file`-equivalente propio para voice guide.
- Produces: `Carousel(title, slides, caption, hashtags, carousel_type)` con `slides: list[dict]` de forma `{"titulo": str, "bullets": list[str]}`; `generate_semana_tech() -> Carousel`; `generate_carousel_tema(topic: dict | None = None) -> Carousel`; `CAROUSEL_TOPICS: list[dict]`. Task 6 consume las tres.

- [ ] **Step 1: Agregar el modelo en `src/models.py`**

```python
@dataclass
class Carousel:
    title: str
    slides: list        # list[dict] — {"titulo": str, "bullets": list[str]}
    caption: str
    hashtags: list      # list[str]
    carousel_type: str  # "semana_tech" | "tema"
```

- [ ] **Step 2: Write the failing test**

```python
# tests/brain/test_carousel_generator.py
import json
from src.brain import carousel_generator as cg


_FAKE = json.dumps({
    "title": "Semana en tech: lo que pasó y por qué importa",
    "slides": [
        {"titulo": "Portada: 3 noticias que sí te afectan", "bullets": []},
        {"titulo": "Apple libera X", "bullets": ["Qué pasó", "Por qué te importa"]},
        {"titulo": "Cierre", "bullets": ["La próxima entrega el viernes"]},
    ],
    "caption": "Lo que pasó esta semana en tech, sin humo.",
    "hashtags": ["#techtok", "#tecnologia"],
})


def _mock_heavy(mocker):
    resp = mocker.MagicMock()
    resp.text = _FAKE
    return mocker.patch("src.brain.llm_client.heavy", return_value=resp)


def test_semana_tech_usa_search_y_parsea(mocker):
    mock = _mock_heavy(mocker)
    c = cg.generate_semana_tech()
    assert mock.call_args[1]["search"] is True
    assert c.carousel_type == "semana_tech"
    assert len(c.slides) == 3
    assert c.slides[1]["bullets"] == ["Qué pasó", "Por qué te importa"]


def test_prompt_semana_tech_exige_verificacion(mocker):
    mock = _mock_heavy(mocker)
    cg.generate_semana_tech()
    prompt = mock.call_args[0][0]
    assert "últimos 7 días" in prompt
    assert "NO VERIFICADO" in prompt or "no la incluyas" in prompt


def test_carousel_tema_toma_del_banco(mocker):
    _mock_heavy(mocker)
    c = cg.generate_carousel_tema()
    assert c.carousel_type == "tema"
    assert len(cg.CAROUSEL_TOPICS) >= 4
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/brain/test_carousel_generator.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 4: Write minimal implementation**

```python
# src/brain/carousel_generator.py
"""Genera carruseles (texto por slide, listo para pegar en Canva)."""
import json
import random
from src.brain import llm_client
from src.brain.script_generator import _load_voice_guide, _load_contexto_actual
from src.models import Carousel

_JSON_SCHEMA = """
Responde SOLO con JSON válido (sin markdown, sin ```):
{
  "title": "título del carrusel (sin el prefijo 'Carrusel:')",
  "slides": [
    {"titulo": "texto grande del slide", "bullets": ["bullet corto 1", "bullet corto 2"]}
  ],
  "caption": "caption para el post (1-2 líneas, tono de Isaac)",
  "hashtags": ["5 hashtags"]
}
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/brain/test_carousel_generator.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add src/models.py src/brain/carousel_generator.py tests/brain/test_carousel_generator.py
git commit -m "feat: generador de carruseles (Semana en tech + banco de temas)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Carruseles a Notion + workflows (viernes 7am y manual)

**Files:**
- Modify: `src/outputs/notion_writer.py` (nueva función `write_carousel`)
- Create: `scripts/run_semana_tech.py`
- Create: `scripts/run_carousel.py`
- Create: `.github/workflows/semana-tech.yml`
- Create: `.github/workflows/carousel.yml`
- Test: `tests/outputs/test_notion_writer.py`

**Interfaces:**
- Consumes: `Carousel` (Task 5), helpers `_h2/_p/_bullet/_bold_line` existentes en `notion_writer.py`, `generate_semana_tech()/generate_carousel_tema()`.
- Produces: `write_carousel(carousel: Carousel) -> str` (URL de la página creada, título `Carrusel: {title}`, Tipo="carrusel", Estado="Pendiente").

- [ ] **Step 1: Write the failing test**

Agregar a `tests/outputs/test_notion_writer.py`:

```python
from src.models import Carousel


def test_write_carousel_crea_pagina_ordenada(mocker):
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/carr1"}
    nw._notion = mock_notion

    c = Carousel(
        title="Semana en tech: 30 jun - 4 jul",
        slides=[
            {"titulo": "Portada", "bullets": []},
            {"titulo": "Noticia 1", "bullets": ["qué pasó", "por qué te importa"]},
        ],
        caption="La semana sin humo.",
        hashtags=["#techtok"],
        carousel_type="semana_tech",
    )
    url = nw.write_carousel(c)

    assert url == "https://notion.so/carr1"
    kwargs = mock_notion.pages.create.call_args[1]
    titulo = kwargs["properties"]["Título"]["title"][0]["text"]["content"]
    assert titulo == "Carrusel: Semana en tech: 30 jun - 4 jul"
    assert kwargs["properties"]["Tipo"]["select"]["name"] == "carrusel"
    contenido = str(kwargs["children"])
    assert "Slide 1" in contenido and "Slide 2" in contenido
    assert "por qué te importa" in contenido
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/outputs/test_notion_writer.py -v`
Expected: FAIL con `AttributeError: ... no attribute 'write_carousel'`

- [ ] **Step 3: Write minimal implementation**

En `src/outputs/notion_writer.py` (import `Carousel` desde `src.models`):

```python
def write_carousel(carousel: Carousel) -> str:
    from src.config import settings
    notion = _get_notion()
    children = [
        _h2("Caption sugerido"),
        _p(carousel.caption),
        _h2("Hashtags"),
        _p(" ".join(carousel.hashtags)),
        _h2("📇 Slides — copia y pega en Canva"),
    ]
    for i, slide in enumerate(carousel.slides, 1):
        children.append(_bold_line(f"Slide {i} — {slide['titulo']}"))
        children += [_bullet(b) for b in slide["bullets"]]
    response = notion.pages.create(
        parent={"database_id": settings.NOTION_DATABASE_ID},
        properties={
            "Título": {"title": [{"text": {"content": f"Carrusel: {carousel.title}"[:200]}}]},
            "Tipo": {"select": {"name": "carrusel"}},
            "Estado": {"select": {"name": "Pendiente"}},
            "Fecha": {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%d")}},
        },
        children=children,
    )
    return response["url"]
```

Nota: la API de Notion crea sola la opción "carrusel" del select "Tipo" al primer uso — no hay que tocar el database.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/outputs/test_notion_writer.py -v`
Expected: PASS

- [ ] **Step 5: Scripts de entrada**

```python
# scripts/run_semana_tech.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.brain.carousel_generator import generate_semana_tech
from src.outputs.notion_writer import write_carousel


def main():
    print("Generando 'Semana en tech' (busqueda web, ultimos 7 dias)...")
    carousel = generate_semana_tech()
    url = write_carousel(carousel)
    print(f"Carrusel guardado en Notion: {url}")


if __name__ == "__main__":
    main()
```

```python
# scripts/run_carousel.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.brain.carousel_generator import generate_carousel_tema, CAROUSEL_TOPICS
from src.outputs.notion_writer import write_carousel


def main():
    wanted = os.environ.get("CAROUSEL_TOPIC", "").strip().lower()
    topic = None
    if wanted:
        topic = next((t for t in CAROUSEL_TOPICS if wanted in t["title"].lower()), None)
        if topic is None:
            print(f"AVISO: '{wanted}' no está en el banco; usando uno al azar")
    carousel = generate_carousel_tema(topic)
    url = write_carousel(carousel)
    print(f"Carrusel guardado en Notion: {url}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Workflows**

```yaml
# .github/workflows/semana-tech.yml
name: Semana en Tech (carrusel semanal)

on:
  schedule:
    - cron: "0 13 * * 5"   # viernes 7am CDMX (UTC-6)
  workflow_dispatch:

jobs:
  carousel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - run: pip install -r requirements.txt
      - name: Generate weekly tech carousel
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          NOTION_API_TOKEN: ${{ secrets.NOTION_API_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
        run: python scripts/run_semana_tech.py
```

```yaml
# .github/workflows/carousel.yml
name: Carrusel por Tema (manual)

on:
  workflow_dispatch:
    inputs:
      topic:
        description: "Parte del título del tema (vacío = al azar del banco)"
        required: false
        default: ""

jobs:
  carousel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - run: pip install -r requirements.txt
      - name: Generate topic carousel
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          NOTION_API_TOKEN: ${{ secrets.NOTION_API_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
          CAROUSEL_TOPIC: ${{ github.event.inputs.topic }}
        run: python scripts/run_carousel.py
```

- [ ] **Step 7: Run full suite + commit**

Run: `python -m pytest tests/ -q` — Expected: todos PASS

```bash
git add src/outputs/notion_writer.py scripts/run_semana_tech.py scripts/run_carousel.py .github/workflows/semana-tech.yml .github/workflows/carousel.yml tests/outputs/test_notion_writer.py
git commit -m "feat: carruseles a Notion + Semana en tech viernes 7am + carrusel manual

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Validación end-to-end y entrega

**Files:**
- Create: `tests/test_e2e_contenido.py`
- Modify: ninguno (solo validación)

**Interfaces:**
- Consumes: todo lo anterior con LLM y Notion mockeados.

- [ ] **Step 1: Write the e2e test**

```python
# tests/test_e2e_contenido.py
"""E2E con mocks: un contenido de cada tipo pasa completo por generación → Notion.
(Historias diarias quedan para la Fase 2 — chatbot — según decisión de Isaac.)"""
import json
from unittest.mock import MagicMock
from src.brain import script_generator as sg
from src.brain import carousel_generator as cg
from src.outputs import notion_writer as nw


def _fake_script(script_type):
    return json.dumps({
        "title": "t", "topic_context": "c", "hook": "h", "body": "b" * 200, "cta": "cta",
        "spot": "s", "como_grabar": "cg", "puntos": ["p1"], "arranque": "a",
        "hashtags_tiktok": ["#x"], "hashtags_reels": [], "hashtags_shorts": [],
        "script_type": script_type,
    })


def _fake_carousel():
    return json.dumps({
        "title": "Semana en tech", "caption": "cap", "hashtags": ["#t"],
        "slides": [{"titulo": "Portada", "bullets": []}, {"titulo": "N1", "bullets": ["b"]}],
    })


def test_e2e_reel_hasta_notion(mocker, tmp_path):
    resp = mocker.MagicMock(); resp.text = _fake_script("howto")
    mocker.patch("src.brain.llm_client.heavy", return_value=resp)
    sg._file_cache = {}
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/x"}
    nw._notion = mock_notion

    script = sg.generate_howto()
    url = nw.write_script(script)
    assert url.startswith("https://notion.so/")
    assert mock_notion.pages.create.call_args[1]["properties"]["Tipo"]["select"]["name"] == "howto"


def test_e2e_vlog_hasta_notion(mocker):
    resp = mocker.MagicMock(); resp.text = _fake_script("vlog")
    mocker.patch("src.brain.llm_client.heavy", return_value=resp)
    sg._file_cache = {}
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/v"}
    nw._notion = mock_notion
    url = nw.write_script(sg.generate_vlog())
    assert url == "https://notion.so/v"


def test_e2e_carrusel_hasta_notion(mocker):
    resp = mocker.MagicMock(); resp.text = _fake_carousel()
    mocker.patch("src.brain.llm_client.heavy", return_value=resp)
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/c"}
    nw._notion = mock_notion
    url = nw.write_carousel(cg.generate_semana_tech())
    assert url == "https://notion.so/c"
```

- [ ] **Step 2: Run e2e + full suite**

Run: `python -m pytest tests/ -q`
Expected: todos PASS (≈52)

- [ ] **Step 3: Commit + push**

```bash
git add tests/test_e2e_contenido.py
git commit -m "test: e2e reel/vlog/carrusel hasta Notion con mocks

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git pull --rebase && git push
```

- [ ] **Step 4: Entrega (spec sección 8)**

Redactar en el chat: resumen de cambios con fundamento de cada decisión, qué quedó pendiente de validar (primera corrida real del workflow de viernes; opción "carrusel" apareciendo en el select de Notion), qué se asumió vs qué se confirmó leyendo código.

---

## Fuera de alcance de este plan (Fase 2 — plan aparte tras OK de arquitectura)

- Chatbot Telegram (historias diarias, buenos días, canción del día, "qué subo hoy") con proveedor LLM intercambiable y routing light/heavy — requiere infraestructura siempre-encendida fuera de GitHub Actions.
- Integración Canva API (sección 6.1) — solo reporte de factibilidad, sin código.
