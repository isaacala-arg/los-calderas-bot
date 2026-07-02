# Batch B — Implementation Report

**Fecha:** 2026-07-02  
**Implementador:** Claude Sonnet 4.6 (claude-sonnet-4-6)

---

## STATUS: DONE

---

## Commits

| Hash | Título |
|------|--------|
| `f917b16` | feat: libreria de ganchos y CTAs por familias con rotacion |
| `fc23bbf` | feat: pilar vlog voz en off, fuera videojuegos, regla de verificacion |

---

## Conteo final de tests

- Baseline (Tasks 1-2 ya hechas): **41 tests**
- Tras Task 3: **46 tests** (+5: 4 en test_ganchos.py + 1 integración en test_script_generator.py)
- Tras Task 4: **49 tests** (+3: generate_vlog, sin_videojuegos, regla_verificacion)
- **Total final: 49 passed, 0 failed**

---

## Qué se hizo

### Task 3 — Ganchos y CTAs por familias con rotación

- Creado `src/brain/ganchos.py` con:
  - `FAMILIAS`: 6 familias de ganchos (reflexion, principiantes, hacks, instantaneo, choque_real, vlog)
  - `CTAS`: 5 familias de CTA con reglas de estilo
  - `build_ganchos_block(script_type)`: filtra familias aplicables al tipo, marca `choque_real` como PRIORIDAD ALTA para trend/tech/fsd, tipos desconocidos reciben `instantaneo`, incluye reglas de rotación y la restricción de nunca "sígueme" literal
- Modificado `src/brain/script_generator.py`: importa `build_ganchos_block` e inyecta el bloque en `_build_prompt` justo antes de `_COMMON`
- Creado `tests/brain/test_ganchos.py` (4 tests TDD)
- Agregado `test_ganchos_block_en_prompt` en `tests/brain/test_script_generator.py`

### Task 4 — Pilar vlog, fuera videojuegos, regla de verificación

- Agregado `"vlog"` a `_TYPE_GUIDANCE` en `script_generator.py` con instrucciones de voz en off, clips grabables, gancho visual sin spoiler
- Creado `_VLOG_TOPICS` (4 temas) después de `_FSD_TOPICS`: día real de becario, cambio físico, viernes con el Swift, recap semanal — todos grabables con el Swift u oficina
- Eliminado el dict de Assetto Corsa de `_LIFESTYLE_TOPICS` (título "Lo que Assetto Corsa NO te prepara...")
- Agregada la regla de VERIFICACIÓN (DATO NO VERIFICADO, 7-14 días) en `_COMMON` después de la REGLA DE ORO
- Creada `generate_vlog(canal_context="")` en `script_generator.py`
- Modificado `scripts/run_generator.py`: importa `generate_vlog` y cambia `personal_rotation` a `[generate_lifestyle, generate_vlog, generate_fsd]`
- Agregados 3 tests TDD en `tests/brain/test_script_generator.py`

---

## Concerns

Ninguno. Todos los pasos del brief se cumplieron en orden (test falla → implementación → test pasa → commit). No se tocaron archivos fuera de los listados en el brief.
