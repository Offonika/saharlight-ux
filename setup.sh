# setup.sh — автоматическая установка окружения для Diabetes Bot
# Используйте: bash setup.sh

set -e

echo "Обновление списка пакетов и установка системных зависимостей…"
sudo apt-get update || { echo "APT update failed" >&2; exit 1; }
sudo add-apt-repository ppa:deadsnakes/ppa -y || { echo "Add-apt-repository failed" >&2; exit 1; }
sudo apt-get update || { echo "APT update failed" >&2; exit 1; }
sudo apt-get install -y python3.12-venv python3.12-dev build-essential libpq-dev || { echo "APT install failed" >&2; exit 1; }

command -v python3.12 >/dev/null 2>&1 || {
    echo >&2 "Python 3.12 не найден. Убедитесь, что установлен python3.12."
    exit 1
}

echo "Создание виртуального окружения…"
[ -d "venv" ] && rm -rf venv
python3.12 -m venv venv
source venv/bin/activate

echo "Установка Python-зависимостей…"
pip install --upgrade pip || { echo "Pip upgrade failed" >&2; exit 1; }
pip install -r requirements.txt || { echo "Python dependencies installation failed" >&2; exit 1; }

echo "Установка JavaScript-зависимостей…"
if ! command -v pnpm >/dev/null 2>&1; then
    echo "pnpm не найден, пытаюсь установить…"
    if command -v node >/dev/null 2>&1 && command -v corepack >/dev/null 2>&1 && [ "$(printf '%s\n' '16.13.0' "$(node -v | sed 's/^v//')" | sort -V | head -n1)" = '16.13.0' ]; then
        corepack enable pnpm || { echo "corepack enable pnpm failed" >&2; exit 1; }
    else
        npm install -g pnpm || { echo "npm install -g pnpm failed" >&2; exit 1; }
    fi
    command -v pnpm >/dev/null 2>&1 || { echo "pnpm installation failed" >&2; exit 1; }
fi

pnpm install || { echo "pnpm install failed" >&2; exit 1; }

echo "Сборка фронтенда…"
pnpm --filter services/webapp/ui run build || { echo "pnpm build failed" >&2; exit 1; }

if [ ! -f ".env" ]; then
    echo "Копирование infra/env/.env.example в .env (заполните ключи и пароли)…"
    cp infra/env/.env.example .env
fi

echo "Установка завершена! Проверьте файл .env и заполните свои токены и пароли."
echo "Фронтенд собран в services/webapp/ui/dist."
echo "Для запуска API: source venv/bin/activate && python services/api/app/main.py"
