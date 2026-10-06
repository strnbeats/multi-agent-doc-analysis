PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: help install migrate run run-mock test test-api postman-check check

help:
	@echo "make install       - создать .venv и установить зависимости"
	@echo "make migrate       - применить Alembic-миграции"
	@echo "make run           - запустить API с реальным GigaChat"
	@echo "make run-mock      - запустить API с локальным mock LLM"
	@echo "make test          - запустить все тесты"
	@echo "make test-api      - запустить только сквозные API-тесты"
	@echo "make postman-check - проверить JSON Postman-коллекции"
	@echo "make check         - выполнить все локальные проверки"

install:
	python3 -m venv .venv
	$(PIP) install -e '.[dev]'

migrate:
	PYTHON_BIN=$(PYTHON) ./cmd/migrate.sh

run:
	PYTHON_BIN=$(PYTHON) ./cmd/run.sh real

run-mock:
	PYTHON_BIN=$(PYTHON) ./cmd/run.sh mock

test:
	PYTHON_BIN=$(PYTHON) ./cmd/test.sh

test-api:
	$(PYTHON) -m pytest tests/test_api.py tests/test_api_mock_e2e.py

postman-check:
	$(PYTHON) -m json.tool postman/document-analysis.postman_collection.json >/dev/null
	$(PYTHON) -m json.tool postman/local.postman_environment.json >/dev/null

check: test postman-check
