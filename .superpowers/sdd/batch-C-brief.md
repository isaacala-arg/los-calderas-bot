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
