from ingestion.loader import load_pdf

text = load_pdf("data/raw/load.pdf")

print(text[:1000])
print("Символов:", len(text))#временная проверка, чтобы убедиться, что текст загружен корректно