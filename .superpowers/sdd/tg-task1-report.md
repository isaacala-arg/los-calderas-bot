# tg-task1-report — fix(telegram): intent de guion solo con pedido explícito

**Fecha:** 2026-07-02
**Commit:** 79a37a9
**Rama:** main

---

## Cambio realizado

### telegram-bot/worker.js

**Problema:** La condición original disparaba la intent "guion" con cualquier mención casual (ej. "el guion de ayer me quedó bien").

**Fix en detectarIntent:** Se reemplazó por dos patrones explícitos que requieren intención activa de pedir un guion.

**Fix en extraerTema:** Se reescribió con grupos de captura; devuelve "" cuando no hay tema (el handler ya pide el tema en ese caso).

### telegram-bot/test.mjs

Se agregaron 2 nuevos tests:
- detectarIntent: mencionar guion de conversacional NO dispara guion
- detectarIntent: formas explícitas SÍ disparan guion con tema

---

## Output de tests

  pass 9 | fail 0 | tests 9 | duration_ms 94.9469
