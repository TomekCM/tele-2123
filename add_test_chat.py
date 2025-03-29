import sqlite3
import datetime

def add_test_chat():
    """Add a test conversation to ensure chats appear in the sidebar"""
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    
    # Delete any existing test conversation
    cursor.execute("DELETE FROM messages WHERE user_id = 123456789")
    
    # Current timestamp
    now = datetime.datetime.now()
    timestamp1 = now.strftime("%Y-%m-%d %H:%M:%S")
    timestamp2 = (now - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Add incoming message
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, is_read, is_replied) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (123456789, 'test_user', 'Test User', 'Hello! This is a test message to verify chat display.', 
         timestamp2, 0, 0)
    )
    
    # Add outgoing reply
    cursor.execute(
        """INSERT INTO messages 
        (user_id, message_text, timestamp, is_read, is_replied, reply_text) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        (123456789, None, timestamp1, 1, 1, 'This is a test reply from the system.')
    )
    
    conn.commit()
    conn.close()
    print("Test chat added successfully! Please refresh your web interface.")

if __name__ == "__main__":
    add_test_chat()