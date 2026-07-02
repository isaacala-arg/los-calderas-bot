from unittest.mock import MagicMock
from src.models import Script, Carousel
from src.outputs import notion_writer as nw


def _make_script():
    return Script(
        title="Semana sin tocar el volante",
        topic_context="FSD en CDMX, prueba real",
        hook="No manches... llevo cinco días sin tocar esto",
        body="Todo empezó el lunes...",
        cta="Guarda esto para cuando alguien te diga que los eléctricos no sirven",
        spot="Manejando el Tesla con FSD activo",
        como_grabar="Cel en el tripie sobre el tablero + DJI Mic. Una toma.",
        puntos=["Muestra el volante girando solo", "Cuenta los 5 días", "Remata"],
        arranque="Volteas a cámara y dices: 'No manches, llevo cinco días sin tocar esto'",
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


def test_write_carousel_crea_pagina_ordenada(mocker):
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/carr1"}
    nw._notion = mock_notion

    c = Carousel(
        title="Semana en tech: 30 jun - 4 jul",
        slides=[
            {"titulo": "Portada", "bullets": []},
            {"titulo": "Noticia 1", "bullets": ["qué pasó", "por qué te importa"], "fuente": "Reuters — 2026-07-01"},
        ],
        caption="La semana sin humo.",
        hashtags=["#techtok"],
        carousel_type="semana_tech",
    )
    url = nw.write_carousel(c)

    assert url == "https://notion.so/carr1"
    kwargs = mock_notion.pages.create.call_args[1]
    titulo = kwargs["properties"]["Título"]["title"][0]["text"]["content"]
    assert titulo == "Carrusel: Semana en tech: 30 jun - 4 jul"
    assert kwargs["properties"]["Tipo"]["select"]["name"] == "carrusel"
    contenido = str(kwargs["children"])
    assert "Slide 1" in contenido and "Slide 2" in contenido
    assert "por qué te importa" in contenido
    assert "Fuente: Reuters — 2026-07-01" in contenido
