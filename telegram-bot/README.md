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
