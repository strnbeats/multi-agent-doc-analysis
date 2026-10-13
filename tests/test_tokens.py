from unittest.mock import patch

from multi_agent_docs.llm.client import count_tokens


def test_count_tokens_returns_token_count():
    with patch("multi_agent_docs.llm.client.giga.tokens_count") as mock_count:
        mock_count.return_value = [
            type("TokenCount", (), {"tokens": 42})()
        ]

        result = count_tokens("Пример текста для проверки")

    assert result == 42
    mock_count.assert_called_once_with(
        ["Пример текста для проверки"],
        model="GigaChat-3-Ultra",
    )