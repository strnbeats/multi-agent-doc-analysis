import argparse
import json
import sys
from pathlib import Path

# Позволяет запускать скрипт из корня проекта без установки пакета.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from multi_agent_docs.agents.fact_checker import fact_checker
from multi_agent_docs.llm.client import get_default_client
from multi_agent_docs.models import TokenUsage


SCENARIOS = {
    1: {
        "name": "Точное подтверждение",
        "source_text": """
ООО «Вектор» основано в 2018 году.
Компания занимается разработкой программного обеспечения.
В 2023 году штат организации составлял 45 сотрудников.
""".strip(),
        "analysis": """
ООО «Вектор» было основано в 2018 году.
Основным направлением деятельности компании является разработка
программного обеспечения.
В 2023 году в организации работало 45 человек.
""".strip(),
        "summary": """
Компания основана в 2018 году и занимается разработкой ПО.
В 2023 году её штат составлял 45 сотрудников.
""".strip(),
    },
    2: {
        "name": "Прямое противоречие",
        "source_text": """
ООО «Вектор» основано в 2018 году.
В 2023 году выручка компании составила 12 миллионов рублей.
""".strip(),
        "analysis": """
ООО «Вектор» основано в 2018 году.
В 2023 году выручка компании составила 20 миллионов рублей.
""".strip(),
        "summary": """
Выручка компании за 2023 год составила 20 миллионов рублей.
""".strip(),
    },
    3: {
        "name": "Недостаточно данных",
        "source_text": """
ООО «Вектор» занимается разработкой программного обеспечения.
Компания была основана в 2018 году.
""".strip(),
        "analysis": """
ООО «Вектор» занимается разработкой программного обеспечения.
Главный офис компании находится в Москве.
В компании работает 120 сотрудников.
""".strip(),
        "summary": """
Компания основана в 2018 году и имеет офис в Москве.
""".strip(),
    },
    4: {
        "name": "Частичное подтверждение",
        "source_text": """
ООО «Вектор» заключило договор с компанией «Альфа».
Стоимость договора составляет 10 миллионов рублей.
""".strip(),
        "analysis": """
ООО «Вектор» заключило договор с компанией «Альфа»
на сумму 10 миллионов рублей в марте 2025 года.
""".strip(),
        "summary": """
Компания заключила договор на 10 миллионов рублей в марте 2025 года.
""".strip(),
    },
    5: {
        "name": "Противоречие внутри источника",
        "source_text": """
В первом разделе документа указано:
«Договор с компанией Альфа был заключён 10 марта 2025 года».

В третьем разделе того же документа указано:
«Договор с компанией Альфа был заключён 15 марта 2025 года».
""".strip(),
        "analysis": """
Договор с компанией «Альфа» был заключён 10 марта 2025 года.
""".strip(),
        "summary": """
Договор с компанией «Альфа» был заключён 10 марта 2025 года.
""".strip(),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Локальная проверка Fact Checker на настоящем GigaChat."
    )
    parser.add_argument(
        "scenario",
        type=int,
        nargs="?",
        default=1,
        choices=SCENARIOS.keys(),
        help="Номер сценария от 1 до 5. По умолчанию: 1.",
    )
    args = parser.parse_args()

    scenario = SCENARIOS[args.scenario]

    print("=" * 70)
    print(f"FACT CHECKER — СЦЕНАРИЙ {args.scenario}")
    print(scenario["name"])
    print("=" * 70)

    print("\nПодключение к GigaChat...")
    llm = get_default_client()

    state = {
        "text": scenario["source_text"],
        "analysis": scenario["analysis"],
        "summary": scenario["summary"],
        "llm": llm,
        "token_usage": TokenUsage(),
    }

    print("Запуск Fact Checker...\n")

    result = fact_checker(state)

    print("=" * 70)
    print("РЕЗУЛЬТАТ FACT CHECKER")
    print("=" * 70)

    print(
        json.dumps(
            result["fact_check"],
            ensure_ascii=False,
            indent=2,
        )
    )

    usage = result["token_usage"]

    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()

    print("\n" + "=" * 70)
    print("РАСХОД ТОКЕНОВ")
    print("=" * 70)
    print(json.dumps(usage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()