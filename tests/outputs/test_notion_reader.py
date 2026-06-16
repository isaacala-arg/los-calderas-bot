from unittest.mock import MagicMock
import src.outputs.notion_reader as nr


def _make_page(title: str, tipo: str = "trend", estado: str = "Pendiente", page_id: str = "page-1"):
    return {
        "id": page_id,
        "properties": {
            "Título": {"title": [{"text": {"content": title}}]},
            "Tipo": {"select": {"name": tipo}},
            "Estado": {"select": {"name": estado}},
            "Fecha": {"date": {"start": "2026-06-01"}},
        },
    }


def _make_blocks(hook_text: str) -> dict:
    return {
        "results": [
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Contexto del tema"}}]},
            },
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": "contexto..."}}]},
            },
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "🎣 Gancho (0–3 seg)"}}]},
            },
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": hook_text}}]},
            },
        ]
    }


def test_get_recent_titles_returns_list():
    mock_client = MagicMock()
    mock_client.databases.query.return_value = {
        "results": [
            _make_page("Cuánto cuesta cargar el Tesla"),
            _make_page("El Olinia del gobierno"),
        ]
    }
    nr._notion = mock_client

    titles = nr.get_recent_titles(days=45)

    assert "Cuánto cuesta cargar el Tesla" in titles
    assert "El Olinia del gobierno" in titles
    assert len(titles) == 2


def test_get_recent_titles_returns_empty_on_error():
    nr._notion = None
    original = nr._get_notion

    def _raise():
        raise Exception("API error")

    nr._get_notion = _raise
    try:
        titles = nr.get_recent_titles()
        assert titles == []
    finally:
        nr._get_notion = original


def test_get_approved_examples_returns_examples():
    mock_client = MagicMock()
    mock_client.databases.query.return_value = {
        "results": [
            _make_page("Mi Tesla vs gasolina", tipo="howto", estado="Publicado", page_id="abc")
        ]
    }
    mock_client.blocks.children.list.return_value = _make_blocks("Oigan, acabo de calcular cuánto me cuesta")
    nr._notion = mock_client

    examples = nr.get_approved_examples(limit=2)

    assert len(examples) == 1
    assert examples[0]["title"] == "Mi Tesla vs gasolina"
    assert examples[0]["type"] == "howto"
    assert "calcular" in examples[0]["hook"]


def test_get_approved_examples_skips_page_with_no_title():
    mock_client = MagicMock()
    mock_client.databases.query.return_value = {
        "results": [
            {
                "id": "page-empty",
                "properties": {
                    "Título": {"title": []},
                    "Tipo": {"select": None},
                    "Estado": {"select": {"name": "Publicado"}},
                },
            }
        ]
    }
    mock_client.blocks.children.list.return_value = {"results": []}
    nr._notion = mock_client

    examples = nr.get_approved_examples()

    assert examples == []


def test_get_approved_examples_returns_empty_on_error():
    nr._notion = None
    original = nr._get_notion

    def _raise():
        raise Exception("API error")

    nr._get_notion = _raise
    try:
        examples = nr.get_approved_examples()
        assert examples == []
    finally:
        nr._get_notion = original


def test_get_hook_from_page_returns_text():
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = _make_blocks("Nambre... acabo de ver algo")
    nr._notion = mock_client

    hook = nr._get_hook_from_page("page-123")

    assert hook == "Nambre... acabo de ver algo"


def test_get_hook_from_page_returns_empty_if_no_gancho_heading():
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Contexto del tema"}}]},
            },
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": "algo"}}]},
            },
        ]
    }
    nr._notion = mock_client

    hook = nr._get_hook_from_page("page-123")

    assert hook == ""
