import sqlite3
import os

def upgrade_database():
    """Обновляет структуру базы данных для поддержки новых функций"""
    
    # Проверяем наличие базы данных
    if not os.path.exists('messages.db'):
        print("База данных не найдена. Создайте ее сначала.")
        return False
    
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    
    # Добавляем новые столбцы для хранения информации о медиафайлах
    try:
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Добавляем столбцы для медиафайлов
        if 'has_media' not in columns:
            print("Добавление поддержки медиафайлов...")
            cursor.execute("ALTER TABLE messages ADD COLUMN has_media INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE messages ADD COLUMN media_type TEXT")
            cursor.execute("ALTER TABLE messages ADD COLUMN media_file_id TEXT")
            cursor.execute("ALTER TABLE messages ADD COLUMN media_path TEXT")
        
        # Создаем таблицу псевдонимов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS aliases (
            user_id INTEGER PRIMARY KEY,
            real_name TEXT,
            alias TEXT NOT NULL,
            created_at TEXT
        )
        ''')
        
        # Создаем таблицу поисковых индексов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_search (
            id INTEGER PRIMARY KEY,
            message_id INTEGER,
            user_id INTEGER,
            content TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        print("База данных успешно обновлена!")
        return True
        
    except Exception as e:
        print(f"Ошибка при обновлении базы данных: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()