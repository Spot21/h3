import os
import sys
from pathlib import Path
from dotenv import load_dotenv


# Определяем корневую директорию проекта
if getattr(sys, 'frozen', False):
    # Если запущено как exe файл
    PROJECT_ROOT = Path(sys.executable).parent
else:
    # Если запущено как Python скрипт
    PROJECT_ROOT = Path(__file__).parent.resolve()

# Загружаем переменные окружения из .env файла
env_file = PROJECT_ROOT / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"⚠️ Файл .env не найден по пути: {env_file}")
    print("Создайте файл .env с необходимыми настройками")

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен для доступа к API Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Идентификаторы администраторов (список строк с ID)
ADMINS = [admin_id.strip() for admin_id in os.getenv('ADMINS', '').split(',') if admin_id.strip()]

# Настройки подключения к базе данных
db_path = os.path.join('data', 'history_bot.db')
DB_ENGINE = os.getenv('DB_ENGINE', f'sqlite:///{db_path}')

# Настройки бота
ENABLE_PARENT_REPORTS = os.getenv('ENABLE_PARENT_REPORTS', 'True').lower() == 'true'

# Пути к файлам - используем os.path для корректной работы на всех платформах
DATA_DIR = os.getenv('DATA_DIR', 'data')
MEDIA_DIR = os.path.join(DATA_DIR, 'media')
QUESTIONS_DIR = os.path.join(DATA_DIR, 'questions')

# Убедимся, что все необходимые директории существуют
for directory in [DATA_DIR, MEDIA_DIR, QUESTIONS_DIR, MEDIA_DIR / 'images']:
    directory.mkdir(parents=True, exist_ok=True)

# Логирование
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = DATA_DIR / 'bot.log'

# Настройки для Windows
if os.name == 'nt':  # Windows
    # Настройки кодировки для Windows
    os.environ['PYTHONIOENCODING'] = 'utf-8'
