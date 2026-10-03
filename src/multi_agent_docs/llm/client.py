from dotenv import load_dotenv
from gigachat import GigaChat

load_dotenv()

giga = GigaChat(
    credentials=None,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-3-Ultra",
    verify_ssl_certs=False,
)


def ask_llm(prompt: str) -> str:
    response = giga.chat(prompt)

    return response.choices[0].message.content


def count_tokens(text: str) -> int:
    result = giga.tokens_count(
        [text],
        model="GigaChat-3-Ultra"
    )

    return result[0].tokens


if __name__ == "__main__":
    text = "Привет! Это тестовый текст для подсчёта токенов."

    print("Количество токенов:", count_tokens(text))