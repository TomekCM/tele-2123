import sqlite3
import hashlib
import os

def fix_auth_database():
    # Check if auth.db exists
    if os.path.exists('auth.db'):
        print("Checking auth database structure...")
        
        conn = sqlite3.connect('auth.db')
        cursor = conn.cursor()
        
        # Check if password column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'password' not in columns:
            print("'password' column missing. Attempting to fix...")
            
            # Get the current structure
            has_password_hash = 'password_hash' in columns
            
            if has_password_hash:
                # Rename password_hash to password
                print("Converting password_hash column to password...")
                cursor.execute("ALTER TABLE users RENAME COLUMN password_hash TO password")
            else:
                # Create a temporary table with correct structure
                print("Creating new password column...")
                cursor.execute("ALTER TABLE users ADD COLUMN password TEXT")
                
                # Add default admin user with password 'admin'
                cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", 
                              (hashlib.sha256('admin'.encode()).hexdigest(),))
            
            conn.commit()
            print("Database structure fixed successfully!")
        else:
            print("Database structure is correct.")
        
        conn.close()
    else:
        print("Auth database not found. It will be created when you run the application.")

if __name__ == "__main__":
    fix_auth_database()