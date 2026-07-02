# Batch A — Reporte de implementación

**Fecha:** 2026-07-02  
**Ejecutor:** Claude Sonnet 4.6 (agente implementador)

---

## Task 1: Router llm_client light/heavy con proveedor intercambiable

### Qué se hizo
1. **Test escrito primero** (`tests/brain/test_llm_client.py`): 3 tests — `test_light_uses_flash_sin_search`, `test_heavy_uses_pro_con_search`, `test_proveedor_desconocido_truena`. Todos fallaban con `ImportError: cannot import name 'llm_client'` (esperado).
2. **Implementación mínima** (`src/brain/llm_client.py`): módulo con `PROVIDER` (env `LLM_PROVIDER`, default `"gemini"`), `_call_gemini`, `_dispatch`, `light()`, `heavy()`. Delega a `gemini_client.call` con el modelo y config correctos según tier y flag `search`.
3. **Migración de 3 consumidores:**
   - `src/brain/evaluator.py`: import `gemini_client` → `llm_client`; `gemini_client.call(prompt)` → `llm_client.light(prompt)`.
   - `src/brain/script_generator.py`: import `gemini_client` → `llm_client`; el bloque `config/call` en `generate()` reemplazado por `llm_client.heavy(prompt, search=...)`.
   - `scripts/run_custom_topic.py`: import → `llm_client`; `gemini_client.call(..., config=SEARCH_CONFIG)` → `llm_client.light(..., search=True)`.
4. **Suite completa:** 37 prev + 3 nuevos = **40 passed**.

### Output de tests
```
40 passed in 2.47s
```

---

## Task 2: Guiones publicados de Isaac como few-shot de voz real

### Qué se hizo
1. **Archivos copiados al repo:**
   - `C:/Users/Isaac/Downloads/guiones_publicados_isaac.md` → `style/guiones-publicados.md`
   - `C:/Users/Isaac/Downloads/banco_ganchos_ctas.md` → `style/banco-ganchos.md`
2. **Test escrito primero** (`test_guiones_publicados_en_prompt` en `tests/brain/test_script_generator.py`): fallaba con `AttributeError: ... has no attribute 'GUIONES_PUBLICADOS_PATH'` (esperado).
3. **Implementación mínima** en `src/brain/script_generator.py`:
   - Constante `GUIONES_PUBLICADOS_PATH = os.path.join(_STYLE_DIR, "guiones-publicados.md")` junto a las demás rutas.
   - En `_build_prompt`: bloque que carga el archivo y, si no está vacío, lo agrega como sección `GUIONES YA PUBLICADOS POR ISAAC` antes de `CONTEXTO DEL CANAL`.
4. **Ajuste en `style/los-calderas-voice.md`**: sección "Frases PROHIBIDAS" — `"¿Tú qué opinas?"` → `"¿Tú qué opinas?" (suelto; SÍ se permite pregunta directa si es específica al contenido del video)`. Resuelve conflicto con banco de CTAs §2.2.
5. **Suite completa:** 40 prev + 1 nuevo = **41 passed**.

### Output de tests
```
41 passed in 2.53s
```

---

## Self-review

- TDD seguido al pie de la letra en ambas tasks: test rojo → implementación → test verde → commit.
- Los commits usan exactamente los mensajes textuales del brief (incluyendo `Co-Authored-By`).
- `test_generate_uses_pro_model` sigue pasando porque `heavy()` delega en `gemini_client.call` con `model=MODEL_PRO` — la cadena de dependencia se preserva correctamente.
- El `_file_cache` se limpia en el nuevo test antes de parchear `GUIONES_PUBLICADOS_PATH`, igual que los tests existentes.
- No se tocaron archivos fuera de los listados en el brief.
- Sin `git push` (per instrucciones).

### Concerns
Ninguno. Implementación limpia, todos los tests pasan.
