import sqlite3
import datetime

def check_messages_db():
    conn = sqlite3.connect('messages.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("===== MESSAGES DATABASE DIAGNOSTIC =====")
    
    # Check if messages table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    if not cursor.fetchone():
        print("ERROR: 'messages' table doesn't exist!")
        conn.close()
        return
    
    # Get message count
    cursor.execute("SELECT COUNT(*) FROM messages")
    count = cursor.fetchone()[0]
    print(f"Total messages in database: {count}")
    
    # Get the most recent messages
    print("\nMost recent messages:")
    cursor.execute("""
    SELECT id, user_id, first_name, message_text, reply_text, timestamp, is_read, is_replied
    FROM messages ORDER BY timestamp DESC LIMIT 5
    """)
    recent = cursor.fetchall()
    
    if not recent:
        print("No messages found in the database!")
    else:
        for msg in recent:
            print(f"ID: {msg['id']} | User: {msg['user_id']} | Time: {msg['timestamp']}")
            print(f"   Content: {msg['message_text'] or '(No text)'}")
            print(f"   Reply: {msg['reply_text'] or '(No reply)'}")
            print(f"   Read: {'Yes' if msg['is_read'] else 'No'} | Replied: {'Yes' if msg['is_replied'] else 'No'}")
            print("   " + "-" * 40)
    
    # Check unread messages
    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_read = 0")
    unread = cursor.fetchone()[0]
    print(f"\nUnread messages: {unread}")
    
    # Check users with messages
    cursor.execute("SELECT DISTINCT user_id, COUNT(*) as msg_count FROM messages GROUP BY user_id")
    users = cursor.fetchall()
    print("\nUsers with messages:")
    for user in users:
        print(f"User ID: {user['user_id']} | Message count: {user['msg_count']}")
    
    conn.close()
    print("\n===== END DIAGNOSTIC =====")

if __name__ == "__main__":
    check_messages_db()