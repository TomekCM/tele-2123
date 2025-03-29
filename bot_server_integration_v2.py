import logging
import time
import sqlite3
import requests
import os

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integration_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Конфигурация
TOKEN = "YOUR_BOT_TOKEN"  # ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ НА ВАШ ТОКЕН
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
CHECK_INTERVAL = 3  # Секунды между проверками

def send_message_via_api(chat_id, text):
    """Отправляет сообщение через HTTP API Telegram напрямую"""
    try:
        response = requests.post(
            TELEGRAM_API,
            json={
                'chat_id': chat_id,
                'text': text
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"Сообщение отправлено пользователю {chat_id}")
                return True
            else:
                logger.error(f"Telegram API вернул ошибку: {result.get('description')}")
                return False
        else:
            logger.error(f"Ошибка HTTP {response.status_code}: {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        return False

def check_database_for_replies():
    """Проверяет базу данных на наличие новых ответов и отправляет их"""
    if not os.path.exists('messages.db'):
        logger.warning("База данных не найдена")
        return
    
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Обновляем структуру если нужно
        try:
            cursor.execute("PRAGMA table_info(messages)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'telegram_sent' not in columns:
                cursor.execute("ALTER TABLE messages ADD COLUMN telegram_sent INTEGER DEFAULT 0")
                conn.commit()
                logger.info("Добавлен столбец telegram_sent в таблицу messages")
        except Exception as e:
            logger.error(f"Ошибка при обновлении структуры: {e}")
        
        # Получаем неотправленные ответы
        cursor.execute("""
            SELECT id, user_id, reply_text 
            FROM messages 
            WHERE is_replied = 1 AND reply_text IS NOT NULL
            AND (telegram_sent IS NULL OR telegram_sent = 0)
        """)
        
        replies = cursor.fetchall()
        
        for reply in replies:
            message_id, user_id, reply_text = reply
            logger.info(f"Отправка ответа #{message_id} пользователю {user_id}: {reply_text[:30]}...")
            
            # Отправляем через API Telegram
            success = send_message_via_api(user_id, reply_text)
            
            # Обновляем статус
            if success:
                cursor.execute("UPDATE messages SET telegram_sent = 1 WHERE id = ?", (message_id,))
                conn.commit()
                logger.info(f"Сообщение #{message_id} помечено как отправленное")
            else:
                # Помечаем как проблемное, но не как отправленное
                cursor.execute("UPDATE messages SET telegram_sent = -1 WHERE id = ?", (message_id,))
                conn.commit()
                logger.error(f"Не удалось отправить сообщение #{message_id}")
        
        conn.close()
        
        if replies:
            logger.info(f"Обработано {len(replies)} ответов")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке базы данных: {e}")

def main():
    logger.info("Сервис интеграции запущен")
    
    # Проверяем токен
    try:
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe")
        if response.status_code != 200 or not response.json().get('ok'):
            logger.error(f"Ошибка при проверке токена бота: {response.json().get('description')}")
            logger.error("Сервис не может быть запущен с неверным токеном!")
            return
        
        bot_info = response.json().get('result')
        logger.info(f"Бот подключен: {bot_info.get('first_name')} (@{bot_info.get('username')})")
        
    except Exception as e:
        logger.error(f"Не удалось подключиться к Telegram API: {e}")
        logger.error("Сервис не может быть запущен!")
        return
    
    # Основной цикл
    try:
        while True:
            check_database_for_replies()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Сервис остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()