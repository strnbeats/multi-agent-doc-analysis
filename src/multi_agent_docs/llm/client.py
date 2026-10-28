from functools import lru_cache
from typing import Protocol

from gigachat import GigaChat

from ..config import Settings
from ..errors import LLMError
from ..models import LLMAnswer, TokenCount


class LLMClient(Protocol):
    def ask(self, prompt: str) -> LLMAnswer:
        """Отправить prompt в реализацию языковой модели."""
        ...

    def count_tokens(self, text: str) -> int:
        """Посчитать токены в реализации языковой модели."""
        ...


class GigaChatClient:
    def __init__(self, settings: Settings):
        """Настроить SDK GigaChat из параметров приложения."""
        self.model = settings.gigachat_model
        try:
            self._client = GigaChat(
                credentials=settings.gigachat_credentials,
                scope=settings.gigachat_scope,
                model=settings.gigachat_model,
                verify_ssl_certs=settings.gigachat_verify_ssl,
            )
        except Exception as error:
            raise LLMError("Не удалось настроить подключение к GigaChat") from error

    def ask(self, prompt: str) -> LLMAnswer:
        """Отправить prompt и вернуть текст вместе со статистикой токенов."""
        try:
            response = self._client.chat(prompt)
            return LLMAnswer(
                content=response.choices[0].message.content,
                usage=TokenCount(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                ),
            )
        except Exception as error:
            raise LLMError() from error

    def count_tokens(self, text: str) -> int:
        """Получить точное число токенов текста через GigaChat API."""
        try:
            result = self._client.tokens_count([text], model=self.model)
            return result[0].tokens
        except Exception as error:
            raise LLMError("Не удалось определить размер документа") from error


@lru_cache(maxsize=1)
def get_default_client() -> GigaChatClient:
    """Вернуть один лениво созданный реальный клиент GigaChat."""
    return GigaChatClient(Settings.from_env())
