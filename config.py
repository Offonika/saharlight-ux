# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Загрузка переменных из .env файла

TELEGRAM_TOKEN      = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY      = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

DB_HOST     = os.getenv('DB_HOST', 'localhost')
DB_PORT     = os.getenv('DB_PORT', '5432')
DB_NAME     = os.getenv('DB_NAME', 'diabetes_bot')
DB_USER     = os.getenv('DB_USER', 'diabetes_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

OPENAI_PROXY = "http://user150107:dx4a5m@102.129.178.65:6517"
