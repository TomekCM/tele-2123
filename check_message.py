import sqlite3

def check_message_status(message_id):
    """Проверяет статус отправки сообщения"""
    conn = sqlite3.connect('messages.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, user_id, reply_text, timestamp, telegram_sent FROM messages WHERE id = ?", 
        (message_id,)
    )
    
    message = cursor.fetchone()
    
    if not message:
        print(f"Сообщение с ID {message_id} не найдено")
        conn.close()
        return
    
    print(f"Сообщение ID: {message['id']}")
    print(f"Пользователь: {message['user_id']}")
    print(f"Текст: {message['reply_text']}")
    print(f"Время: {message['timestamp']}")
    
    if message['telegram_sent'] == 1:
        print(f"✅ Статус: ОТПРАВЛЕНО (telegram_sent = 1)")
    else:
        print(f"❌ Статус: НЕ ОТПРАВЛЕНО (telegram_sent = 0)")
    
    conn.close()

if __name__ == "__main__":
    message_id = input("Введите ID сообщения для проверки: ")
    check_message_status(int(message_id))