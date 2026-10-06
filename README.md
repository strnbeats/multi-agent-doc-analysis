# Multi-Agent Document Analysis

Backend MVP для фонового анализа PDF/TXT через LangGraph. В рабочем режиме используется GigaChat, в тестовом — локальный детерминированный mock. История задач хранится в SQLite, схема управляется Alembic.

## Быстрый старт

Требуется Python 3.9+ и `make`.

```bash
make install
cp .env.example .env
```

Для рабочего режима заполните `GIGACHAT_CREDENTIALS` в `.env`, затем выполните:

```bash
make migrate
make run
```

API будет доступно на <http://127.0.0.1:8000>, Swagger — на <http://127.0.0.1:8000/docs>.

## Режимы запуска

Рабочий режим проходит полный pipeline и обращается к GigaChat:

```bash
make run
# или напрямую
./cmd/run.sh real
```

Тестовый режим проходит тот же `FastAPI → service → runner → LangGraph → agents → SQLite`, но использует встроенный mock LLM и отдельную базу `data/mock.db`:

```bash
make run-mock
# или напрямую
./cmd/run.sh mock
```

Mock-режим удобен для Swagger, Postman и разработки без ключа GigaChat. Это не упрощённый endpoint: подменяется только внешний LLM-клиент.

Дополнительные настройки запуска:

```bash
HOST=0.0.0.0 PORT=8080 make run-mock
RELOAD=1 make run-mock
```

## Миграции базы

Приложение автоматически выполняет `upgrade head` при старте. Явный запуск:

```bash
make migrate
./cmd/migrate.sh
```

Создание новой ревизии после изменения схемы:

```bash
.venv/bin/alembic revision -m "описание изменения"
```

Откат последней ревизии:

```bash
.venv/bin/python -m multi_agent_docs.commands downgrade --revision=-1
```

Первая миграция принимает таблицу `documents`, созданную предыдущей версией backend, не удаляя существующие записи. Текущая версия хранится в `alembic_version`.

## Тестирование

Все тесты используют mock и не обращаются к GigaChat:

```bash
make test
```

Только сквозные HTTP API-тесты:

```bash
make test-api
```

Полная локальная проверка тестов и Postman JSON:

```bash
make check
```

Сквозной тест API действительно запускает загрузчик, runner, LangGraph, агентов, фоновую очередь и SQLite. Заглушкой является только ответ внешней языковой модели.

## Postman

Импортируйте:

- `postman/document-analysis.postman_collection.json`;
- `postman/local.postman_environment.json`.

Запустите `make run-mock`, выберите окружение `Document Analysis Local`, затем выполните запросы по порядку:

1. `Health`;
2. `Analyze document` — сохраняет полученный ID в `document_id`;
3. `Get analysis status or result`;
4. запросы раздела `History`.

Если Postman не подставил файл автоматически, вручную выберите `data/raw/test.txt` в поле `file` запроса `Analyze document`.

## API

- `POST /analyze` — принять файл и вернуть `202` с ID;
- `GET /documents/{id}` — получить статус или полный результат;
- `GET /documents?limit=50&offset=0` — получить историю;
- `GET /health` — проверить SQLite и worker;
- `GET /docs` — открыть Swagger.

Ограничения по умолчанию: загрузка до 100 МБ и до 250 000 токенов извлечённого текста. Временный исходный файл удаляется после обработки.

## Команды

```text
make help          список команд
make install       установка окружения
make migrate       миграции SQLite
make run           рабочий API
make run-mock      тестовый API
make test          все тесты
make test-api      сквозные API-тесты
make check         все локальные проверки
```
