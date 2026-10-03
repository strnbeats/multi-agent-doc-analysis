# Архитектура проекта

## 1. Общая информация

Название: Multi-Agent Document Analysis
Интерфейс: CLI/Dashboard
Язык: Python
Статус: Prototype

## 2. Общая схема

Пользователь
    |
    v
CLI/Dashboard
    |
    v
Application Core
    |
    v
Workflow / Orchestrator
    |
    +--> Document Ingestion
    |
    +--> Retrieval / RAG
    |
    +--> Analysis
    |
    +--> Verification
    |
    v
Результат пользователю

## 3. Компоненты

### CLI
Принимает команды и отображает результаты.

### Application Core
Связывает интерфейс с логикой приложения.

### Document Ingestion
Загружает документы и извлекает текст.

### Retrieval / RAG
Ищет релевантные фрагменты документов.

### Agents
Выполняют специализированные задачи.

### Workflow / Orchestrator
Управляет последовательностью выполнения.

## 4. Технологии

- Python
- Fastapi
- OpenAI
- Pypdf
- LangChain
- LangGraph
- SQLite(неоднозначно)
- Gradio(для создания Dashboard)

## 5. Открытые вопросы

- Основной пользовательский сценарий
- Набор агентов
- Формат хранения документов
- Векторная база
- Распределение ответственности в команде