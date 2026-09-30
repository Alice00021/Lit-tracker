# Lit Tracker

Трекер прочитанных книг с заметками и **рекомендациями на основе вкуса**, который анализирует локальная LLM.
Читаешь книгу → пишешь заметку → сервис строит «профиль вкуса» и подбирает похожие книги по векторному поиску.

## Что умеет

- **Книги и записи о чтении** — CRUD, оценка, заметка, дата прочтения.
- **Профиль вкуса** — LLM (Ollama) анализирует заметки и выделяет темы, стиль, любимое и нелюбимое.
  Анализ идёт в фоне на графе **LangGraph**: повторы с обратной связью в промпт, backoff, проверка результата.
  Состояние сохраняется в Postgres после каждого шага, поэтому анализ **переживает рестарт сервиса** (см. ниже).
- **Рекомендации** — усреднённый эмбеддинг заметок → поиск похожих книг через **pgvector**.
- **Умный поиск** — агент **LangChain** с инструментами поверх каталога; результаты кэшируются в Redis.
- **Эксплуатация** — две реплики приложения за nginx, миграции Alembic, метрики Prometheus, дашборды Grafana,
  rate limit, request-id в логах.

## Архитектура

```mermaid
flowchart LR
    client([Клиент]) --> nginx[nginx :8080]
    nginx --> app1[app1 FastAPI]
    nginx --> app2[app2 FastAPI]
    app1 & app2 --> pg[(PostgreSQL + pgvector)]
    app1 & app2 --> redis[(Redis)]
    app1 & app2 --> ollama[[Ollama: LLM + embeddings]]
    prom[Prometheus] -. scrape /metrics .-> app1 & app2
    grafana[Grafana] --> prom
    migrate[migrate: alembic + seed] -. один раз при старте .-> pg
```

Код разложен по слоям (чистая архитектура): зависимости идут только внутрь.

```
app/
├── domain/          # сущности, интерфейсы репозиториев, исключения
├── application/     # сервисы (бизнес-логика)
├── infrastructure/  # БД, LLM-клиенты, LangChain-агент, LangGraph-граф
├── interfaces/      # FastAPI-роуты, схемы, middleware
└── models/          # SQLAlchemy-модели
```

## Стек

| Область | Технологии |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Данные | PostgreSQL 15 + pgvector, SQLAlchemy 2 (async), Alembic, Redis |
| AI | Ollama (`llama3.1`, `nomic-embed-text`), LangChain, LangGraph |
| Инфраструктура | Docker Compose, nginx, Prometheus, Grafana |
| Качество | pytest (unit / e2e), ruff, GitHub Actions (lint → test → docker build → публикация образа в GHCR) |

## Быстрый старт

Нужны Docker с Compose и [Ollama](https://ollama.com) на машине (или доступная по сети).

Проект зависит от общей библиотеки [`common-service`](https://github.com/Alice00021/Common-service),
поэтому репозитории клонируются **рядом**:

```bash
git clone https://github.com/Alice00021/Lit-tracker.git lit-tracker
git clone https://github.com/Alice00021/Common-service.git common-service

# модели для эмбеддингов и анализа
ollama pull nomic-embed-text
ollama pull llama3.1

cd lit-tracker
cp .env.example .env
docker compose up -d --build
```

Первый запуск собирает образ и сам применяет миграции (сервис `migrate`).

| Что | Адрес |
|---|---|
| API через nginx | http://localhost:8080 |
| Swagger UI | http://localhost:8080/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (логин/пароль из `.env.example`) |

Ollama на другой машине: укажи её адрес в `.env` (`OLLAMA_BASE_URL`), по умолчанию compose ходит в Ollama на хосте
(`http://host.docker.internal:11434`).

### Пример

```bash
# добавить книгу
curl -X POST localhost:8080/books -H 'content-type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert"}'

# отметить прочитанной с заметкой
curl -X POST localhost:8080/books/1/entries -H 'content-type: application/json' \
  -d '{"note": "Потрясающее мировоззрение и политика", "read_date": "2026-09-01", "rating": 5}'

# запустить анализ вкуса (вернётся 202, работа идёт в фоне)
curl -X POST localhost:8080/taste-profile/analyze
curl localhost:8080/taste-profile          # status: pending → processing → done

curl localhost:8080/recommendations
```

## API

| Метод | Путь | Описание |
|---|---|---|
| `POST` `GET` | `/books` | создать книгу / список |
| `GET` `PATCH` `DELETE` | `/books/{id}` | одна книга |
| `POST` | `/books/{id}/entries` | запись о прочтении с заметкой |
| `GET` | `/books/entries` | записи о чтении |
| `GET` `PATCH` `DELETE` | `/books/entries/{id}` | одна запись |
| `POST` | `/books/search/smart` | умный поиск (LangChain-агент) |
| `POST` | `/taste-profile/analyze` | запустить анализ вкуса (202, в фоне) |
| `GET` | `/taste-profile` | статус и результат анализа |
| `GET` | `/recommendations` | рекомендации по вкусу |
| `GET` | `/health`, `/metrics` | healthcheck и метрики Prometheus |

Полная схема — в Swagger UI.

## Как устроен анализ вкуса

```mermaid
flowchart LR
    A[collect_notes] --> B[analyze_taste]
    B --> C{validate_analysis}
    C -- ок --> S[save_profile]
    C -- ошибка, есть попытки --> R[retry_analysis: backoff + причина в промпт] --> B
    C -- попытки кончились / повтор бессмыслен --> F[fail_profile]
```

- Ошибка прошлой попытки добавляется в промпт, паузы между попытками растут; если заметок нет — сразу `failed`.
- Граф компилируется с **Postgres-чекпоинтером**: после каждого узла состояние сохраняется.
- Если сервис упал или был перезапущен посреди анализа, фоновая задача каждые 60 с ищет «зависшие» записи
  (`pending`/`processing` без движения более 5 минут) и **продолжает с последнего шага**, не повторяя уже сделанное.
  Захват записи атомарный, поэтому при двух репликах анализ подхватит ровно одна.
- Живой анализ отмечает себя heartbeat-ом, чтобы его не приняли за зависший.

## Разработка и тесты

```bash
python -m venv venv && source venv/bin/activate
pip install -e ../common-service
pip install -r requirements.txt

ruff check app tests scripts
pytest tests/unit          # быстрые тесты, внешние сервисы не нужны
```

**E2E-тесты** гоняют настоящее приложение (lifespan, Postgres, Redis, чекпоинтер LangGraph);
Ollama в них подменён заглушкой, поэтому она не нужна. Нужны Postgres с `pgvector` и Redis
(`docker compose up -d postgres redis`) и **отдельная** БД, чтобы не трогать рабочие данные:

```bash
docker compose exec postgres psql -U postgres -c "CREATE DATABASE lit_tracker_e2e"
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/lit_tracker_e2e
export REDIS_URL=redis://localhost:6380/1 SERVICE_ENV=test
alembic upgrade head && python -m scripts.setup_checkpointer
pytest tests/e2e
```

В CI (GitHub Actions) при каждом push/PR выполняются: lint, unit- и e2e-тесты, поиск секретов в истории
(gitleaks) и сборка Docker-образа.

## Настройки

Все параметры читаются из переменных окружения — список с комментариями в [`.env.example`](.env.example).

## Планы

- Авторизация (JWT): сейчас все роуты работают от демо-пользователя `user_id=1`, он создаётся seed-скриптом.
- Автодеплой на сервер из CD-пайплайна (сейчас образ публикуется в GHCR).
- Очередь задач для тяжёлых фоновых операций, если нагрузка вырастет.
