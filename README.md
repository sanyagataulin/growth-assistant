# Помощник роста (Growth Assistant)

ИИ-советник фермера, продающего продукцию через онлайн-маркетплейс. Приложение анализирует данные магазина — продажи, товары, остатки и сроки годности, акции, поведение клиентов — и каждый день формирует топ-3 приоритетных действий в виде карточек с оценкой недельного эффекта и уверенности. Тексты рекомендаций генерирует LLM через OpenRouter; без API-ключа помощник работает на шаблонных формулировках. Есть переключатель дня, чтобы видеть, как меняются приоритеты со временем.

При первом старте база автоматически наполняется детерминированными демо-данными одного магазина.

## Стек

**Backend**
- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2, Alembic, PostgreSQL 16 (psycopg 3)
- Pydantic v2 + pydantic-settings
- JWT-аутентификация (PyJWT, bcrypt)
- LangChain (langchain-openai → OpenRouter) для генерации текстов

**Frontend**
- React 18, TypeScript
- Vite 5 (в production — nginx)
- Ant Design 5, Recharts, dayjs

**Инфраструктура**
- Docker Compose (db + backend + frontend)

## Запуск

### Docker Compose (рекомендуется)

```bash
cp .env.example .env   # при желании впишите OPENROUTER_API_KEY
docker compose up --build
```

- Фронтенд: http://localhost:3000
- API: http://localhost:8000, Swagger UI: http://localhost:8000/docs
- Демо-логин: **farmer** / **farmer123**

При старте контейнер бэкенда сам применяет миграции Alembic и, если база пуста, засеивает демо-данными. Ключ `OPENROUTER_API_KEY` необязателен — без него рекомендации используют шаблонные тексты.

### Локально без Docker

Нужен запущенный PostgreSQL и Python 3.12, Node 22.

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Задайте переменные окружения (см. `.env.example` в корне), обязательно `DATABASE_URL` — дефолт указывает на хост `db`, который вне Docker не резолвится, например:

```bash
export DATABASE_URL=postgresql+psycopg://farmer:farmer@localhost:5432/growth
```

Затем:

```bash
alembic upgrade head
python -m app.seed_if_empty
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Dev-сервер Vite поднимется на http://localhost:3000 и проксирует `/api` на `http://localhost:8000`. Продакшен-сборка: `npm run build`.
