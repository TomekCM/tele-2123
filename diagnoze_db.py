import sqlite3
import os
import json
import datetime

def diagnose_database():
    print("===== DATABASE DIAGNOSTIC TOOL =====")
    print(f"Current time: {datetime.datetime.now()}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if database file exists
    if not os.path.exists('messages.db'):
        print("ERROR: messages.db file not found!")
        return
    
    print(f"Database file found. Size: {os.path.getsize('messages.db') / 1024:.2f} KB")
    
    try:
        # Connect to database
        conn = sqlite3.connect('messages.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        print(f"Tables found: {tables}")
        
        # Check message count
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        message_count = cursor.fetchone()['count']
        print(f"Total messages: {message_count}")
        
        # Get unique users
        cursor.execute("SELECT DISTINCT user_id FROM messages")
        user_ids = [row['user_id'] for row in cursor.fetchall()]
        print(f"Unique users: {len(user_ids)}")
        print(f"User IDs: {user_ids}")
        
        # Test the chat list query specifically
        print("\nTesting chat list query:")
        try:
            cursor.execute('''
            SELECT 
                m.user_id,
                m.username,
                m.first_name,
                m.message_text AS last_message_text,
                m.timestamp AS last_message_time,
                m.has_media,
                m.media_type,
                m.is_replied,
                m.reply_text,
                (SELECT COUNT(*) FROM messages 
                 WHERE user_id = m.user_id AND is_read = 0 AND is_replied = 0) AS unread_count,
                NULL as alias
            FROM messages m
            INNER JOIN (
                SELECT user_id, MAX(id) as max_id 
                FROM messages 
                GROUP BY user_id
            ) latest ON m.user_id = latest.user_id AND m.id = latest.max_id
            ORDER BY m.timestamp DESC
            ''')
            
            chats = [dict(row) for row in cursor.fetchall()]
            print(f"Query successful! Found {len(chats)} chats")
            
            # Output first 3 chats
            if chats:
                print("\nSample chat data:")
                for i, chat in enumerate(chats[:3]):
                    print(f"Chat {i+1}: User {chat['user_id']}, Name: {chat.get('first_name') or 'Unknown'}")
                    print(f"  Last message: {chat.get('last_message_text') or 'No text'}")
                    print(f"  Time: {chat.get('last_message_time')}")
                    print(f"  Unread: {chat.get('unread_count')}")
            
            # Save chat data to file for inspection
            with open('chat_data.json', 'w') as f:
                json.dump(chats, f, indent=2)
            print("\nFull chat data saved to chat_data.json")
            
        except Exception as e:
            print(f"ERROR in chat list query: {e}")
        
        # Get recent messages
        print("\nMost recent messages:")
        cursor.execute('''
        SELECT id, user_id, first_name, message_text, timestamp, is_read, is_replied
        FROM messages ORDER BY timestamp DESC LIMIT 5
        ''')
        
        recent = cursor.fetchall()
        for msg in recent:
            print(f"ID: {msg['id']} | User: {msg['user_id']} | Time: {msg['timestamp']}")
            print(f"  Content: {msg['message_text'] or '(No text)'}")
            print(f"  Read: {'Yes' if msg['is_read'] else 'No'} | Replied: {'Yes' if msg['is_replied'] else 'No'}")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n===== END DIAGNOSTIC =====")

if __name__ == "__main__":
    diagnose_database()