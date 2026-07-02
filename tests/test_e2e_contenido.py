"""E2E con mocks: un contenido de cada tipo pasa completo por generación → Notion.
(Historias diarias quedan para la Fase 2 — chatbot — según decisión de Isaac.)"""
import json
from unittest.mock import MagicMock
from src.brain import script_generator as sg
from src.brain import carousel_generator as cg
from src.outputs import notion_writer as nw


def _fake_script(script_type):
    return json.dumps({
        "title": "t", "topic_context": "c", "hook": "h", "body": "b" * 200, "cta": "cta",
        "spot": "s", "como_grabar": "cg", "puntos": ["p1"], "arranque": "a",
        "hashtags_tiktok": ["#x"], "hashtags_reels": [], "hashtags_shorts": [],
        "script_type": script_type,
    })


def _fake_carousel():
    return json.dumps({
        "title": "Semana en tech", "caption": "cap", "hashtags": ["#t"],
        "slides": [{"titulo": "Portada", "bullets": []}, {"titulo": "N1", "bullets": ["b"]}],
    })


def test_e2e_reel_hasta_notion(mocker, tmp_path):
    resp = mocker.MagicMock(); resp.text = _fake_script("howto")
    mocker.patch("src.brain.llm_client.heavy", return_value=resp)
    sg._file_cache = {}
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/x"}
    nw._notion = mock_notion

    script = sg.generate_howto()
    url = nw.write_script(script)
    assert url.startswith("https://notion.so/")
    assert mock_notion.pages.create.call_args[1]["properties"]["Tipo"]["select"]["name"] == "howto"


def test_e2e_vlog_hasta_notion(mocker):
    resp = mocker.MagicMock(); resp.text = _fake_script("vlog")
    mocker.patch("src.brain.llm_client.heavy", return_value=resp)
    sg._file_cache = {}
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/v"}
    nw._notion = mock_notion
    url = nw.write_script(sg.generate_vlog())
    assert url == "https://notion.so/v"


def test_e2e_carrusel_hasta_notion(mocker):
    resp = mocker.MagicMock(); resp.text = _fake_carousel()
    mocker.patch("src.brain.llm_client.heavy", return_value=resp)
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"url": "https://notion.so/c"}
    nw._notion = mock_notion
    url = nw.write_carousel(cg.generate_semana_tech())
    assert url == "https://notion.so/c"
