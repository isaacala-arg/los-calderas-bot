from unittest.mock import MagicMock
from src.models import Script
from src.outputs import notion_writer as nw


def _make_script():
    return Script(
        title="Semana sin tocar el volante",
        topic_context="FSD en CDMX, prueba real",
        hook="No manches... llevo cinco días sin tocar esto",
        body="Todo empezó el lunes...",
        cta="Guarda esto para cuando alguien te diga que los eléctricos no sirven",
        visual_idea="Tú en asiento trasero leyendo, FSD activo, volante girando solo",
        hashtags_tiktok=["#Tesla", "#FSD"],
        hashtags_reels=["#Tesla"],
        hashtags_shorts=["#Tesla"],
        script_type="trend",
    )


def test_write_script_calls_notion_and_returns_url(mocker):
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/page123"}
    mocker.patch("notion_client.Client", return_value=mock_notion)
    nw._notion = mock_notion

    url = nw.write_script(_make_script())

    assert url == "https://notion.so/page123"
    mock_notion.pages.create.assert_called_once()
    call_kwargs = mock_notion.pages.create.call_args[1]
    assert "children" in call_kwargs
    assert len(call_kwargs["children"]) > 0
