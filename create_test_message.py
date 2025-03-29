import sqlite3
import datetime

def create_test_message():
    """Создает тестовое сообщение в базе данных, ожидающее отправки"""
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    
    # ID пользователя Telegram (замените на реальный)
    user_id = 6586101843  # Ваш ID из предыдущих логов
    
    # Текущее время
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Создаем тестовое сообщение с флагом telegram_sent = 0
    cursor.execute(
        """INSERT INTO messages 
        (user_id, message_text, timestamp, is_read, is_replied, reply_text, telegram_sent) 
        VALUES (?, NULL, ?, 1, 1, ?, 0)""",
        (user_id, timestamp, f"Тестовое сообщение, созданное скриптом в {timestamp}")
    )
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"Создано тестовое сообщение (ID: {message_id}) для пользователя {user_id}")
    print(f"Время: {timestamp}")
    print(f"Флаг telegram_sent установлен в 0")
    print(f"Проверьте, что отправщик сообщений обнаружит и отправит это сообщение")

if __name__ == "__main__":
    create_test_message()