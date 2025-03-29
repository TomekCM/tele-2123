import logging
import sqlite3
import datetime
import os
import time
import sys
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Получение значений из .env
TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_PATH = os.getenv("DATABASE_PATH", "messages.db")
UPLOAD_FOLDER = os.getenv("UPLOADS_FOLDER", "static/uploads")

# Проверка, что токен загружен
if not TOKEN:
    print("ВНИМАНИЕ: Токен не найден в .env файле. Используется значение по умолчанию.")
    TOKEN = "7653820469:AAHCZ_BGU9CDzCiC8i86Lvwz6Eua2S0f68U"

# Настройка логирования - исправлена кодировка
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("sender.log", encoding='utf-8'), 
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Функция для безопасного логирования без эмодзи
def safe_log(message, level="info"):
    """Безопасное логирование без Unicode-символов"""
    try:
        if level.lower() == "error":
            logger.error(message)
        elif level.lower() == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    except:
        # Если возникла ошибка с логированием, используем print
        print(f"[{level.upper()}] {message}")

# ИСПРАВЛЕНО: Асинхронная функция для отправки сообщений
async def send_messages_async():
    """Асинхронно отправляет ожидающие сообщения из базы данных"""
    try:
        # Проверка подключения к API Telegram
        try:
            bot = Bot(token=TOKEN)
            me = await bot.get_me()
            safe_log(f"Подключен к боту: @{me.username}")
        except Exception as e:
            safe_log(f"Ошибка подключения к API Telegram: {e}", "error")
            return 0
            
        # Подключение к базе данных
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем сообщения, ожидающие отправки
        cursor.execute(
            """SELECT * FROM messages 
               WHERE is_replied = 1 AND telegram_sent = 0
               ORDER BY timestamp ASC"""
        )
        
        messages = cursor.fetchall()
        
        if messages:
            safe_log(f"Найдено {len(messages)} сообщений для отправки")
            
        for msg in messages:
            try:
                # Отправка сообщения
                if msg['has_media'] == 1 and msg['media_path']:
                    # Отправка медиа-файлов
                    file_path = msg['media_path'].lstrip('/')
                    if os.path.exists(file_path):
                        if msg['media_type'] == 'photo':
                            with open(file_path, 'rb') as photo:
                                await bot.send_photo(msg['user_id'], photo, caption=msg['reply_text'])
                        elif msg['media_type'] == 'video':
                            with open(file_path, 'rb') as video:
                                await bot.send_video(msg['user_id'], video, caption=msg['reply_text'])
                        elif msg['media_type'] == 'audio':
                            with open(file_path, 'rb') as audio:
                                await bot.send_audio(msg['user_id'], audio, caption=msg['reply_text'])
                        else:
                            with open(file_path, 'rb') as doc:
                                await bot.send_document(msg['user_id'], doc, caption=msg['reply_text'])
                    else:
                        # Если файл не найден, отправляем только текст
                        safe_log(f"Файл не найден: {file_path}, отправляем только текст", "warning")
                        await bot.send_message(msg['user_id'], f"{msg['reply_text']} (файл не найден)")
                else:
                    # Отправка текстового сообщения
                    user_id = msg['user_id']
                    reply_text = msg['reply_text']
                    safe_log(f"Отправка сообщения пользователю {user_id}: {reply_text[:30]}...")
                    
                    result = await bot.send_message(user_id, reply_text)
                    if not result:
                        safe_log(f"Ошибка отправки сообщения: не получен результат", "error")
                        continue
                
                # Обновляем флаг отправки
                cursor.execute(
                    """UPDATE messages SET telegram_sent = 1 WHERE id = ?""",
                    (msg['id'],)
                )
                conn.commit()
                
                safe_log(f"Сообщение {msg['id']} успешно отправлено пользователю {msg['user_id']}")
                
                # Делаем паузу между сообщениями
                await asyncio.sleep(0.5)
                
            except Exception as e:
                safe_log(f"Ошибка отправки сообщения {msg['id']}: {e}", "error")
                # При ошибке делаем паузу
                await asyncio.sleep(1)
        
        conn.close()
        
        return len(messages)
        
    except Exception as e:
        safe_log(f"Ошибка в функции отправки: {e}", "error")
        return 0

# Синхронная обертка для проверки сообщения по ID
def check_message_by_id(message_id):
    """Проверяет статус конкретного сообщения по ID"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем информацию о сообщении
        cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        message = cursor.fetchone()
        
        if not message:
            print(f"Сообщение с ID {message_id} не найдено")
            return
        
        print(f"Сообщение ID: {message['id']}")
        print(f"Пользователь: {message['user_id']}")
        print(f"Текст: {message['reply_text'] or message['message_text']}")
        print(f"Время: {message['timestamp']}")
        
        if message['telegram_sent'] == 1:
            print("✅ Статус: ОТПРАВЛЕНО (telegram_sent = 1)")
        else:
            print("❌ Статус: НЕ ОТПРАВЛЕНО (telegram_sent = 0)")
            
        conn.close()
    except Exception as e:
        print(f"Ошибка при проверке сообщения: {e}")

# Синхронная обертка для принудительной пересылки сообщения
def force_resend_message(message_id):
    """Принудительно пересылает сообщение, установив статус telegram_sent = 0"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Сбрасываем статус отправки
        cursor.execute("UPDATE messages SET telegram_sent = 0 WHERE id = ?", (message_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            print(f"Сообщение {message_id} помечено для повторной отправки")
        else:
            print(f"Сообщение {message_id} не найдено")
        
        conn.close()
    except Exception as e:
        print(f"Ошибка при пересылке сообщения: {e}")

# ИСПРАВЛЕНО: Асинхронная главная функция
async def main_async():
    safe_log("Запуск автономного отправщика сообщений")
    safe_log(f"Используется токен: {TOKEN[:10]}...{TOKEN[-5:]}")
    safe_log(f"База данных: {DATABASE_PATH}")
    safe_log(f"Каталог загрузок: {UPLOAD_FOLDER}")
    
    # Отправляем сообщения один раз при запуске
    sent = await send_messages_async()
    
    if sent > 0:
        safe_log(f"Отправлено {sent} сообщений при запуске")
    else:
        safe_log("Нет сообщений для отправки")
    
    # Запускаем цикл проверки
    safe_log("Запуск цикла проверки сообщений")
    
    try:
        while True:
            # Проверяем каждые 5 секунд
            await asyncio.sleep(5)
            sent = await send_messages_async()
            if sent > 0:
                safe_log(f"Отправлено {sent} новых сообщений")
    except KeyboardInterrupt:
        safe_log("Отправщик сообщений остановлен пользователем")
    except Exception as e:
        safe_log(f"Критическая ошибка в главном цикле: {e}", "error")

# Синхронная точка входа
def main():
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        # Команда check - проверить сообщение по ID
        if command == "check" and len(sys.argv) > 2:
            check_message_by_id(sys.argv[2])
            return
            
        # Команда resend - пометить сообщение для повторной отправки
        if command == "resend" and len(sys.argv) > 2:
            force_resend_message(sys.argv[2])
            return
    
    # Запускаем асинхронный главный цикл
    asyncio.run(main_async())

if __name__ == "__main__":
    main()