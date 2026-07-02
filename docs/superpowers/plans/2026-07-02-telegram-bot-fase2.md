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

### Task 1: Worker con router de intents (funciones puras + plumbing Telegram, integraciones stub)

**Files:**
- Create: `telegram-bot/worker.js`
- Create: `telegram-bot/wrangler.toml`
- Test: `telegram-bot/test.mjs`

**Interfaces:**
- Produces (exportadas para test y para Task 2): `detectarIntent(texto) -> {tipo, arg}` con tipos `"ayuda"|"buenos_dias"|"cancion"|"que_subo"|"guion"|"historia"|"chat"`; `siguienteVariante(ultima, total) -> int` (aleatoria ≠ ultima); `extraerTema(texto) -> string`; `sugerirContenido(conteos, diaSemana) -> string` (conteos = objeto `{tipo: n}`); `formatearCancion(arg) -> string`; `BUENOS_DIAS` (array de 4 strings). Default export: `{ fetch(request, env) }`.
- Task 2 reemplaza los stubs `llamarLLM`, `consultarNotion`, `dispararGuion`, `leerEstado`, `guardarEstado`.

- [ ] **Step 1: Write the failing tests**

```javascript
// telegram-bot/test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  detectarIntent, siguienteVariante, extraerTema,
  sugerirContenido, formatearCancion, BUENOS_DIAS,
} from "./worker.js";

test("detectarIntent clasifica los comandos de Isaac", () => {
  assert.equal(detectarIntent("Buenos días").tipo, "buenos_dias");
  assert.equal(detectarIntent("/bd").tipo, "buenos_dias");
  assert.equal(detectarIntent("canción del día: Nights - Frank Ocean").tipo, "cancion");
  assert.equal(detectarIntent("¿qué subo hoy?").tipo, "que_subo");
  assert.equal(detectarIntent("que subo hoy").tipo, "que_subo");
  assert.equal(detectarIntent("guion sobre el nuevo BYD").tipo, "guion");
  assert.equal(detectarIntent("hazme un guión de los aranceles").tipo, "guion");
  assert.equal(detectarIntent("dame una historia para hoy").tipo, "historia");
  assert.equal(detectarIntent("/start").tipo, "ayuda");
  assert.equal(detectarIntent("oye y si grabo en la noche?").tipo, "chat");
});

test("extraerTema limpia el prefijo del comando", () => {
  assert.equal(extraerTema("guion sobre el nuevo BYD"), "el nuevo BYD");
  assert.equal(extraerTema("hazme un guión de los aranceles a China"), "los aranceles a China");
});

test("siguienteVariante nunca repite y respeta rango", () => {
  for (let i = 0; i < 50; i++) {
    const v = siguienteVariante(2, 4);
    assert.notEqual(v, 2);
    assert.ok(v >= 0 && v < 4);
  }
});

test("BUENOS_DIAS trae las 4 variantes de la spec", () => {
  assert.equal(BUENOS_DIAS.length, 4);
  assert.ok(BUENOS_DIAS.some((v) => v.includes("qué tal amanecieron")));
});

test("sugerirContenido: 2+ reels esta semana -> carrusel", () => {
  const s = sugerirContenido({ trend: 1, howto: 1, carrusel: 0 }, 3);
  assert.ok(s.toLowerCase().includes("carrusel"));
});

test("sugerirContenido: pocos reels -> sugiere reel del pilar menos usado", () => {
  const s = sugerirContenido({ trend: 1 }, 3);
  assert.ok(s.toLowerCase().includes("reel"));
});

test("formatearCancion con y sin canción", () => {
  assert.equal(
    formatearCancion("Nights - Frank Ocean"),
    "🎵 Canción del día: Nights — Frank Ocean"
  );
  assert.ok(formatearCancion("").includes("¿cuál canción?"));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test telegram-bot/`
Expected: FAIL — `Cannot find module ... worker.js`

- [ ] **Step 3: Write the worker (v1 con stubs)**

```javascript
// telegram-bot/worker.js
// Chatbot personal de Los Calderas en Telegram — Cloudflare Worker, sin dependencias.
// Seguridad: secret token de Telegram + allowlist de chat_id (solo Isaac).

export const BUENOS_DIAS = [
  "Buenos días 🤍 ¿qué tal amanecieron?",
  "Buenos días, hoy toca [entreno / chamba / grabar] — cuéntales qué sigue hoy",
  "Buenos días 🤍 Otro día más para intentarlo de nuevo. Vamos con todo.",
  "Buenos días a todos 🤍☀️",
];

const AYUDA = `Soy tu content manager de Los Calderas. Dime:
• "buenos días" — historia de buenos días (roto las 4 variantes)
• "canción del día: [nombre] - [artista]"
• "¿qué subo hoy?" — te sugiero según tu semana en Notion
• "guion sobre [tema]" — lo genero y te lo dejo en Notion (~3 min)
• "historia" / "encuesta" — idea para historia de hoy
• o platícame lo que sea (ideas, dudas de contenido)`;

export function detectarIntent(texto) {
  const t = (texto || "").trim().toLowerCase();
  if (t === "/start" || t === "/ayuda" || t === "ayuda") return { tipo: "ayuda", arg: "" };
  if (t === "/bd" || t.startsWith("buenos d") || t.startsWith("buenos di")) return { tipo: "buenos_dias", arg: "" };
  if (t.startsWith("canci") || t.startsWith("cancion") || t.includes("canción del día") || t.includes("cancion del dia") || t.startsWith("rola"))
    return { tipo: "cancion", arg: texto.split(":").slice(1).join(":").trim() };
  if (t.includes("que subo") || t.includes("qué subo")) return { tipo: "que_subo", arg: "" };
  if (/(guion|guión)/.test(t) && /(sobre|de |del )/.test(t)) return { tipo: "guion", arg: extraerTema(texto) };
  if (t.includes("historia") || t.includes("encuesta")) return { tipo: "historia", arg: texto };
  return { tipo: "chat", arg: texto };
}

export function extraerTema(texto) {
  return (texto || "")
    .replace(/^.*?(guion|guión)\s*(sobre|de|del)\s+/i, "")
    .trim();
}

export function siguienteVariante(ultima, total) {
  let v;
  do {
    v = Math.floor(Math.random() * total);
  } while (v === ultima && total > 1);
  return v;
}

const TIPOS_REEL = ["trend", "howto", "lifestyle", "opinion", "tech", "fsd", "vlog"];

export function sugerirContenido(conteos, diaSemana) {
  const reels = TIPOS_REEL.reduce((n, t) => n + (conteos[t] || 0), 0);
  const carruseles = conteos["carrusel"] || 0;
  if (reels >= 2 && carruseles === 0) {
    return "Esta semana ya llevas " + reels + " reels y ningún carrusel — hoy toca CARRUSEL. Revisa en Notion el más reciente con título \"Carrusel:\" y diséñalo en Canva.";
  }
  const pilares = ["tech", "howto", "lifestyle", "vlog", "opinion", "fsd", "trend"];
  const menosUsado = pilares.reduce((min, p) => ((conteos[p] || 0) < (conteos[min] || 0) ? p : min), pilares[0]);
  return "Hoy toca REEL del pilar \"" + menosUsado + "\" (es el que menos has usado esta semana). Revisa tus guiones Pendientes en Notion de ese tipo y graba el que más te late.";
}

export function formatearCancion(arg) {
  const limpio = (arg || "").trim();
  if (!limpio) return "¿cuál canción? Mándame: canción del día: [nombre] - [artista]";
  const [nombre, artista] = limpio.split(/\s*-\s*/);
  const cuerpo = artista ? `${nombre.trim()} — ${artista.trim()}` : limpio;
  return `🎵 Canción del día: ${cuerpo}`;
}

// ─── Integraciones (Task 2 las implementa; aquí stubs que fallan claro) ───────
async function llamarLLM(env, prompt, tier) { throw new Error("llamarLLM: pendiente Task 2"); }
async function consultarNotion(env) { throw new Error("consultarNotion: pendiente Task 2"); }
async function dispararGuion(env, tema) { throw new Error("dispararGuion: pendiente Task 2"); }
async function leerEstado(env, key) { return null; }
async function guardarEstado(env, key, valor) {}

// ─── Telegram plumbing ────────────────────────────────────────────────────────
async function responder(env, chatId, texto) {
  await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text: texto }),
  });
}

async function manejarMensaje(env, chatId, texto) {
  const { tipo, arg } = detectarIntent(texto);
  try {
    if (tipo === "ayuda") return responder(env, chatId, AYUDA);
    if (tipo === "buenos_dias") {
      const ultima = parseInt(await leerEstado(env, "lastBuenosDias"), 10);
      const v = siguienteVariante(Number.isInteger(ultima) ? ultima : -1, BUENOS_DIAS.length);
      await guardarEstado(env, "lastBuenosDias", String(v));
      return responder(env, chatId, BUENOS_DIAS[v]);
    }
    if (tipo === "cancion") return responder(env, chatId, formatearCancion(arg));
    if (tipo === "que_subo") {
      const conteos = await consultarNotion(env);
      return responder(env, chatId, sugerirContenido(conteos, new Date().getDay()));
    }
    if (tipo === "guion") {
      if (!arg) return responder(env, chatId, "¿guion sobre qué tema? Ej: guion sobre los aranceles a autos chinos");
      await dispararGuion(env, arg);
      return responder(env, chatId, `Va 🫡 — generando guion sobre "${arg}". En ~3 min te aparece en Notion como Pendiente.`);
    }
    if (tipo === "historia") {
      const idea = await llamarLLM(env, PROMPT_HISTORIA + "\nPetición de Isaac: " + arg, "light");
      return responder(env, chatId, idea);
    }
    const r = await llamarLLM(env, PROMPT_CHAT + "\nIsaac dice: " + texto, "light");
    return responder(env, chatId, r);
  } catch (e) {
    return responder(env, chatId, "Se me cayó el sistema 😅: " + e.message);
  }
}

const PROMPT_HISTORIA = `Eres el content manager de "Los Calderas" (Isaac: 20 años, ingeniero en formación, becario de tecnología, CDMX; Swift propio, Tesla del papá "el Caldermóvil"). Genera UNA idea de historia de Instagram para HOY: detrás de cámaras, encuesta u opción de pregunta a la audiencia. Máximo 1 pregunta. Formato: texto listo para poner en la historia + (si aplica) opciones de encuesta. Español CDMX, breve, sin "sígueme".`;

const PROMPT_CHAT = `Eres el asistente de contenido de Isaac ("Los Calderas": carros + tecnología, TikTok/Reels/Shorts; Swift propio, Tesla del papá "el Caldermóvil", Mini de la mamá — nunca digas "su Tesla" como si fuera de Isaac). Responde BREVE (máx 5 líneas), español mexicano CDMX, práctico y con humor ligero. Si pide un guion completo, dile que use: guion sobre [tema].`;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/webhook" && request.method === "POST") {
      if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.TELEGRAM_SECRET)
        return new Response("forbidden", { status: 403 });
      const update = await request.json();
      const msg = update.message || update.edited_message;
      if (msg && String(msg.chat.id) === String(env.ALLOWED_CHAT_ID) && msg.text)
        await manejarMensaje(env, msg.chat.id, msg.text);
      return new Response("ok"); // siempre 200 para que Telegram no reintente
    }
    return new Response("Los Calderas bot", { status: 200 });
  },
};
```

```toml
# telegram-bot/wrangler.toml
name = "los-calderas-telegram"
main = "worker.js"
compatibility_date = "2026-06-01"

[[kv_namespaces]]
binding = "ESTADO"
id = "REEMPLAZAR_CON_ID_DE_KV"   # se crea con: npx wrangler kv namespace create ESTADO

[vars]
LLM_PROVIDER = "gemini"
MODEL_LIGHT = "gemini-2.5-flash"
MODEL_HEAVY = "gemini-2.5-pro"
GITHUB_REPO = "isaacala-arg/los-calderas-bot"
# Secrets (npx wrangler secret put X): TELEGRAM_TOKEN, TELEGRAM_SECRET,
# ALLOWED_CHAT_ID, LLM_API_KEY, GITHUB_TOKEN, NOTION_API_TOKEN, NOTION_DATABASE_ID
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test telegram-bot/`
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add telegram-bot/worker.js telegram-bot/wrangler.toml telegram-bot/test.mjs
git commit -m "feat(telegram): worker con router de intents y plumbing seguro

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

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
