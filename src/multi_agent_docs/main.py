from ingestion.loader import load_document

text = load_document("data/raw/load.pdf")

print(text)