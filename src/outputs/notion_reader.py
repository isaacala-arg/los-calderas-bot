from datetime import date, timedelta

_notion = None


def _get_notion():
    global _notion
    if _notion is None:
        from notion_client import Client
        from src.config import settings
        _notion = Client(auth=settings.NOTION_API_TOKEN)
    return _notion


def get_recent_titles(days: int = 45) -> list[str]:
    """Return script titles from the last N days to avoid repeating topics."""
    try:
        from src.config import settings
        notion = _get_notion()
        since = (date.today() - timedelta(days=days)).isoformat()
        response = notion.databases.query(
            database_id=settings.NOTION_DATABASE_ID,
            filter={"property": "Fecha", "date": {"on_or_after": since}},
            page_size=50,
        )
        titles = []
        for page in response.get("results", []):
            parts = page["properties"].get("Título", {}).get("title", [])
            if parts:
                titles.append(parts[0]["text"]["content"])
        return titles
    except Exception:
        return []


def get_approved_examples(limit: int = 4) -> list[dict]:
    """Return approved/published scripts as style reference for the generator.

    Scripts where Estado != 'Pendiente' are considered approved by Isaac.
    Each entry has: title, type, hook (the edited hook text from the page).
    """
    try:
        from src.config import settings
        notion = _get_notion()
        response = notion.databases.query(
            database_id=settings.NOTION_DATABASE_ID,
            filter={"property": "Estado", "select": {"does_not_equal": "Pendiente"}},
            sorts=[{"property": "Fecha", "direction": "descending"}],
            page_size=limit,
        )
        examples = []
        for page in response.get("results", []):
            title_parts = page["properties"].get("Título", {}).get("title", [])
            title = title_parts[0]["text"]["content"] if title_parts else ""
            tipo_sel = page["properties"].get("Tipo", {}).get("select")
            script_type = tipo_sel["name"] if tipo_sel else ""
            hook = _get_hook_from_page(page["id"])
            if title:
                examples.append({"title": title, "type": script_type, "hook": hook})
        return examples
    except Exception:
        return []


def _get_hook_from_page(page_id: str) -> str:
    """Extract the (possibly edited) hook text from a Notion page."""
    try:
        notion = _get_notion()
        results = notion.blocks.children.list(block_id=page_id).get("results", [])
        take_next = False
        for block in results:
            btype = block.get("type")
            if take_next and btype == "paragraph":
                parts = block["paragraph"].get("rich_text", [])
                return parts[0]["text"]["content"] if parts else ""
            if btype == "heading_2":
                parts = block["heading_2"].get("rich_text", [])
                heading = parts[0]["text"]["content"] if parts else ""
                if "Gancho" in heading:
                    take_next = True
        return ""
    except Exception:
        return ""
