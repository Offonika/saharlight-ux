# setup.sh — автоматическая установка окружения для Diabetes Bot
# Используйте: bash setup.sh

echo "Обновление списка пакетов и установка системных зависимостей…"
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential libpq-dev

echo "Создание виртуального окружения…"
python3 -m venv venv
source venv/bin/activate

echo "Установка Python-зависимостей…"
pip install --upgrade pip
pip install -r services/api/app/requirements.txt

echo "Сборка фронтенда (npm ci && npm run build)…"
pushd services/webapp/ui >/dev/null
npm ci
npm run build
popd >/dev/null

if [ ! -f ".env" ]; then
    echo "Копирование infra/env/.env.example в .env (заполните ключи и пароли)…"
    cp infra/env/.env.example .env
fi

echo "Установка завершена! Проверьте файл .env и заполните свои токены и пароли."
echo "Фронтенд собран в services/webapp/ui/dist."
echo "Для запуска API: source venv/bin/activate && uvicorn services.api.app.main:app --reload"
