# Multi-Agent Document Analysis

Backend MVP для фонового анализа PDF, TXT, DOCX, HTML, Markdown и CSV через LangGraph. В рабочем режиме используется GigaChat, в тестовом — локальный детерминированный mock. История задач хранится в SQLite, схема управляется Alembic.

## Форматы документов

| Формат | Расширения | Что извлекается |
| --- | --- | --- |
| PDF | `.pdf` | Текст страниц |
| Обычный текст | `.txt` | UTF-8 текст |
| Word | `.docx` | Абзацы и таблицы, включая вложенные, в порядке документа |
| HTML | `.html`, `.htm` | Текст страницы, таблицы, адреса ссылок и подписи изображений без скриптов и стилей |
| Markdown | `.md`, `.markdown` | Заголовки, абзацы, списки, таблицы, ссылки и блоки кода |
| CSV | `.csv` | Строки и ячейки таблицы с автоматическим определением разделителя |

Регистр расширения не важен. Markdown и CSV читаются в UTF-8, в том числе с BOM; HTML учитывает объявленную кодировку страницы. Для CSV поддерживаются запятая, точка с запятой, табуляция и `|`, кавычки и переносы строк внутри ячеек. Строки преобразуются в текст с табуляцией между ячейками, без пересчёта чисел и формул. Формат определяется по расширению, поэтому у файла должно быть корректное окончание имени.

Файлы-примеры для ручной проверки находятся в `data/examples/`: загрузите любой из них через `POST /analyze` на странице `/docs`, затем проверьте результат через `GET /documents/{id}`. Для DOCX ограничен суммарный распакованный размер — 100 МБ. Читаются основной текст и таблицы; распознавание текста на изображениях не выполняется.

Загрузчики используют [python-docx](https://python-docx.readthedocs.io/en/latest/api/document.html), [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/), [markdown-it-py](https://markdown-it-py.readthedocs.io/en/latest/using.html) и стандартный модуль [csv](https://docs.python.org/3/library/csv.html).

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

## Dashboard Gradio

Для необязательного интерфейса нужен Python 3.10+ (backend без dashboard
сохраняет прежние требования). В соответствующее виртуальное окружение установите:

```bash
python -m pip install -e '.[dashboard,dev]'
```

Запустите backend из корня репозитория в одном терминале и интерфейс в другом:

```bash
# Терминал 1, без ключа и платных запросов
make run-mock

# Терминал 2, то же окружение
python -m multi_agent_docs.dashboard
```

Интерфейс: <http://127.0.0.1:7860>. Backend по умолчанию:
<http://127.0.0.1:8000>; другой адрес задаётся через `API_BASE_URL`.
`DASHBOARD_HOST` и `DASHBOARD_PORT` меняют адрес интерфейса; публичная share-ссылка
не создаётся. Gradio не загружается при обычном запуске backend.

UI отправляет один `POST /analyze`, показывает ID и опрашивает
`GET /documents/{id}`. Отображаются queued/running/completed/failed и вкладки
итога, анализа, summary, фактчека и токенов. Через пять минут ожидание
останавливается; задача в backend продолжает выполняться. Сохраните ID и
нажмите «Обновить по ID», в том числе после перезапуска интерфейса.
При обрыве связи во время самой отправки результат приёма может быть неизвестен:
проверьте историю API перед повторной загрузкой, чтобы не создать новую задачу.

Существующее окружение Python 3.9 не нужно перезаписывать: создайте отдельное
окружение Python 3.10+ для dashboard. Gradio не является системой авторизации;
публикация интерфейса для внешних пользователей требует отдельного решения.

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

Завершённый анализ в `GET /documents/{id}` содержит метаданные исходного файла:

```json
{"metadata": {"file_type": "txt", "size_bytes": 1024}}
```

Тип определяется по расширению без учёта регистра (`pdf`, `txt`, `docx`, `html`, `md` или `csv`), содержимое проверяет загрузчик. `.htm` нормализуется в `html`, `.markdown` — в `md`. Размер измеряется в байтах до извлечения текста. Метаданные передаются в `State` каждого графа, в том числе при разбиении на фрагменты, и сохраняются вместе с результатом в SQLite. Для незавершённых анализов и старых записей без метаданных API возвращает `metadata: null`.

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
