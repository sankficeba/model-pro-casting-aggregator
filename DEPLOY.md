# Автодеплой через GitHub Actions

Workflow: [.github/workflows/deploy.yml](.github/workflows/deploy.yml)

При `push` в `main` (или ручном запуске через `workflow_dispatch`):

1. Собирается Docker-образ.
2. Пушится в **GitHub Container Registry** (`ghcr.io/<owner>/<repo>:latest` + `:sha-<commit>`).
3. По SSH выполняется `docker compose pull && up -d` на VPS.

Используется `docker-compose.prod.yml`, который тянет готовый образ из GHCR
(в отличие от dev-варианта `docker-compose.yml`, где образ собирается локально).

---

## 1. Подготовка VPS (один раз)

### 1.1. Установить Docker и Compose plugin

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # перелогиниться после этого
docker compose version            # проверить
```

### 1.2. Создать deploy-пользователя (рекомендуется не использовать root)

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
sudo mkdir -p /home/deploy/.ssh && sudo chown deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
```

### 1.3. Сгенерировать SSH-ключ (на ЛОКАЛЬНОЙ машине)

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/tg_parser_deploy -N ""
```

Получится два файла:
- `~/.ssh/tg_parser_deploy`     — приватный (пойдёт в **секрет GitHub**)
- `~/.ssh/tg_parser_deploy.pub` — публичный (пойдёт на VPS)

### 1.4. Положить публичный ключ на VPS

```bash
ssh-copy-id -i ~/.ssh/tg_parser_deploy.pub deploy@YOUR_VPS_IP
# или вручную:
cat ~/.ssh/tg_parser_deploy.pub | ssh deploy@YOUR_VPS_IP \
  "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Проверить:

```bash
ssh -i ~/.ssh/tg_parser_deploy deploy@YOUR_VPS_IP 'echo OK && docker compose version'
```

### 1.5. Подготовить каталог проекта на VPS

```bash
ssh deploy@YOUR_VPS_IP
mkdir -p /home/deploy/tg_parser/{sessions,data}
cd /home/deploy/tg_parser
```

Положить туда **только** два файла (остальное прилетит в виде Docker-образа):

- `docker-compose.prod.yml` — скопировать из репозитория
- `.env` — реальные значения переменных (см. `.env.example`)

```bash
# на VPS:
nano docker-compose.prod.yml   # вставить содержимое из репо
nano .env                      # вставить реальные TG_API_ID, TG_API_HASH, BOT_TOKEN, OPENAI_API_KEY и т.д.
chmod 600 .env
```

### 1.6. Первый запуск + авторизация Telethon

При первом запуске Telethon потребует ввести код подтверждения.
Поэтому делаем это вручную в интерактивном режиме (один раз):

```bash
# Войти в GHCR (если репозиторий приватный — иначе пропустить)
echo "GHCR_PAT" | docker login ghcr.io -u GITHUB_USERNAME --password-stdin

export IMAGE="ghcr.io/<owner>/<repo>:latest"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml run --rm app
# ввести код из Telegram, дождаться "Userbot запущен"
# Ctrl+C
```

Файл сессии сохранится в `./sessions/userbot.session` (volume) и больше код спрашивать не будет.

Затем уже фоновый старт:

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f app
```

---

## 2. Секреты в GitHub

`Settings → Secrets and variables → Actions → New repository secret`

| Имя секрета         | Что класть |
|---------------------|------------|
| `SSH_HOST`          | IP или домен VPS |
| `SSH_USER`          | `deploy` (или ваш SSH-пользователь) |
| `SSH_PORT`          | (опционально) если SSH не на 22 |
| `SSH_PRIVATE_KEY`   | содержимое `~/.ssh/tg_parser_deploy` (целиком, с `-----BEGIN ...-----`) |
| `DEPLOY_PATH`       | `/home/deploy/tg_parser` |
| `GHCR_PULL_USER`    | ваш GitHub username (для `docker login` на VPS) |
| `GHCR_PULL_TOKEN`   | Personal Access Token со scope `read:packages` (см. ниже) |

### Создание GHCR_PULL_TOKEN

Если репозиторий **публичный** — этот секрет не нужен, удалите шаг `docker login` из workflow.

Если **приватный**:
1. `Settings → Developer settings → Personal access tokens → Tokens (classic)`
2. `Generate new token (classic)`, scope: `read:packages`.
3. Скопировать токен в секрет `GHCR_PULL_TOKEN`.

### Environment "production" (опционально, но рекомендуется)

`Settings → Environments → New environment → production` —
там можно включить **Required reviewers**, чтобы каждый деплой требовал подтверждения,
и/или ограничить ветки, с которых деплой разрешён.

---

## 3. Что делает workflow

```
push → main
   │
   ├── job: build-and-push
   │     ├── checkout
   │     ├── setup buildx
   │     ├── docker login ghcr.io (через GITHUB_TOKEN)
   │     ├── tags: latest + sha-<commit>
   │     └── docker buildx build --push (с GHA-кэшем)
   │
   └── job: deploy (needs: build-and-push)
         └── ssh deploy@VPS:
               docker login ghcr.io
               docker compose -f docker-compose.prod.yml pull
               docker compose -f docker-compose.prod.yml up -d --remove-orphans
               docker image prune -f
```

`concurrency.group: deploy-prod` — гарантирует, что одновременно идёт только один деплой.

## 4. Быстрая проверка

После пуша в `main`:

1. Открыть `Actions` в репозитории — пройти оба job-а до зелёного.
2. На VPS:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker compose -f docker-compose.prod.yml logs --tail=100 app
   ```

## 5. Откат

Образы тегаются `sha-<commit>`. Чтобы откатиться:

```bash
ssh deploy@VPS
cd /home/deploy/tg_parser
export IMAGE="ghcr.io/<owner>/<repo>:sha-<previous_commit>"
docker compose -f docker-compose.prod.yml up -d
```

## 6. Чего НЕТ в Git и НЕ должно туда попасть

- `.env`              — реальные секреты (есть в `.gitignore`)
- `sessions/`         — `.session` файлы Telethon
- `data/filters.json` — пользовательские фильтры

Эти файлы живут **только на VPS**. Workflow их не трогает.
