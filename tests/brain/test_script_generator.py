import json
from datetime import datetime
from src.models import Article
from src.brain import script_generator as sg


def _make_article():
    return Article(
        title="Tesla FSD aprobado en México",
        url="https://example.com",
        summary="Tesla anunció que FSD estará disponible en México...",
        source="Electrek",
        published=datetime.utcnow(),
    )


def _mock_script_json():
    return json.dumps({
        "title": "Semana sin tocar el volante",
        "topic_context": "FSD en CDMX, prueba real de 5 días",
        "hook": "No manches... llevo cinco días sin tocar esto",
        "body": "Todo empezó el lunes cuando decidí activar el FSD...",
        "cta": "Guarda esto para cuando alguien te diga que los eléctricos no sirven en México",
        "visual_idea": "Cámara fija desde asiento trasero. Tú leyendo un libro. El volante girando solo.",
        "filming_tips": ["Empieza con el libro en el asiento trasero, sin hablar, 2 segundos", "Cuando dices el dato del precio, muestra la pantalla del carro"],
        "hashtags_tiktok": ["#Tesla", "#FSD", "#AutosElectricos", "#Mexico", "#TeslaMexico"],
        "hashtags_reels": ["#Tesla", "#FSD", "#AutosElectricosMexico"],
        "hashtags_shorts": ["#Tesla", "#FSD", "#Mexico"],
        "script_type": "trend",
    })


def test_generate_returns_script(mocker, tmp_path):
    voice_file = tmp_path / "los-calderas-voice.md"
    voice_file.write_text("# Voz del canal\nTono casual mexicano.")

    mocker.patch("src.brain.script_generator.VOICE_GUIDE_PATH", str(voice_file))

    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.return_value.text = _mock_script_json()
    sg._client = mock_client

    script = sg.generate(_make_article())

    assert script.hook == "No manches... llevo cinco días sin tocar esto"
    assert script.script_type == "trend"
    assert len(script.hashtags_tiktok) > 0
    assert script.visual_idea != ""


def test_generate_evergreen_returns_script(mocker, tmp_path):
    voice_file = tmp_path / "los-calderas-voice.md"
    voice_file.write_text("# Voz del canal\nTono casual mexicano.")

    mocker.patch("src.brain.script_generator.VOICE_GUIDE_PATH", str(voice_file))

    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.return_value.text = _mock_script_json()
    sg._client = mock_client

    script = sg.generate_evergreen()

    assert script is not None
    assert script.hook != ""
