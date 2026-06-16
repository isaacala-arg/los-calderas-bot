from datetime import datetime, timezone
from notion_client import Client
from src.models import Script

_notion = None


def _get_notion():
    global _notion
    if _notion is None:
        from src.config import settings
        _notion = Client(auth=settings.NOTION_API_TOKEN)
    return _notion


def write_script(script: Script) -> str:
    from src.config import settings
    notion = _get_notion()
    response = notion.pages.create(
        parent={"database_id": settings.NOTION_DATABASE_ID},
        properties={
            "Título": {"title": [{"text": {"content": script.title}}]},
            "Tipo": {"select": {"name": script.script_type}},
            "Estado": {"select": {"name": "Pendiente"}},
            "Fecha": {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%d")}},
        },
        children=[
            _h2("Contexto del tema"),
            _p(script.topic_context),
            _h2("🎣 Gancho (0–3 seg)"),
            _p(script.hook),
            _h2("📖 Cuerpo (40–75 seg)"),
            _p(script.body),
            _h2("📣 Cierre / CTA"),
            _p(script.cta),
            _h2("🎬 Idea Visual"),
            _p(script.visual_idea),
            _h2("🎬 Consejos de grabación"),
            *[_bullet(tip) for tip in script.filming_tips],
            _h2("Hashtags"),
            _p(f"TikTok: {' '.join(script.hashtags_tiktok)}"),
            _p(f"Reels: {' '.join(script.hashtags_reels)}"),
            _p(f"Shorts: {' '.join(script.hashtags_shorts)}"),
            *_teleprompter_section(script),
        ],
    )
    return response["url"]


def _h2(text: str) -> dict:
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"text": {"content": text}}]},
    }


def _p(text: str) -> dict:
    # Notion hard limit: 2000 chars per rich_text content block
    text = str(text)[:2000]
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": text}}]},
    }


def _teleprompter_section(script) -> list:
    if script.script_type == "lifestyle":
        return [
            _h2("🎬 PLAN DE ESCENAS — improvisar en cámara"),
            _p(script.body),
        ]
    return [
        _h2("📱 TELEPROMPTER — copia y lee"),
        _p(f"{script.hook}\n\n{script.body}\n\n{script.cta}"),
    ]


def _bullet(text: str) -> dict:
    return {
        "object": "block", "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]},
    }
