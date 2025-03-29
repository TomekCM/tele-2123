import sqlite3
import os
import datetime

def initialize_database():
    db_path = 'messages.db'
    
    # Create a new database file
    print(f"Creating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Create messages table
    print("Creating messages table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        first_name TEXT,
        message_text TEXT,
        timestamp TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        is_replied INTEGER DEFAULT 0,
        reply_text TEXT,
        telegram_sent INTEGER DEFAULT 0,
        has_media INTEGER DEFAULT 0,
        media_type TEXT,
        media_file_id TEXT,
        media_path TEXT
    )
    ''')
    
    # Create aliases table
    print("Creating aliases table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aliases (
        user_id INTEGER PRIMARY KEY,
        real_name TEXT,
        alias TEXT NOT NULL,
        created_at TEXT
    )
    ''')
    
    # Create search index table
    print("Creating message_search table...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_search (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        user_id INTEGER,
        content TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )
    ''')
    
    # Create an index for faster message lookups
    print("Creating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_search_content ON message_search (content)')
    
    # Create uploads directory if it doesn't exist
    if not os.path.exists('static/uploads'):
        print("Creating static/uploads directory...")
        os.makedirs('static/uploads')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Database initialization complete!")
    
    # Verify the database was created correctly
    verify_database()

def verify_database():
    """Check if the database was created correctly"""
    print("\n=== VERIFICATION ===")
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables found: {[table[0] for table in tables]}")
        
        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = cursor.fetchall()
        print(f"Indexes found: {[index[0] for index in indexes]}")
        
        # Insert a test message
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """INSERT INTO messages 
            (user_id, username, first_name, message_text, timestamp) 
            VALUES (?, ?, ?, ?, ?)""",
            (999999, 'test_user', 'Test User', 'This is a test message from the initialization script.', timestamp)
        )
        
        # Check if message was inserted
        cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = 999999")
        count = cursor.fetchone()[0]
        print(f"Test message inserted: {'Yes' if count > 0 else 'No'}")
        
        # Clean up the test message
        cursor.execute("DELETE FROM messages WHERE user_id = 999999")
        
        conn.commit()
        conn.close()
        print("Verification complete! Database is properly set up.")
    except Exception as e:
        print(f"Verification failed: {e}")

if __name__ == "__main__":
    initialize_database()