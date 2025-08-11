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
pip install -r backend/requirements.txt

if [ ! -f ".env" ]; then
    echo "Копирование backend/.env.example в .env (заполните ключи и пароли)…"
    cp backend/.env.example .env
fi

echo "Установка завершена! Проверьте файл .env и заполните свои токены и пароли."
echo "Для запуска: source venv/bin/activate && python backend/bot.py"
