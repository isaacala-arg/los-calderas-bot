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

