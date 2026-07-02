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

