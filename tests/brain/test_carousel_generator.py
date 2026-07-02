import json
from src.brain import carousel_generator as cg


_FAKE = json.dumps({
    "title": "Semana en tech: lo que pasó y por qué importa",
    "slides": [
        {"titulo": "Portada: 3 noticias que sí te afectan", "bullets": []},
        {"titulo": "Apple libera X", "bullets": ["Qué pasó", "Por qué te importa"]},
        {"titulo": "Cierre", "bullets": ["La próxima entrega el viernes"]},
    ],
    "caption": "Lo que pasó esta semana en tech, sin humo.",
    "hashtags": ["#techtok", "#tecnologia"],
})


def _mock_heavy(mocker):
    resp = mocker.MagicMock()
    resp.text = _FAKE
    return mocker.patch("src.brain.llm_client.heavy", return_value=resp)


def test_semana_tech_usa_search_y_parsea(mocker):
    mock = _mock_heavy(mocker)
    c = cg.generate_semana_tech()
    assert mock.call_args[1]["search"] is True
    assert c.carousel_type == "semana_tech"
    assert len(c.slides) == 3
    assert c.slides[1]["bullets"] == ["Qué pasó", "Por qué te importa"]


def test_prompt_semana_tech_exige_verificacion(mocker):
    mock = _mock_heavy(mocker)
    cg.generate_semana_tech()
    prompt = mock.call_args[0][0]
    assert "últimos 7 días" in prompt
    assert "NO VERIFICADO" in prompt or "no la incluyas" in prompt


def test_carousel_tema_toma_del_banco(mocker):
    _mock_heavy(mocker)
    c = cg.generate_carousel_tema()
    assert c.carousel_type == "tema"
    assert len(cg.CAROUSEL_TOPICS) >= 4
