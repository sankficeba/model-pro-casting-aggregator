# Деплой на VPS — modelpro.agency

Полный пайплайн: GitHub Actions → GHCR → SSH на VPS → docker compose с Caddy/SSL.

При `push` в `main`:

1. Собирается Docker-образ (один общий для bot и api).
2. Пушится в **GitHub Container Registry** (`ghcr.io/<owner>/<repo>:latest` + `:sha-<commit>`).
3. По SSH на VPS копируются `docker-compose.prod.yml` и `Caddyfile`, выполняется `docker compose pull && up -d`, Caddy перечитывает конфиг.

## Сервисы на VPS

```
┌───────────────────────────┐       ┌─────────────────────┐
│ Caddy (80/443)            │  ◄──  │ Интернет (modelpro) │
│ - LE авто-SSL             │       └─────────────────────┘
│ - / → "Coming soon" /     │
│   webapp:80 (когда будет) │
│ - /api/* → api:8000       │
└───┬──────────────┬────────┘
    │              │
    ▼              ▼
┌─────────┐    ┌─────────┐
│ webapp  │    │  api    │ (FastAPI uvicorn)
│ (later) │    │ :8000   │
└─────────┘    └────┬────┘
                    │
              ┌─────▼─────┐    ┌──────────────────┐
              │ postgres  │ ◄─ │ app (bot+userbot)│
              │ :5432     │    │ Telethon+aiogram │
              └───────────┘    └──────────────────┘
```

## 1. Подготовка домена (modelpro.agency)

### 1.1. Узнать IP вашего VPS

```bash
ssh deploy@VPS_IP
curl -s ifconfig.me
```

### 1.2. Прописать A-записи у регистратора домена

В DNS-панели регистратора (где покупали `modelpro.agency`):

| Тип | Имя | Значение | TTL |
|---|---|---|---|
| A | `@`   | `IP_VPS` | 600 |
| A | `www` | `IP_VPS` | 600 |

После сохранения — DNS-обновление занимает от 5 минут до пары часов.

### 1.3. Проверить, что DNS дошёл

С локальной машины:

```bash
# Linux/macOS
dig modelpro.agency A +short
dig www.modelpro.agency A +short

# Windows PowerShell
nslookup modelpro.agency
```

Должны увидеть IP вашего VPS. Если возвращает что-то другое — DNS ещё не распространился, подождите.

## 2. Открыть порты на VPS

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow OpenSSH                # уже должно быть
sudo ufw enable
sudo ufw status
```

Без открытых 80/443 Caddy не получит сертификат от Let's Encrypt (валидация идёт по HTTP-01 challenge на 80 порту).

## 3. Подготовка каталога проекта

```bash
ssh deploy@VPS_IP
mkdir -p /home/deploy/tg_parser/{sessions}
cd /home/deploy/tg_parser
```

`.env` (скопировать из `.env.example` и заполнить):

```bash
nano .env
```

Минимум:

```
TG_API_ID=...
TG_API_HASH=...
TG_PHONE=+7...
TG_SESSION_NAME=userbot
BOT_TOKEN=...
TG_CHANNELS=@channel1,@channel2
LLM_PROVIDER=stub

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=tg_parser
POSTGRES_USER=tg_parser
POSTGRES_PASSWORD=придумайте_надёжный_пароль_не_менее_24_символов

IMAGE=ghcr.io/sankficeba/model_pro:latest
LOG_LEVEL=INFO
```

```bash
chmod 600 .env
```

## 4. Секреты GitHub Actions

`Settings → Secrets and variables → Actions`:

| Секрет | Значение |
|---|---|
| `SSH_HOST` | IP или `modelpro.agency` |
| `SSH_USER` | `deploy` |
| `SSH_PORT` | (опц.) если SSH не на 22 |
| `SSH_PRIVATE_KEY` | приватный ключ (ed25519) |
| `DEPLOY_PATH` | `/home/deploy/tg_parser` |
| `GHCR_PULL_USER` | ваш GitHub username |
| `GHCR_PULL_TOKEN` | PAT со scope `read:packages` (если репо приватный) |

## 5. Первый запуск

После пуша в `main` Actions сам всё сделает. Но для самого первого запуска нужно:

### 5.1. Telethon-сессия (один раз, интерактивно)

```bash
cd /home/deploy/tg_parser
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml run --rm app
```

Откроется интерактивный сеанс. В чате с «Telegram» (ID 777000) в самом мессенджере придёт код — введите его. После «Userbot запущен» нажмите Ctrl+C.

### 5.2. Поднять всё в фоне

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

Должно быть 4 контейнера в статусе `Up`/`healthy`:

| Контейнер | Назначение |
|---|---|
| `tg_parser_app` | userbot + aiogram bot |
| `tg_parser_api` | FastAPI на 8000 |
| `tg_parser_caddy` | reverse proxy, 80/443 |
| `tg_parser_postgres` | БД |

### 5.3. Проверить SSL и API

```bash
# С VPS изнутри:
curl http://127.0.0.1:8000/api/health    # {"status":"ok"}

# С локальной машины (после DNS):
curl https://modelpro.agency/api/health
curl https://modelpro.agency/                 # "Casting Mini App is starting up..."
```

Если открыть `https://modelpro.agency/` в браузере — должен быть валидный SSL (зелёный замок) и ваше сообщение-заглушка.

Если SSL ещё «получается» — Caddy в этот момент проходит challenge у Let's Encrypt. В логах:

```bash
docker compose -f docker-compose.prod.yml logs --tail=50 caddy
```

Ищите строки вроде `obtaining certificate` / `certificate obtained successfully`.

## 6. Мониторинг

```bash
# Все логи
docker compose -f docker-compose.prod.yml logs -f

# Только бот
docker compose -f docker-compose.prod.yml logs -f app

# Только API
docker compose -f docker-compose.prod.yml logs -f api

# Только Caddy (там видны входящие HTTPS-запросы)
docker compose -f docker-compose.prod.yml logs -f caddy
```

## 7. Подключение к БД с локальной машины (опц.)

```powershell
# SSH-туннель
ssh -N -L 5432:localhost:5432 deploy@modelpro.agency
```

В DBeaver / pgAdmin: host `localhost`, port `5432`, db `tg_parser`, user `tg_parser`, password — из `.env`.

## 8. Откат

Все образы тегаются `sha-<commit>`. На VPS:

```bash
cd /home/deploy/tg_parser
export IMAGE="ghcr.io/sankficeba/model_pro:sha-<previous_commit>"
docker compose -f docker-compose.prod.yml up -d
```

## 9. Troubleshooting

| Симптом | Причина | Лечение |
|---|---|---|
| Mini App: «Не удалось загрузить» | домен ещё без HTTPS | подождать 1-2 минуты, посмотреть `docker compose logs caddy` |
| `permission denied` для docker.sock | deploy не в группе docker | `sudo usermod -aG docker deploy && relogin` |
| `unable to get image OWNER/REPO` | не задана `IMAGE` в .env | дописать `IMAGE=ghcr.io/.../...:latest` в `.env` |
| `Temporary failure in name resolution` | postgres не поднялся | `docker compose ps`, проверить логи postgres |
| Caddy: `obtaining certificate failed` | DNS ещё не пришёл / 80 порт закрыт | `dig modelpro.agency A`, `sudo ufw status` |
