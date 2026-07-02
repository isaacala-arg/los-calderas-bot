# Batch C — Implementation Report

**Fecha:** 2026-07-02  
**Implementador:** Claude Sonnet 4.6 (claude-sonnet-4-6)  
**STATUS:** DONE

---

## Commits

| Hash | Título |
|------|--------|
| `4ce4f7c` | feat: generador de carruseles (Semana en tech + banco de temas) |
| `8695979` | feat: carruseles a Notion + Semana en tech viernes 7am + carrusel manual |
| `4f742b9` | test: e2e reel/vlog/carrusel hasta Notion con mocks |

---

## Conteo de tests

- **Antes del batch:** 49 tests
- **Después del batch:** 56 tests (+7)
- **Resultado:** 56 passed, 0 failed

---

## Decisiones tomadas / concerns

### Fix no-trivial: braces en f-strings de prompts
El `_JSON_SCHEMA` definido en `carousel_generator.py` usa `{` y `}` en el ejemplo de JSON. Al concatenarlo con `_SEMANA_TECH_PROMPT` y `_TEMA_PROMPT` y llamar `.format(...)`, Python los interpreta como placeholders de formato y lanza `KeyError`. Solución: escapar todas las llaves del bloque JSON como `{{` y `}}`. El brief no advierte esto — fue detectado y corregido durante el Step 5 antes del commit.

### Pendiente de validar (primera corrida real)
1. **Primera corrida del workflow `semana-tech.yml` el viernes.** La opción `"carrusel"` en el select `Tipo` de Notion se crea automáticamente la primera vez que el script llama a `notion.pages.create` con ese valor — no hay que tocar el database manualmente.
2. **Búsqueda web en `generate_semana_tech()`.** El prompt pasa `search=True` a `llm_client.heavy`. La integración real depende de que Gemini 2.5 Pro tenga Google Search habilitado en la API key configurada.

### Lo que se confirmó leyendo código (no asumido)
- `_load_voice_guide()` y `_load_contexto_actual()` ya están en `script_generator.py` y son importables directamente — `carousel_generator.py` los reutiliza.
- `_notion` es una variable de módulo mutable en `notion_writer.py`; los tests e2e la inyectan directamente (`nw._notion = mock_notion`) igual que los tests existentes.
- `script_generator._file_cache` existe y los tests e2e lo resetean antes de generar para evitar contaminación de caché entre tests.
- El patch correcto para `llm_client.heavy` es `"src.brain.llm_client.heavy"` (patch en el módulo fuente, no en el importador) — confirmado leyendo cómo `script_generator` y `carousel_generator` importan el módulo (`from src.brain import llm_client`).

### Fuera de alcance (Fase 2)
- Chatbot Telegram (historias diarias, buenos días, canción del día).
- Integración Canva API.

---

## Fix puntual: prompts sin .format() (2026-07-02)

**Commit:** `e541f8f`  
**Implementador:** Claude Sonnet 4.6 (claude-sonnet-4-6)

### Problema
`_SEMANA_TECH_PROMPT` y `_TEMA_PROMPT` usaban `.format(voice_guide=..., contexto=..., title=..., context=...)`. Si los archivos de estilo editables a mano (`style/los-calderas-voice.md`, `style/contexto-actual.md`) contenían cualquier llave `{...}`, Python lanzaba `KeyError` y tumbaba el workflow. Además, `_JSON_SCHEMA` tenía que escaparse con `{{`/`}}` por culpa de ese patrón.

### Cambios en `src/brain/carousel_generator.py`
- Eliminados `_SEMANA_TECH_PROMPT` y `_TEMA_PROMPT` con placeholders `.format()`.
- Creados `_SEMANA_TECH_CUERPO` y `_TEMA_CUERPO` como cuerpos estáticos sin placeholders.
- `generate_semana_tech()` arma el prompt con f-string: `f"{_load_voice_guide()}\n\n---\n{_load_contexto_actual()}\n\n{_SEMANA_TECH_CUERPO}"`.
- `generate_carousel_tema()` antepone `f"TEMA: {topic['title']}\nCONTEXTO: {topic['context']}\n\n"` al cuerpo estático.
- `_JSON_SCHEMA`: revertido escapado `{{`/`}}` a llaves normales `{`/`}` (ya no hay `.format()` que las rompa).

### Cambios en `tests/brain/test_carousel_generator.py`
- Añadido `test_semana_tech_inmune_a_llaves_en_voice_guide`: parchea `_load_voice_guide` para devolver `"guia con {llaves} y {script_type} raros"`, llama `generate_semana_tech()`, verifica que no truena y que `"{llaves}"` llega literal al prompt del LLM.

### Resultado de tests
```
tests/brain/test_carousel_generator.py tests/test_e2e_contenido.py: 7 passed in 2.22s
tests/ (suite completa): 57 passed in 3.54s
```
