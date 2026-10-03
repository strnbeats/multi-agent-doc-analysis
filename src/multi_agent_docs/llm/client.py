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


if __name__ == "__main__":
    answer = ask_llm("Привет! Кто ты? Ответь коротко.")

    print(answer)