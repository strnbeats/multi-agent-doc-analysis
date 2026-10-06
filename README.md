# Multi-Agent Document Analysis

Backend MVP для фонового анализа PDF/TXT через GigaChat и LangGraph. Результаты и история задач сохраняются в SQLite.

## Установка

Требуется Python 3.9+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Заполните `GIGACHAT_CREDENTIALS` в `.env`. По умолчанию проверка SSL включена.

## Запуск

```bash
uvicorn multi_agent_docs.main:app --reload
```

- Swagger: <http://127.0.0.1:8000/docs>
- Проверка состояния: <http://127.0.0.1:8000/health>

`POST /analyze` возвращает `202` и ID фоновой задачи. Состояние и результат доступны через `GET /documents/{id}`, история — через `GET /documents`.

Ограничения по умолчанию: загрузка до 100 МБ и до 250 000 токенов извлечённого текста. Исходные файлы удаляются после обработки.

## Тесты

```bash
pytest
```

Автоматические тесты не обращаются к GigaChat. Для ручной проверки используйте Swagger и тестовый файл из `data/raw`.
