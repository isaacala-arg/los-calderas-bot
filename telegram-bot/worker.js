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
  const pideGuion =
    /^\s*(guion|guión)\s+(sobre|de|del)\s+\S/.test(t) ||
    /(hazme|genera|genérame|crea|créame|quiero)\s+(un\s+)?(guion|guión)/.test(t);
  if (pideGuion) return { tipo: "guion", arg: extraerTema(texto) };
  if (t.includes("historia") || t.includes("encuesta")) return { tipo: "historia", arg: texto };
  return { tipo: "chat", arg: texto };
}

export function extraerTema(texto) {
  const t = (texto || "").trim();
  // Patrón 1: "guion sobre/de/del <tema>"
  const m1 = t.match(/(?:guion|guión)\s+(?:sobre|de|del)\s+(\S.*)/i);
  if (m1) return m1[1].trim();
  // Patrón 2: "hazme/genera/... (un) guion (sobre/de/del <tema>)"
  const m2 = t.match(/(?:hazme|genera|genérame|crea|créame|quiero)\s+(?:un\s+)?(?:guion|guión)(?:\s+(?:sobre|de|del)\s+(\S.*))?/i);
  if (m2) return (m2[1] || "").trim();
  return "";
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
