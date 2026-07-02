from src.brain import llm_client, gemini_client


def test_light_uses_flash_sin_search(mocker):
    mock = mocker.patch("src.brain.gemini_client.call", return_value="r")
    llm_client.light("hola")
    kwargs = mock.call_args[1]
    assert kwargs["model"] == gemini_client.MODEL_FLASH
    assert kwargs["config"] is None


def test_heavy_uses_pro_con_search(mocker):
    mock = mocker.patch("src.brain.gemini_client.call", return_value="r")
    llm_client.heavy("hola", search=True)
    kwargs = mock.call_args[1]
    assert kwargs["model"] == gemini_client.MODEL_PRO
    assert kwargs["config"] is gemini_client.SEARCH_CONFIG


def test_proveedor_desconocido_truena(mocker):
    mocker.patch.object(llm_client, "PROVIDER", "openai")
    try:
        llm_client.light("hola")
        assert False, "debió tronar"
    except NotImplementedError as e:
        assert "openai" in str(e)
