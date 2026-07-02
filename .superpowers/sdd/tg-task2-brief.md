# Telegram Chatbot Fase 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chatbot personal de Isaac en Telegram (Cloudflare Worker gratuito, siempre encendido) que responde historias de buenos días, canción del día, "¿qué subo hoy?" leyendo Notion, genera historias/encuestas, y dispara guiones del repo — con proveedor LLM intercambiable y routing light/heavy.

**Architecture:** Un solo Cloudflare Worker (`telegram-bot/worker.js`, JS módulos, sin build) recibe el webhook de Telegram, rutea por intent con funciones puras testeables, y llama REST directo a Gemini (light/heavy), Notion (query semanal) y GitHub Actions (workflow_dispatch de `custom-topic.yml`, input `tema`). Estado mínimo (rotación de buenos días) en Cloudflare KV. Seguridad: secret token de Telegram + allowlist de chat_id (solo Isaac).

**Tech Stack:** Cloudflare Workers (plan free), JavaScript ES modules, `node --test` (Node ≥18; local hay v24), wrangler CLI, APIs REST: Telegram Bot API, Gemini `generateContent`, Notion 2022-06-28, GitHub Actions dispatches.

## Global Constraints

- Todo vive en `telegram-bot/` dentro del repo `C:\Users\Isaac\Documents\los-calderas-bot` (rama main).
- Tests: `node --test telegram-bot/` desde la raíz — deben pasar SIN red ni secrets (solo funciones puras).
- Worker sin dependencias npm ni paso de build (un archivo, `fetch` nativo).
- Routing de modelos: light=`gemini-2.5-flash` (historias, chat, frases), heavy=`gemini-2.5-pro` (nada lo usa aún en el worker — los guiones pesados se delegan al repo vía GitHub). Proveedor por var `LLM_PROVIDER` (default `gemini`); otro proveedor → responder error claro, no tronar silencioso.
- Seguridad NO negociable: (1) validar header `X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_SECRET`; (2) ignorar mensajes cuyo `chat.id` ≠ `ALLOWED_CHAT_ID`.
- Buenos días: 4 variantes de la spec §2A, NUNCA la misma dos días seguidos (estado en KV `ESTADO`, key `lastBuenosDias`).
- CTA/textos en español mexicano CDMX, tono de Isaac (breve, sin "sígueme").
- "Qué subo hoy": contar páginas de Notion con `Fecha` en los últimos 7 días agrupadas por `Tipo`; si reels (tipos trend/howto/lifestyle/opinion/tech/fsd/vlog) ≥ 2 esta semana → sugerir carrusel; si no → sugerir reel del pilar menos usado. UNA sola opción concreta (spec §2 lógica de selección).
- Guion bajo demanda: POST `https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/custom-topic.yml/dispatches` body `{"ref":"main","inputs":{"tema": <tema>}}` con PAT `GITHUB_TOKEN` (fine-grained, solo Actions read/write de este repo).
- Isaac hace lo MÍNIMO: el README de setup no puede pasar de ~10 minutos de pasos (BotFather, cuenta Cloudflare, `npx wrangler`, secrets, /setup).
- Commits en español + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. No push (el controlador pushea al final).

---

### Task 2: Integraciones reales (LLM, Notion, GitHub, KV), ruta /setup y README de 10 minutos

**Files:**
- Modify: `telegram-bot/worker.js` (reemplazar stubs, agregar /setup)
- Create: `telegram-bot/README.md`
- Test: `telegram-bot/test.mjs` (agregar tests de helpers puros nuevos)

**Interfaces:**
- Consumes: exports de Task 1.
- Produces: `construirFiltroNotion(hoy: Date) -> object` y `contarPorTipo(paginas: array) -> object` exportados (puros, testeables). Stubs reemplazados por implementaciones reales.

- [ ] **Step 1: Write the failing tests (helpers puros nuevos)**

Agregar a `telegram-bot/test.mjs`:

```javascript
import { construirFiltroNotion, contarPorTipo } from "./worker.js";

test("construirFiltroNotion pide Fecha de los últimos 7 días", () => {
  const f = construirFiltroNotion(new Date("2026-07-02T12:00:00Z"));
  assert.equal(f.filter.property, "Fecha");
  assert.equal(f.filter.date.on_or_after, "2026-06-26");
});

test("contarPorTipo agrupa por el select Tipo", () => {
  const paginas = [
    { properties: { Tipo: { select: { name: "trend" } } } },
    { properties: { Tipo: { select: { name: "trend" } } } },
    { properties: { Tipo: { select: null } } },
    { properties: { Tipo: { select: { name: "carrusel" } } } },
  ];
  assert.deepEqual(contarPorTipo(paginas), { trend: 2, carrusel: 1 });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test telegram-bot/`
Expected: los 2 nuevos FAIL (export inexistente); los 7 previos PASS

- [ ] **Step 3: Implementar integraciones (reemplazar stubs en worker.js)**

```javascript
// Reemplaza las 5 funciones stub por:

async function llamarLLM(env, prompt, tier) {
  if ((env.LLM_PROVIDER || "gemini") !== "gemini")
    return `Proveedor LLM '${env.LLM_PROVIDER}' no implementado — configura el adapter en worker.js`;
  const model = tier === "heavy" ? env.MODEL_HEAVY : env.MODEL_LIGHT;
  const r = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.LLM_API_KEY}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
    }
  );
  if (!r.ok) throw new Error(`LLM ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const data = await r.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || "(sin respuesta del modelo)";
}

export function construirFiltroNotion(hoy) {
  const desde = new Date(hoy.getTime() - 6 * 24 * 60 * 60 * 1000);
  return {
    filter: { property: "Fecha", date: { on_or_after: desde.toISOString().slice(0, 10) } },
    page_size: 50,
  };
}

export function contarPorTipo(paginas) {
  const conteos = {};
  for (const p of paginas) {
    const tipo = p.properties?.Tipo?.select?.name;
    if (tipo) conteos[tipo] = (conteos[tipo] || 0) + 1;
  }
  return conteos;
}

async function consultarNotion(env) {
  const r = await fetch(`https://api.notion.com/v1/databases/${env.NOTION_DATABASE_ID}/query`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.NOTION_API_TOKEN}`,
      "content-type": "application/json",
      "Notion-Version": "2022-06-28",
    },
    body: JSON.stringify(construirFiltroNotion(new Date())),
  });
  if (!r.ok) throw new Error(`Notion ${r.status}`);
  return contarPorTipo((await r.json()).results || []);
}

async function dispararGuion(env, tema) {
  const r = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/custom-topic.yml/dispatches`,
    {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.GITHUB_TOKEN}`,
        accept: "application/vnd.github+json",
        "user-agent": "los-calderas-telegram",
      },
      body: JSON.stringify({ ref: "main", inputs: { tema } }),
    }
  );
  if (r.status !== 204) throw new Error(`GitHub ${r.status}: ${(await r.text()).slice(0, 200)}`);
}

async function leerEstado(env, key) {
  return env.ESTADO ? env.ESTADO.get(key) : null;
}

async function guardarEstado(env, key, valor) {
  if (env.ESTADO) await env.ESTADO.put(key, valor);
}
```

Y en `export default fetch`, ANTES del bloque `/webhook`, agregar la ruta de setup (registra el webhook por ti — un paso menos para Isaac):

```javascript
    if (url.pathname === "/setup" && request.method === "GET") {
      if (url.searchParams.get("secret") !== env.TELEGRAM_SECRET)
        return new Response("forbidden", { status: 403 });
      const hook = `${url.origin}/webhook`;
      const r = await fetch(
        `https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/setWebhook?url=${encodeURIComponent(hook)}&secret_token=${env.TELEGRAM_SECRET}`
      );
      return new Response(await r.text(), { headers: { "content-type": "application/json" } });
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test telegram-bot/`
Expected: 9 tests PASS

- [ ] **Step 5: README de setup (≤10 min de Isaac)**

```markdown
# Bot de Telegram — Los Calderas (setup una sola vez, ~10 min)

## 1. Crea el bot (2 min)
1. En Telegram habla con **@BotFather** → `/newbot` → nombre: `Los Calderas Manager` → usuario: el que quieras terminado en `bot`.
2. Guarda el **token** que te da (ese es `TELEGRAM_TOKEN`).
3. Habla con **@userinfobot** → te dice tu **id** numérico (ese es `ALLOWED_CHAT_ID`).

## 2. Cuenta de Cloudflare (3 min)
1. Crea cuenta gratis en https://dash.cloudflare.com/sign-up (no pide tarjeta).

## 3. Despliega el worker (5 min, desde esta carpeta `telegram-bot/`)
```bash
npx wrangler login                      # abre el navegador, autoriza
npx wrangler kv namespace create ESTADO # copia el id que imprime a wrangler.toml
npx wrangler deploy                     # te da la URL https://los-calderas-telegram.<tu>.workers.dev

# Secrets (te los pide uno por uno):
npx wrangler secret put TELEGRAM_TOKEN      # el de BotFather
npx wrangler secret put TELEGRAM_SECRET     # inventa una contraseña larga
npx wrangler secret put ALLOWED_CHAT_ID     # tu id de @userinfobot
npx wrangler secret put LLM_API_KEY         # tu API key de Gemini
npx wrangler secret put NOTION_API_TOKEN    # el mismo del repo
npx wrangler secret put NOTION_DATABASE_ID  # el mismo del repo
npx wrangler secret put GITHUB_TOKEN        # PAT fine-grained: repo los-calderas-bot, permiso Actions: Read and write
```

## 4. Conecta Telegram (30 seg)
Abre en el navegador:
`https://los-calderas-telegram.<tu>.workers.dev/setup?secret=TU_TELEGRAM_SECRET`
Debe responder `{"ok":true,...}`. Listo — escríbele "ayuda" a tu bot.

## Qué le puedes decir
- `buenos días` → historia del día (rota 4 variantes, nunca repite)
- `canción del día: Nights - Frank Ocean`
- `¿qué subo hoy?` → sugiere según tu semana real en Notion
- `guion sobre [tema]` → lo genera el repo y aparece en Notion en ~3 min
- `historia` / `encuesta` → idea de historia para hoy
- cualquier otra cosa → chat con tu asistente de contenido

## Cambiar de IA después
En `wrangler.toml`: `LLM_PROVIDER`, `MODEL_LIGHT/HEAVY` y el secret `LLM_API_KEY`.
(Para Claude/OpenAI hay que agregar su adapter en `llamarLLM` — ~15 líneas.)
```

- [ ] **Step 6: Commit**

```bash
git add telegram-bot/worker.js telegram-bot/README.md telegram-bot/test.mjs
git commit -m "feat(telegram): integraciones LLM/Notion/GitHub/KV, /setup y README de 10 min

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
