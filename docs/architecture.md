# Архитектура backend MVP

## Слои

```text
HTTP / FastAPI
      ↓
AnalysisService + однопоточная очередь
      ├──→ runner → LangGraph → agents → GigaChat
      ↓
DocumentRepository
      ↓
SQLite
```

FastAPI отвечает только за HTTP: потоковую загрузку, HTTP-валидацию и схемы ответов. Он обращается к истории и запускает анализ исключительно через `AnalysisService`.

`AnalysisService` регистрирует задачу, передаёт её единственному фоновому worker и сохраняет результат либо безопасную ошибку. Незавершённые задачи после рестарта переводятся в `failed`.

Runner извлекает текст, проверяет лимит токенов и запускает LangGraph. Большие документы разбиваются на чанки; результаты объединяются редьюсерами. Исходный файл удаляется после завершения задачи.

Схема SQLite изменяется только версионируемыми Alembic-миграциями. На старте сервис выполняет `upgrade head`; прямого `CREATE TABLE` в runtime-коде нет.

## Режимы LLM

- `APP_MODE=real` — настоящий `GigaChatClient`;
- `APP_MODE=mock` — детерминированный `MockLLMClient` без сети.

Оба режима используют одинаковые transport, business, repository и LangGraph. Благодаря этому сквозные API-тесты подменяют только внешнюю модель, а не внутренний pipeline.

## Состояния задачи

```text
queued → running → completed
                 ↘ failed
```

## Публичный API

- `POST /analyze` — регистрация фонового анализа;
- `GET /documents` — страница истории;
- `GET /documents/{id}` — статус или полный результат;
- `GET /health` — проверка SQLite и worker;
- `GET /docs` — Swagger UI.

Gradio не входит в backend MVP и в будущем должен работать только через HTTP API.
