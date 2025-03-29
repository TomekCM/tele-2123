import sqlite3

def check_recent_messages():
    """Проверяет статус последних сообщений"""
    conn = sqlite3.connect('messages.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, user_id, reply_text, timestamp, telegram_sent 
           FROM messages 
           WHERE is_replied = 1
           ORDER BY id DESC
           LIMIT 10"""
    )
    
    messages = cursor.fetchall()
    
    print(f"Последние {len(messages)} сообщений:")
    print("-" * 50)
    
    for msg in messages:
        status = "✅ ОТПРАВЛЕНО" if msg['telegram_sent'] == 1 else "❌ НЕ ОТПРАВЛЕНО"
        print(f"ID: {msg['id']}, Пользователь: {msg['user_id']}")
        print(f"Текст: {msg['reply_text'][:50]}...")
        print(f"Время: {msg['timestamp']}")
        print(f"Статус: {status} (telegram_sent = {msg['telegram_sent']})")
        print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    check_recent_messages()