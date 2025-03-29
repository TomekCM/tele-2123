import requests
import sqlite3
import time
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("integration_log.txt"), logging.StreamHandler()]
)
logger = logging.getLogger()

# Используем ваш токен, который работает в диагностике
TOKEN = "YOUR_BOT_TOKEN"  # Вставьте сюда ваш токен
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

def main():
    logger.info("Запуск сервиса отправки сообщений...")
    
    while True:
        try:
            # Подключаемся к базе данных
            conn = sqlite3.connect('messages.db')
            cursor = conn.cursor()
            
            # Получаем неотправленные ответы
            cursor.execute("""
                SELECT id, user_id, reply_text 
                FROM messages 
                WHERE is_replied = 1 AND reply_text IS NOT NULL
                AND (telegram_sent IS NULL OR telegram_sent = 0)
            """)
            
            messages = cursor.fetchall()
            
            if messages:
                logger.info(f"Найдено {len(messages)} неотправленных сообщений")
                
                for msg_id, user_id, text in messages:
                    logger.info(f"Отправка сообщения #{msg_id} пользователю {user_id}")
                    
                    # Отправляем сообщение через API
                    try:
                        response = requests.post(
                            API_URL,
                            json={
                                'chat_id': user_id,
                                'text': text
                            }
                        )
                        
                        if response.status_code == 200 and response.json().get('ok'):
                            logger.info(f"Сообщение #{msg_id} успешно отправлено!")
                            cursor.execute("UPDATE messages SET telegram_sent = 1 WHERE id = ?", (msg_id,))
                            conn.commit()
                        else:
                            logger.error(f"Ошибка при отправке: {response.json().get('description')}")
                            # Отмечаем как проблемное
                            cursor.execute("UPDATE messages SET telegram_sent = -1 WHERE id = ?", (msg_id,))
                            conn.commit()
                    
                    except Exception as e:
                        logger.error(f"Исключение при отправке сообщения: {e}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
        
        # Пауза между проверками
        time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Сервис остановлен пользователем")