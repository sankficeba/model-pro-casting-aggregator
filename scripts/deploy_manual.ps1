<#
.SYNOPSIS
  Ручной деплой на прод в обход GitHub Actions (когда CI недоступен).

.DESCRIPTION
  1. Проверяет, что все изменения закоммичены (деплоится ровно HEAD).
  2. Гоняет pytest (через uv) и собирает фронт (npm run build).
  3. Пакует HEAD (git archive, LF-переводы строк) + webapp/dist, грузит на сервер.
  4. На сервере scripts/deploy_remote.sh: сборка, smoke-проверка, rollback-метка,
     миграции, перезапуск app/api/webapp, проверка здоровья, авто-откат.

.EXAMPLE
  ./scripts/deploy_manual.ps1                  # всё
  ./scripts/deploy_manual.ps1 -Target backend  # только бот+API
  ./scripts/deploy_manual.ps1 -Target webapp   # только Mini App

.NOTES
  Откат вручную (на сервере):
    IMG=ghcr.io/sankficeba/model-pro-casting-aggregator
    sudo docker tag $IMG:rollback-<время> $IMG:latest   # (и -webapp при необходимости)
    cd /home/deploy/tg_parser && sudo IMAGE=$IMG:latest WEBAPP_IMAGE=$IMG-webapp:latest \
      docker compose -f docker-compose.prod.yml up -d --no-deps app api webapp
#>
param(
    [ValidateSet("all", "backend", "webapp")]
    [string]$Target = "all",
    # Хост из ~/.ssh/config и его адрес.
    [string]$SshHost = "modelpro",
    [string]$HostName = "194.1.132.93",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
$ssh = @("-o", "BatchMode=yes", "-o", "HostName=$HostName", $SshHost)

Step "Проверка рабочей копии"
$dirty = git status --porcelain --untracked-files=no
if ($dirty) { throw "Есть незакоммиченные изменения — деплоится только HEAD. Закоммить их:`n$dirty" }
$rev = git rev-parse --short HEAD
Write-Host "HEAD = $rev  $(git log -1 --format=%s)"

if (-not $SkipTests -and $Target -ne "webapp") {
    Step "Тесты"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "Нужен uv (winget install astral-sh.uv) или -SkipTests" }
    uv run --quiet --python 3.11 --with-requirements requirements-dev.txt python -m pytest -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw "Тесты не прошли" }
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) "mp_deploy_$rev"
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory -Force "$tmp\pkg" | Out-Null

if ($Target -ne "backend") {
    Step "Сборка фронта"
    Push-Location webapp
    npx tsc -p tsconfig.json --noEmit; if ($LASTEXITCODE -ne 0) { Pop-Location; throw "tsc" }
    npm run build | Select-Object -Last 2; if ($LASTEXITCODE -ne 0) { Pop-Location; throw "vite build" }
    Pop-Location
}

Step "Упаковка HEAD"
git -c core.autocrlf=false archive --format=tar -o "$tmp\src.tar" HEAD
New-Item -ItemType Directory "$tmp\pkg\backend" | Out-Null
tar -xf "$tmp\src.tar" -C "$tmp\pkg\backend"
Remove-Item -Recurse -Force "$tmp\pkg\backend\.github" -ErrorAction SilentlyContinue
if ($Target -ne "backend") {
    New-Item -ItemType Directory "$tmp\pkg\webapp" | Out-Null
    Copy-Item -Recurse webapp\dist "$tmp\pkg\webapp\dist"
    Copy-Item webapp\nginx.conf "$tmp\pkg\webapp\"
}
Remove-Item -Recurse -Force "$tmp\pkg\backend\webapp"
Copy-Item "$tmp\pkg\backend\scripts\deploy_remote.sh" "$tmp\pkg\deploy_remote.sh"
tar -czf "$tmp\deploy.tgz" -C "$tmp\pkg" .

Step "Загрузка на сервер"
$remoteDir = "/tmp/mp_build_$rev"
scp -q -o BatchMode=yes -o "HostName=$HostName" "$tmp\deploy.tgz" "${SshHost}:/tmp/mp_deploy_$rev.tgz"
if ($LASTEXITCODE -ne 0) { throw "scp" }

Step "Деплой на сервере ($Target)"
ssh @ssh "rm -rf $remoteDir && mkdir -p $remoteDir && tar -xzf /tmp/mp_deploy_$rev.tgz -C $remoteDir && rm -f /tmp/mp_deploy_$rev.tgz && bash $remoteDir/deploy_remote.sh $remoteDir $Target"
$code = $LASTEXITCODE
Remove-Item -Recurse -Force $tmp
if ($code -ne 0) { throw "Деплой не прошёл (код $code) — см. вывод выше; при провале проверок прод откатан автоматически" }
Write-Host "Готово: $rev задеплоен ($Target)" -ForegroundColor Green
