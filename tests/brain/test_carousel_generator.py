import json
from src.brain import carousel_generator as cg


_FAKE = json.dumps({
    "title": "Semana en tech: lo que pasó y por qué importa",
    "slides": [
        {"titulo": "Portada: 3 noticias que sí te afectan", "bullets": []},
        {"titulo": "Apple libera X", "bullets": ["Qué pasó", "Por qué te importa"], "fuente": "The Verge — 2026-07-01"},
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
    assert "descártala" in prompt or "no la incluyas" in prompt


def test_prompt_semana_tech_ventana_fechas_y_fuentes(mocker):
    """Feedback de Isaac: fechas reales verificadas, fuentes citadas,
    prioridad MX->LATAM->mundo, y búsqueda amplia (no lo primero que salga)."""
    from datetime import date
    mock = _mock_heavy(mocker)
    cg.generate_semana_tech()
    prompt = mock.call_args[0][0]
    assert f"HOY es {date.today().isoformat()}" in prompt   # el modelo sabe qué día es
    assert "PROHIBIDA" in prompt                            # ventana dura de fechas
    assert "FUENTES" in prompt and "Reuters" in prompt      # fuentes confiables citadas
    assert "LATAM" in prompt and "MÉXICO" in prompt         # prioridad geográfica
    assert "10 noticias candidatas" in prompt               # búsqueda amplia
    assert "EN TENDENCIA" in prompt                         # tendencias


def test_parse_incluye_fuente(mocker):
    _mock_heavy(mocker)
    c = cg.generate_semana_tech()
    assert c.slides[1]["fuente"] == "The Verge — 2026-07-01"
    assert c.slides[0]["fuente"] == ""  # portada sin fuente


def test_carousel_tema_toma_del_banco(mocker):
    _mock_heavy(mocker)
    c = cg.generate_carousel_tema()
    assert c.carousel_type == "tema"
    assert len(cg.CAROUSEL_TOPICS) >= 4


def test_semana_tech_inmune_a_llaves_en_voice_guide(mocker):
    """Regresión: si voice_guide contiene {llaves}, NO debe lanzar KeyError."""
    mocker.patch(
        "src.brain.carousel_generator._load_voice_guide",
        return_value="guia con {llaves} y {script_type} raros",
    )
    mock = _mock_heavy(mocker)
    # No debe tronar
    cg.generate_semana_tech()
    prompt = mock.call_args[0][0]
    # El literal debe llegar intacto al LLM
    assert "{llaves}" in prompt
