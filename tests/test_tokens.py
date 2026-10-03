from multi_agent_docs.ingestion.loader import load_document
from multi_agent_docs.llm.client import count_tokens


file_path = "data/raw/load.pdf"

text = load_document(file_path)

tokens = count_tokens(text)

print("=== TOKEN TEST ===")
print("Символов:", len(text))
print("Токенов:", tokens)
print("Примерно символов на токен:", round(len(text) / tokens, 2))