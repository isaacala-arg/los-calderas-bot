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


def _mock_script_json(script_type="trend"):
    return json.dumps({
        "title": "Semana sin tocar el volante",
        "topic_context": "FSD en CDMX, prueba real de 5 días",
        "hook": "No manches... llevo cinco días sin tocar esto",
        "body": "Todo empezó el lunes cuando decidí activar el FSD...",
        "cta": "Guarda esto para cuando alguien te diga que los eléctricos no sirven en México",
        "visual_idea": "Cámara fija desde asiento trasero. Tú leyendo un libro. El volante girando solo.",
        "filming_tips": ["Empieza con el libro en el asiento trasero, sin hablar, 2 segundos", "Muestra la pantalla del carro al dar el dato"],
        "hashtags_tiktok": ["#Tesla", "#FSD", "#AutosElectricos", "#Mexico", "#TeslaMexico"],
        "hashtags_reels": ["#Tesla", "#FSD", "#AutosElectricosMexico"],
        "hashtags_shorts": ["#Tesla", "#FSD", "#Mexico"],
        "script_type": script_type,
    })


def _patch_client(mocker, tmp_path, script_type="trend"):
    voice_file = tmp_path / "los-calderas-voice.md"
    voice_file.write_text("# Voz del canal\nTono casual mexicano.")
    mocker.patch("src.brain.script_generator.VOICE_GUIDE_PATH", str(voice_file))
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.return_value.text = _mock_script_json(script_type)
    sg._client = mock_client
    return mock_client


def test_generate_trend_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "trend")
    script = sg.generate(_make_article(), script_type="trend")
    assert script.hook == "No manches... llevo cinco días sin tocar esto"
    assert script.script_type == "trend"
    assert len(script.hashtags_tiktok) > 0
    assert script.visual_idea != ""
    assert isinstance(script.filming_tips, list)


def test_generate_howto_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "howto")
    script = sg.generate_howto()
    assert script is not None
    assert script.hook != ""
    assert script.script_type == "howto"


def test_generate_lifestyle_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "lifestyle")
    script = sg.generate_lifestyle()
    assert script is not None
    assert script.hook != ""
    assert script.script_type == "lifestyle"


def test_generate_opinion_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "opinion")
    script = sg.generate_opinion()
    assert script is not None
    assert script.hook != ""
    assert script.script_type == "opinion"


def test_generate_evergreen_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "howto")
    script = sg.generate_evergreen()
    assert script is not None
    assert script.hook != ""
