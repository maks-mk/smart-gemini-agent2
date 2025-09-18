# PowerShell-скрипт для глобальной установки MCP-серверов для Smart Gemini Agent

# --- Проверка зависимостей ---
Write-Host "Проверка наличия Node.js и uv..." -ForegroundColor Yellow

# Проверка Node.js
$node_exists = Get-Command node -ErrorAction SilentlyContinue
if (-not $node_exists) {
    Write-Host "Ошибка: Node.js не найден." -ForegroundColor Red
    Write-Host "Пожалуйста, установите Node.js (LTS-версию) с официального сайта: https://nodejs.org/"
    exit
}

# Проверка uv
$uv_exists = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv_exists) {
    Write-Host "Ошибка: uv не найден." -ForegroundColor Red
    Write-Host "Пожалуйста, установите uv, выполнив в PowerShell следующую команду:"
    Write-Host "irm https://astral.sh/uv/install.ps1 | iex"
    exit
}

Write-Host "Все зависимости найдены. Начинаем установку серверов..." -ForegroundColor Green
Write-Host ""

# --- Установка Node.js серверов ---
Write-Host "Установка Node.js серверов (npm)..." -ForegroundColor Cyan

$npm_packages = @(
    "@modelcontextprotocol/server-filesystem",
    "@modelcontextprotocol/server-sequential-thinking",
    "@simonb97/server-win-cli"
)

foreach ($package in $npm_packages) {
    Write-Host "Установка $package..."
    npm install -g $package
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ошибка при установке $package. Проверьте лог npm." -ForegroundColor Red
    } else {
        Write-Host "$package успешно установлен." -ForegroundColor Green
    }
}

Write-Host ""

# --- Установка Python серверов ---
Write-Host "Установка Python серверов (uv)..." -ForegroundColor Cyan

$uv_packages = @(
    "duckduckgo-mcp-server",
    "mcp-server-fetch",
    "excel-mcp-server"
)

foreach ($package in $uv_packages) {
    Write-Host "Установка $package..."
    uv tool install $package
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ошибка при установке $package." -ForegroundColor Red
    } else {
        Write-Host "$package успешно установлен." -ForegroundColor Green
    }
}

Write-Host ""

# --- Инструкции для Blender ---
Write-Host "--- Инструкции для Blender MCP Server ---" -ForegroundColor Yellow
Write-Host "Сервер для Blender требует ручной установки аддона."
Write-Host "1. Установите Blender 4.0 или новее с сайта https://www.blender.org/"
Write-Host "2. Скачайте аддон 'blender-mcp' с GitHub: https://github.com/ahujasid/blender-mcp"
Write-Host "3. В Blender перейдите в Edit > Preferences > Add-ons > Install..."
Write-Host "4. Выберите скачанный .py файл аддона и активируйте его."
Write-Host "После этого сервер можно будет запускать прямо из интерфейса Blender."
Write-Host ""

# --- Завершение ---
Write-Host "Установка завершена!" -ForegroundColor Green
Write-Host "Не забудьте обновить ваш 'mcp.json', чтобы он использовал глобально установленные команды (уберите 'npx -y' и 'uvx')."
