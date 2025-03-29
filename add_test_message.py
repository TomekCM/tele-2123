import sqlite3
import datetime

def add_test_message():
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add a test message
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, is_read, is_replied) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (123456, 'test_user', 'Test User', 'This is a test message. Please reply if you see this!', timestamp, 0, 0)
    )
    
    print(f"Test message inserted with timestamp: {timestamp}")
    
    # Add a test reply
    cursor.execute(
        """INSERT INTO messages 
        (user_id, username, first_name, message_text, timestamp, is_read, is_replied, reply_text) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (123456, 'test_user', 'Test User', '', timestamp, 1, 1, 'This is a test reply from the admin.')
    )
    
    print("Test reply message inserted")
    
    conn.commit()
    conn.close()
    print("Test messages added successfully!")

if __name__ == "__main__":
    add_test_message()