import sqlite3

def reset_telegram_sent_status():
    """Сбрасывает статус отправки для сообщений, чтобы повторить попытку"""
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Обновляем статус для неотправленных сообщений
        cursor.execute("""
            UPDATE messages 
            SET telegram_sent = 0 
            WHERE is_replied = 1 AND reply_text IS NOT NULL
            AND (telegram_sent IS NULL OR telegram_sent < 0)
        """)
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"Сброшен статус отправки для {affected} сообщений")
        return True
    
    except Exception as e:
        print(f"Ошибка при сбросе статусов: {e}")
        return False

if __name__ == "__main__":
    reset_telegram_sent_status()