# Telegram Parser + LLM (MVP)

Userbot читает сообщения из Telegram-каналов, пропускает их через LLM
(абстрактный интерфейс — OpenAI или локальный Ollama), извлекает
структурированные данные (пол, возраст, категория, краткое описание),
и aiogram-бот отправляет уведомления подписчикам, чьи фильтры совпали.

## Архитектура

```
┌──────────────┐    new msg    ┌─────────┐  JSON   ┌──────────────┐
│  Каналы TG   │──────────────▶│ Userbot │────────▶│   LLM (abs)  │
└──────────────┘   Telethon    └────┬────┘         └──────┬───────┘
                                    │                     │
                                    ▼                     ▼
                              ┌────────────┐        ExtractedData
                              │ Filters    │              │
                              │ (JSON)     │◀─────────────┘
                              └─────┬──────┘   matches
                                    │
                                    ▼
                              ┌────────────┐
                              │ aiogram Bot│──▶ уведомление подписчику
                              └────────────┘
```

## Структура проекта

```
model_pro/
├── main.py                  # точка входа: запускает userbot + bot параллельно
├── config.py                # pydantic-settings из .env
├── models/
│   └── schemas.py           # ExtractedData, UserFilter (+ matches)
├── llm/
│   ├── base.py              # абстрактный класс LLMProvider + системный промт
│   ├── openai_provider.py   # OpenAI (или совместимый API)
│   ├── ollama_provider.py   # локальный Ollama
│   └── factory.py           # выбор провайдера по LLM_PROVIDER
├── filters/
│   └── storage.py           # JSON-хранилище фильтров пользователей
├── userbot/
│   └── client.py            # Telethon: слушает каналы, рассылает совпадения
├── bot/
│   └── handlers.py          # aiogram: /start /filter /myfilter /delete
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Подготовка

1. Получить `API_ID` и `API_HASH` на https://my.telegram.org → API development tools.
2. Создать бота у `@BotFather`, получить `BOT_TOKEN`.
3. Скопировать `.env.example` в `.env` и заполнить значения.
4. Указать каналы в `TG_CHANNELS` (через запятую: `@channel1,@channel2`).

## Запуск через Docker (рекомендовано)

```bash
docker compose up --build
```

При первом запуске Telethon запросит код подтверждения — посмотрите логи
контейнера и введите код там же:

```bash
docker compose logs -f app
docker attach tg_parser_app   # ввести код
```

После авторизации файл сессии сохранится в `./sessions/` (volume).
**Не удаляйте этот каталог** — иначе придётся авторизоваться заново.

## Локальный запуск (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env         # затем отредактировать
python main.py
```

## Управление фильтрами

В Telegram своему aiogram-боту:

```
/start
/filter gender=female age=18-30 category=обучение confidence=0.6
/myfilter
/delete
```

Все параметры опциональны:

- `gender`: `male` | `female`
- `age`: число (`25`) или диапазон (`18-30`)
- `category`: подстрока поиска по категории
- `confidence`: минимальная уверенность LLM (0..1, по умолчанию 0.5)

## Переключение LLM-провайдера

В `.env`:

```
LLM_PROVIDER=openai     # или ollama
```

Чтобы добавить нового провайдера (например, OpenRouter, Anthropic) —
создайте класс в `llm/`, унаследовав от `LLMProvider`, и зарегистрируйте
его в `llm/factory.py`.

## Замечания по эксплуатации

- **Сессия Telethon** хранится в `./sessions/userbot.session` — храните в безопасности.
- **Лимиты Telegram**: при подписке на десятки каналов добавьте `asyncio.sleep`
  на «горячих» путях — не получайте entity повторно в цикле.
- **Масштабирование**: для большого потока сообщений вынесите LLM-обработку в
  очередь задач (Celery/RQ + Redis) — текущий MVP блокирует поток ответом LLM.
- **Валидация ответа LLM**: даже с `response_format=json_object` модель может
  вернуть мусор — `llm/base.py` отлавливает ошибки парсинга и возвращает
  `confidence=0.0`, после чего сообщение игнорируется.

## Автодеплой (CI/CD)

Push в `main` → GitHub Actions собирает образ, пушит в GHCR и обновляет VPS по SSH.
Подробная пошаговая настройка: [DEPLOY.md](DEPLOY.md).

Файлы: [.github/workflows/deploy.yml](.github/workflows/deploy.yml), [docker-compose.prod.yml](docker-compose.prod.yml).

## Дальнейшие шаги (за пределами MVP)

- PostgreSQL вместо JSON (несколько фильтров на пользователя, история сообщений).
- Redis для дедупликации и очереди.
- Веб-админка (FastAPI) для управления каналами.
- Метрики Prometheus + Grafana.
