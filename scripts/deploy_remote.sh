#!/usr/bin/env bash
# Серверная часть ручного деплоя (запускается scripts/deploy_manual.ps1).
# Использование: bash deploy_remote.sh <build_dir> <all|backend|webapp>
#
# Что делает:
#   1. backend: образ с зависимостями «deps-<sha requirements.txt>» (собирается
#      полностью только если requirements.txt изменился), поверх него — свежий
#      код (старый /app удаляется, мусора от прошлых версий не остаётся);
#      webapp: nginx + уже собранный локально dist.
#   2. Smoke-проверка нового backend-образа: импорт модулей и сборка бота.
#   3. Текущие образы помечаются rollback-<время>, миграции БД прогоняются
#      ОДИН раз (иначе app и api стартуют и мигрируют одновременно).
#   4. Перезапуск только app/api/webapp (postgres и caddy не трогаем).
#   5. Проверка здоровья; при провале — автоматический откат на rollback-образ.
set -euo pipefail

BUILD_DIR="${1:?build dir}"
TARGET="${2:-all}"
APP_DIR=/home/deploy/tg_parser
IMG=ghcr.io/sankficeba/model-pro-casting-aggregator
WIMG=${IMG}-webapp
STAMP=$(date -u +%Y%m%d%H%M%S)
D="sudo -n docker"

log() { echo "[deploy] $*"; }
compose() {
  sudo -n bash -c "cd $APP_DIR && IMAGE=$IMG:latest WEBAPP_IMAGE=$WIMG:latest docker compose -f docker-compose.prod.yml $*"
}

ENV_FILE=$(mktemp); chmod 600 "$ENV_FILE"
trap 'rm -f "$ENV_FILE"' EXIT
$D inspect tg_parser_app --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -v '^\s*$' > "$ENV_FILE"
NET=$($D inspect tg_parser_app --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')

services=()
if [[ "$TARGET" == all || "$TARGET" == backend ]]; then
  REQ_SHA=$(sha256sum "$BUILD_DIR/backend/requirements.txt" | cut -c1-12)
  DEPS_TAG="deps-$REQ_SHA"
  if ! $D image inspect "$IMG:$DEPS_TAG" >/dev/null 2>&1; then
    CUR_SHA=$($D run --rm --entrypoint sh "$IMG:latest" -c 'sha256sum /app/requirements.txt' | cut -c1-12)
    if [[ "$CUR_SHA" == "$REQ_SHA" ]]; then
      log "зависимости не менялись — берём текущий образ как $DEPS_TAG"
      $D tag "$IMG:latest" "$IMG:$DEPS_TAG"
    else
      log "requirements.txt изменился — полная сборка образа зависимостей $DEPS_TAG"
      $D build -q -f "$BUILD_DIR/backend/Dockerfile" -t "$IMG:$DEPS_TAG" "$BUILD_DIR/backend"
    fi
  fi
  cat > "$BUILD_DIR/backend/Dockerfile.overlay" <<EOF
FROM $IMG:$DEPS_TAG
RUN find /app -mindepth 1 -maxdepth 1 ! -name sessions -exec rm -rf {} +
COPY . /app/
RUN chmod +x /app/entrypoint.sh && mkdir -p /app/sessions
EOF
  $D build -q -f "$BUILD_DIR/backend/Dockerfile.overlay" -t "$IMG:candidate" "$BUILD_DIR/backend" >/dev/null
  log "smoke-проверка backend-образа"
  $D run --rm --entrypoint python --env-file "$ENV_FILE" "$IMG:candidate" -c "
import api.main, main, bot.handlers
from aiogram import Bot
bot.handlers.build_dispatcher(Bot('1:' + 'A' * 35))
print('SMOKE_OK')" | grep -q SMOKE_OK || { log "SMOKE FAILED — прод не тронут"; exit 1; }
  services+=(app api)
fi
if [[ "$TARGET" == all || "$TARGET" == webapp ]]; then
  cat > "$BUILD_DIR/webapp/Dockerfile.static" <<'EOF'
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist /usr/share/nginx/html
EXPOSE 80
EOF
  $D build -q -f "$BUILD_DIR/webapp/Dockerfile.static" -t "$WIMG:candidate" "$BUILD_DIR/webapp" >/dev/null
  $D run --rm "$WIMG:candidate" nginx -t >/dev/null 2>&1 || { log "nginx -t FAILED — прод не тронут"; exit 1; }
  services+=(webapp)
fi

log "rollback-метки: rollback-$STAMP"
$D tag "$IMG:latest" "$IMG:rollback-$STAMP"
$D tag "$WIMG:latest" "$WIMG:rollback-$STAMP"

if [[ " ${services[*]} " == *" app "* ]]; then
  $D tag "$IMG:candidate" "$IMG:latest"
  log "миграции БД (один раз)"
  $D run --rm --network "$NET" --entrypoint alembic --env-file "$ENV_FILE" -e POSTGRES_HOST=postgres "$IMG:latest" upgrade head
fi
if [[ " ${services[*]} " == *" webapp "* ]]; then
  $D tag "$WIMG:candidate" "$WIMG:latest"
fi

log "перезапуск: ${services[*]}"
compose up -d --no-deps "${services[*]}" >/dev/null 2>&1

rollback() {
  log "ПРОВЕРКА НЕ ПРОШЛА — откат на rollback-$STAMP"
  $D tag "$IMG:rollback-$STAMP" "$IMG:latest"
  $D tag "$WIMG:rollback-$STAMP" "$WIMG:latest"
  compose up -d --no-deps "${services[*]}" >/dev/null 2>&1
  exit 1
}

sleep 40
for s in "${services[@]}"; do
  st=$($D inspect "tg_parser_$s" --format '{{.State.Status}} restarts={{.RestartCount}}')
  log "tg_parser_$s: $st"
  [[ "$st" == "running restarts=0" ]] || rollback
done
if [[ " ${services[*]} " == *" app "* ]]; then
  if $D logs --since 1m tg_parser_app 2>&1 | grep -q Traceback; then
    $D logs --since 1m tg_parser_app 2>&1 | grep -A5 Traceback | head -20; rollback
  fi
  $D logs --since 1m tg_parser_app 2>&1 | grep -q "aiogram-бот запущен" || rollback
  $D exec tg_parser_caddy wget -qO- http://api:8000/api/health >/dev/null || rollback
fi
if [[ " ${services[*]} " == *" webapp "* ]]; then
  $D exec tg_parser_caddy wget -qO- http://webapp/app | grep -q '<div id="root">' || rollback
fi

# Оставляем 3 последних rollback-метки, кандидаты удаляем.
for repo in "$IMG" "$WIMG"; do
  $D images "$repo" --format '{{.Tag}}' | grep '^rollback-2' | sort -r | tail -n +4 | xargs -r -I{} $D rmi "$repo:{}" >/dev/null 2>&1 || true
  $D rmi "$repo:candidate" >/dev/null 2>&1 || true
done
$D image prune -f >/dev/null
rm -rf "$BUILD_DIR"
log "OK — задеплоено (${services[*]}), откат: rollback-$STAMP"
