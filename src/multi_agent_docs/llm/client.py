from dotenv import load_dotenv
from gigachat import GigaChat

load_dotenv()

giga = GigaChat(
    credentials=None,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-3-Ultra",
    verify_ssl_certs=False,
)


total_input_tokens = 0
total_output_tokens = 0
total_tokens = 0


def count_tokens(text: str) -> int:
    result = giga.tokens_count(
        [text],
        model="GigaChat-3-Ultra"
    )

    return result[0].tokens


def ask_llm(prompt: str, agent_name: str) -> str:
    global total_input_tokens
    global total_output_tokens
    global total_tokens

    response = giga.chat(prompt)

    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    request_total = response.usage.total_tokens

    total_input_tokens += input_tokens
    total_output_tokens += output_tokens
    total_tokens += request_total

    print(
        f"[{agent_name}] "
        f"input: {input_tokens} | "
        f"output: {output_tokens} | "
        f"total: {request_total}"
    )

    return response.choices[0].message.content