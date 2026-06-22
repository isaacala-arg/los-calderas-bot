from src.brain import gemini_client


def test_call_passes_args_to_client(mocker):
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.return_value.text = "ok"
    gemini_client._client = mock_client

    result = gemini_client.call("hola", config=None)

    assert result.text == "ok"
    mock_client.models.generate_content.assert_called_once()
    kwargs = mock_client.models.generate_content.call_args[1]
    assert kwargs["contents"] == "hola"
    assert kwargs["model"] == gemini_client.MODEL


def test_call_uses_search_config_when_passed(mocker):
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.return_value.text = "ok"
    gemini_client._client = mock_client

    gemini_client.call("hola", config=gemini_client.SEARCH_CONFIG)

    kwargs = mock_client.models.generate_content.call_args[1]
    assert kwargs["config"] is gemini_client.SEARCH_CONFIG
