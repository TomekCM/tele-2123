from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv("TELEGRAM_TOKEN")
db_path = os.getenv("DATABASE_PATH")
uploads = os.getenv("UPLOADS_FOLDER")

print(f"TELEGRAM_TOKEN: {token}")
print(f"DATABASE_PATH: {db_path}")
print(f"UPLOADS_FOLDER: {uploads}")

if not token:
    print("ОШИБКА: Переменные окружения не загружены правильно!")
else:
    print("Переменные окружения загружены успешно!")