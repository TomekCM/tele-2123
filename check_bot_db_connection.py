import sqlite3
import os

def check_bot_db_connection():
    print("=== BOT DATABASE CONNECTION TEST ===")
    
    # Check if database file exists
    if not os.path.exists('messages.db'):
        print("ERROR: Database file 'messages.db' not found!")
        return False
    
    # Try connecting to the database
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            print("ERROR: 'messages' table not found!")
            conn.close()
            return False
        
        print("Connection successful! Database and tables exist.")
        
        # Check message count
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        print(f"Total messages in database: {count}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return False

if __name__ == "__main__":
    check_bot_db_connection()