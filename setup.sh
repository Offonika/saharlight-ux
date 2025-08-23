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
npm ci || { echo "npm ci failed" >&2; exit 1; }

echo "Сборка фронтенда…"
npm --workspace services/webapp/ui run build || { echo "npm build failed" >&2; exit 1; }

if [ ! -f ".env" ]; then
    echo "Копирование infra/env/.env.example в .env (заполните ключи и пароли)…"
    cp infra/env/.env.example .env
fi

echo "Установка завершена! Проверьте файл .env и заполните свои токены и пароли."
echo "Фронтенд собран в services/webapp/ui/dist."
echo "Для запуска API: source venv/bin/activate && python services/api/app/main.py"
