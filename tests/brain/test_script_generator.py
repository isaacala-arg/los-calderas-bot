import json
from datetime import datetime, timezone
from src.models import Article
from src.brain import script_generator as sg
from src.brain import gemini_client


def _make_article():
    return Article(
        title="Tesla FSD aprobado en México",
        url="https://example.com",
        summary="Tesla anunció que FSD estará disponible en México...",
        source="Electrek",
        published=datetime.now(timezone.utc),
    )


def _mock_script_json(script_type="trend"):
    return json.dumps({
        "title": "Cargo el Tesla en plazas",
        "topic_context": "Cuánto cuesta cargar el Caldermóvil en CDMX",
        "hook": "Llevo meses cargando el Tesla de mi papá",
        "body": "Todos me preguntan cuánto sube el recibo de luz...",
        "cta": "Guarda esto para cuando alguien jure que un eléctrico te deja en quiebra",
        "spot": "En la plaza, junto al Tesla conectado al cargador",
        "como_grabar": "Cel en el tripie + DJI Mic. Una sola toma señalando el cargador",
        "puntos": ["La duda real del recibo", "No en casa, en plazas", "Remate del súper"],
        "arranque": "Señalas el cargador y dices: 'Llevo meses cargando el Tesla de mi papá...'",
        "hashtags_tiktok": ["#Tesla", "#FSD", "#Mexico"],
        "hashtags_reels": ["#Tesla", "#AutosElectricos"],
        "hashtags_shorts": ["#Tesla", "#Mexico"],
        "script_type": script_type,
    })


def _patch_client(mocker, tmp_path, script_type="trend"):
    voice_file = tmp_path / "los-calderas-voice.md"
    voice_file.write_text("# Voz del canal\nTono casual mexicano.")
    mocker.patch("src.brain.script_generator.VOICE_GUIDE_PATH", str(voice_file))
    sg._file_cache = {}  # limpiar cache de archivos entre tests
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.return_value.text = _mock_script_json(script_type)
    gemini_client._client = mock_client
    return mock_client


def test_generate_trend_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "trend")
    script = sg.generate(_make_article(), script_type="trend")
    assert script.hook == "Llevo meses cargando el Tesla de mi papá"
    assert script.script_type == "trend"
    assert len(script.hashtags_tiktok) > 0
    assert script.spot != ""
    assert script.arranque != ""
    assert isinstance(script.puntos, list) and len(script.puntos) > 0


def test_generate_uses_pro_model(mocker, tmp_path):
    mock = _patch_client(mocker, tmp_path, "howto")
    sg.generate(_make_article(), script_type="howto")
    kwargs = mock.models.generate_content.call_args[1]
    assert kwargs["model"] == gemini_client.MODEL_PRO


def test_generate_howto_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "howto")
    script = sg.generate_howto()
    assert script is not None
    assert script.hook != ""
    assert script.script_type == "howto"


def test_generate_lifestyle_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "lifestyle")
    script = sg.generate_lifestyle()
    assert script.script_type == "lifestyle"
    assert script.como_grabar != ""


def test_generate_opinion_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "opinion")
    script = sg.generate_opinion()
    assert script.script_type == "opinion"


def test_generate_tech_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "tech")
    script = sg.generate_tech()
    assert script.script_type == "tech"
    assert script.hook != ""


def test_generate_fsd_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "fsd")
    script = sg.generate_fsd()
    assert script.script_type == "fsd"
    assert script.hook != ""


def test_generate_evergreen_returns_script(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "howto")
    script = sg.generate_evergreen()
    assert script is not None
    assert script.hook != ""


def test_append_avoid_hooks_adds_block():
    out = sg.append_avoid_hooks("BASE", ["Gancho uno", "Gancho dos"])
    assert "BASE" in out
    assert "Gancho uno" in out and "Gancho dos" in out
    assert "GANCHOS YA GENERADOS HOY" in out


def test_append_avoid_hooks_empty_returns_same():
    assert sg.append_avoid_hooks("BASE", []) == "BASE"
    assert sg.append_avoid_hooks("", [None, ""]) == ""


def test_creatividad_y_anticopia_en_prompt(mocker, tmp_path):
    _patch_client(mocker, tmp_path, "opinion")
    prompt = sg._build_prompt("opinion", "tema", "ctx", "")
    assert "CREATIVIDAD" in prompt
    assert "ANTI-COPIA" in prompt
    assert "nambre" in prompt.lower()  # la regla que lo prohíbe como muletilla


def test_contexto_actual_injected_into_prompt(mocker, tmp_path):
    mock = _patch_client(mocker, tmp_path, "howto")
    mocker.patch("src.brain.script_generator.CONTEXTO_ACTUAL_PATH", str(tmp_path / "ctx.md"))
    (tmp_path / "ctx.md").write_text("VACACIONES hasta el 15 de agosto. NO menciones la escuela.")
    sg._file_cache = {}
    # re-patch voice after cache clear
    voice_file = tmp_path / "los-calderas-voice.md"
    mocker.patch("src.brain.script_generator.VOICE_GUIDE_PATH", str(voice_file))
    sg.generate_howto()
    prompt = mock.models.generate_content.call_args[1]["contents"]
    assert "VACACIONES hasta el 15 de agosto" in prompt
