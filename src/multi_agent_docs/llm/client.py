from dotenv import load_dotenv
from gigachat import GigaChat

load_dotenv()

total_input_tokens = 0

giga = GigaChat(
    credentials=None,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-3-Ultra",
    verify_ssl_certs=False,
)


def count_tokens(text: str) -> int:
    result = giga.tokens_count(
        [text],
        model="GigaChat-3-Ultra"
    )

    return result[0].tokens


def ask_llm(prompt: str) -> str:
    global total_input_tokens

    tokens = count_tokens(prompt)

    total_input_tokens += tokens

    print(f"[LLM] Входных токенов: {tokens}")

    response = giga.chat(prompt)

    return response.choices[0].message.content